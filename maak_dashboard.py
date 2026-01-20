import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

# --- CONFIGURATIE ---
GOALS = {'bike_out': 3000, 'zwift': 3000, 'run': 350}

COLORS = {
    'primary': '#0f172a', 'gold': '#d4af37', 'gold_bg': '#f59e0b', 'bg': '#f8fafc',
    'card': '#ffffff', 'text': '#1e293b', 'zwift': '#ff6600', 'bike_out': '#0099ff',
    'run': '#fbbf24', 'swim': '#3b82f6', 'padel': '#84cc16', 'walk': '#10b981', 'default': '#64748b',
    'ref_gray': '#cbd5e1'
}

# --- STRIKTE CATEGORISERING ---
def determine_category(row):
    atype = str(row['Activiteitstype']).lower().strip()
    anaam = str(row['Naam']).lower().strip()
    if 'virtu' in atype or 'zwift' in anaam or 'zwift' in atype: return 'Virtueel'
    if any(x in atype for x in ['rit', 'fiets', 'cycle', 'velo', 'bike', 'mtb', 'gravel']): return 'Fiets'
    if any(x in atype for x in ['hardloop', 'run', 'jog', 'loop']): return 'Hardlopen'
    if any(x in atype for x in ['train', 'work', 'fit', 'kracht', 'padel', 'tenn', 'weight', 'gym']): return 'Padel'
    if 'zwem' in atype or 'swim' in atype: return 'Zwemmen'
    if any(x in atype for x in ['wandel', 'hike', 'walk']): return 'Wandelen'
    return 'Overig'

def get_sport_style(cat):
    config = {
        'Fiets': {'icon': '🚴', 'color': COLORS['bike_out']},
        'Virtueel': {'icon': '👾', 'color': COLORS['zwift']},
        'Hardlopen': {'icon': '🏃', 'color': COLORS['run']},
        'Wandelen': {'icon': '🚶', 'color': COLORS['walk']},
        'Padel': {'icon': '🎾', 'color': COLORS['padel']},
        'Zwemmen': {'icon': '🏊', 'color': COLORS['swim']},
        'Overig': {'icon': '🏅', 'color': COLORS['default']}
    }
    return config.get(cat, config['Overig'])

# --- HELPERS ---
def format_time(seconds):
    if pd.isna(seconds) or seconds <= 0: return '-'
    h, r = divmod(int(seconds), 3600); m, _ = divmod(r, 60)
    return f'{h}u {m:02d}m'

def format_diff_html(cur, prev, unit=""):
    if pd.isna(prev) or prev == 0: return '-'
    diff = cur - prev
    color = '#10b981' if diff > 0 else '#ef4444'
    arrow = "▲" if diff > 0 else "▼"
    return f'<span style="color:{color}; font-weight:700;">{arrow} {abs(diff):.1f} {unit}</span>'

def generate_kpi(title, val, icon="", diff=""):
    return f"""<div class="kpi-card"><div class="kpi-icon-box">{icon}</div><div class="kpi-content"><div class="kpi-title">{title}</div><div class="kpi-value">{val}</div><div class="kpi-sub">{diff}</div></div></div>"""

def robust_date_parser(date_series):
    dates = pd.to_datetime(date_series, dayfirst=True, errors='coerce')
    if dates.isna().sum() > len(dates) * 0.5:
        dutch = {'jan': 'Jan', 'feb': 'Feb', 'mrt': 'Mar', 'apr': 'Apr', 'mei': 'May', 'jun': 'Jun', 'jul': 'Jul', 'aug': 'Aug', 'sep': 'Sep', 'okt': 'Oct', 'nov': 'Nov', 'dec': 'Dec'}
        ds = date_series.astype(str).str.lower()
        for nl, en in dutch.items(): ds = ds.str.replace(nl, en, regex=False)
        dates = pd.to_datetime(ds, format='%d %b %Y, %H:%M:%S', errors='coerce')
    return dates

# --- STREAKS (69 WEKEN FIX) ---
def calculate_streaks(df):
    valid = df.dropna(subset=['Datum']).sort_values('Datum')
    if valid.empty: return {}
    valid['WeekStart'] = valid['Datum'].dt.to_period('W-MON').dt.start_time
    wk_dates = sorted(valid['WeekStart'].unique())
    cur_wk = 0; max_wk = 0
    if wk_dates:
        now_wk = pd.Timestamp.now().to_period('W-MON').start_time
        if (now_wk - wk_dates[-1]).days <= 7:
            cur_wk = 1
            for i in range(len(wk_dates)-2, -1, -1):
                if (wk_dates[i+1] - wk_dates[i]).days == 7: cur_wk += 1
                else: break
        temp = 1; max_wk = 1
        for i in range(1, len(wk_dates)):
            if (wk_dates[i] - wk_dates[i-1]).days == 7: temp += 1
            else: max_wk = max(max_wk, temp); temp = 1
        max_wk = max(max_wk, temp)
    return {'cur_week': cur_wk, 'max_week': max_wk}

# --- VISUELE COMPONENTEN ---
def generate_sport_cards(df_yr, df_prev_comp):
    html = '<div class="sport-grid">'
    for cat in ['Fiets', 'Virtueel', 'Hardlopen', 'Padel', 'Wandelen']:
        df_s = df_yr[df_yr['Categorie'] == cat]
        if df_s.empty: continue
        df_p = df_prev_comp[df_prev_comp['Categorie'] == cat] if df_prev_comp is not None else pd.DataFrame()
        st = get_sport_style(cat)
        dist = df_s['Afstand_km'].sum()
        p_dist = df_p['Afstand_km'].sum() if not df_p.empty else 0
        html += f"""<div class="sport-card">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
                <div class="sport-icon-circle" style="background:{st['color']}20; color:{st['color']}">{st['icon']}</div>
                <strong style="font-size:16px;">{cat}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                <div><div class="label">Sessies</div><div class="val">{len(df_s)}</div></div>
                <div style="text-align:right;"><div class="label">Afstand</div><div class="val">{dist:,.0f} km</div><div class="sub">{format_diff_html(dist, p_dist, "km")}</div></div>
            </div>
        </div>"""
    return html + '</div>'

def generate_hall_of_fame(df, title="Eregalerij & Records"):
    html = f'<div class="hof-grid">'
    df_hof = df.dropna(subset=['Datum']).copy()
    for cat in ['Fiets', 'Virtueel', 'Hardlopen']:
        df_s = df_hof[df_hof['Categorie'] == cat].copy()
        if df_s.empty: continue
        style = get_sport_style(cat)
        def top3(col, unit, is_pace=False):
            res = ""
            for i, (_, r) in enumerate(df_s.sort_values(col, ascending=False).head(3).iterrows()):
                v = r[col]
                val_str = f"{v:.1f}{unit}" if not is_pace else f"{int((3600/v)//60)}:{int((3600/v)%60):02d}/km"
                res += f'<div class="top3-item"><span>{"🥇🥈🥉"[i]} {val_str}</span><span class="date">{r["Datum"].strftime("%d %b %y")}</span></div>'
            return res or "Geen data"
        html += f"""<div class="hof-card"><div class="hof-header" style="color:{style['color']}">{style['icon']} {cat}</div><div class="hof-sec"><div class="sec-label">Langste</div>{top3('Afstand_km', 'km')}</div><div class="hof-sec"><div class="sec-label">Snelste ⚡</div>{top3('Gemiddelde_Snelheid_km_u', 'km/u', cat=='Hardlopen')}</div></div>"""
    return html + "</div>"

def create_monthly_charts(df_cur, df_prev, year):
    months = ['Jan','Feb','Mrt','Apr','Mei','Jun','Jul','Aug','Sep','Okt','Nov','Dec']
    def bar(cat, title, color):
        c_m = df_cur[df_cur['Categorie'] == cat].groupby(df_cur['Datum'].dt.month)['Afstand_km'].sum().reindex(range(1,13), fill_value=0)
        p_m = df_prev[df_prev['Categorie'] == cat].groupby(df_prev['Datum'].dt.month)['Afstand_km'].sum().reindex(range(1,13), fill_value=0)
        f = go.Figure()
        f.add_trace(go.Bar(x=months, y=p_m, name=f"{year-1}", marker_color=COLORS['ref_gray']))
        f.add_trace(go.Bar(x=months, y=c_m, name=f"{year}", marker_color=color))
        f.update_layout(title=title, template='plotly_white', barmode='group', margin=dict(t=40,b=20,l=20,r=20), height=220, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=True, legend=dict(orientation="h", y=1.2, x=0.5, xanchor="center"))
        return f.to_html(full_html=False, include_plotlyjs="cdn")
    return f'<div class="chart-box full-width">{bar("Fiets", "🚴 Fietsen Buiten (Maand)", COLORS["bike_out"])}</div><div class="chart-box full-width" style="margin-top:15px;">{bar("Hardlopen", "🏃 Hardlopen (Maand)", COLORS["run"])}</div>'

def create_evolution_chart(df):
    stats = df.groupby(['Jaar', 'Categorie'])['Afstand_km'].sum().unstack(fill_value=0)
    fig = go.Figure()
    if 'Fiets' in stats.columns: fig.add_trace(go.Bar(x=stats.index, y=stats['Fiets'], name='Fietsen Buiten', marker_color=COLORS['bike_out']))
    if 'Virtueel' in stats.columns: fig.add_trace(go.Bar(x=stats.index, y=stats['Virtueel'], name='Zwift', marker_color=COLORS['zwift']))
    if 'Hardlopen' in stats.columns: fig.add_trace(go.Bar(x=stats.index, y=stats['Hardlopen'], name='Lopen', marker_color=COLORS['run']))
    fig.update_layout(title="Jaarlijkse Evolutie", template='plotly_white', barmode='group', height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=True, legend=dict(orientation="h", y=1.2))
    return f'<div class="chart-box full-width">{fig.to_html(full_html=False, include_plotlyjs="cdn")}</div>'

def generate_gear_section(df):
    dfg = df.dropna(subset=['Uitrusting voor activiteit']).copy()
    dfg = dfg[dfg['Uitrusting voor activiteit'].str.strip() != '']
    if dfg.empty: return "<p style='text-align:center; padding:20px; color:#94a3b8;'>Geen uitrusting data gevonden.</p>"
    stats = dfg.groupby('Uitrusting voor activiteit').agg(Km=('Afstand_km','sum'), Type=('Categorie', lambda x: x.mode()[0])).reset_index().sort_values('Km', ascending=False)
    html = '<div class="kpi-grid">'
    for _, r in stats.iterrows():
        icon = '🚲' if r['Type'] in ['Fiets', 'Virtueel'] else '👟'
        html += f"""<div class="kpi-card" style="display:block; padding:20px;"><div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;"><div style="font-size:24px;">{icon}</div><div style="font-weight:700; font-size:14px;">{r['Uitrusting voor activiteit']}</div></div><div style="font-size:22px; font-weight:700;">{r['Km']:,.0f} km</div></div>"""
    return html + '</div>'

# --- MAIN ---
def genereer_dashboard():
    print("🚀 Start V35.0 (Full Restore & Vertical Layout)...")
    try: df = pd.read_csv('activities.csv')
    except: return print("❌ Geen CSV gevonden!")
    
    nm = {'Datum van activiteit': 'Datum', 'Naam activiteit': 'Naam', 'Activiteitstype': 'Activiteitstype', 'Beweegtijd': 'Beweegtijd_sec', 'Afstand': 'Afstand_km', 'Uitrusting voor activiteit': 'Uitrusting voor activiteit'}
    df = df.rename(columns={k:v for k,v in nm.items() if k in df.columns})
    for c in ['Afstand_km', 'Beweegtijd_sec']:
        if c in df.columns: df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce')

    df['Datum'] = robust_date_parser(df['Datum'])
    df['Categorie'] = df.apply(determine_category, axis=1)
    df['Jaar'] = df['Datum'].dt.year
    df['DagVanJaar'] = df['Datum'].dt.dayofyear
    df['Gemiddelde_Snelheid_km_u'] = (df['Afstand_km'] / (df['Beweegtijd_sec'] / 3600)).replace([np.inf, -np.inf], 0)

    years = sorted(df['Jaar'].dropna().unique(), reverse=True)
    nav, sects = "", ""
    
    # KPIs Streak Box
    s = calculate_streaks(df)
    stats_box = f"""<div class="stats-box-container">
        <div class="goals-section">
            <h3 class="box-title">🎯 VOORTGANG {datetime.now().year}</h3>
            <div class="goal-item"><div class="goal-label"><span>🚴 Buiten</span><span>{df[df['Jaar']==datetime.now().year][df['Categorie']=='Fiets']['Afstand_km'].sum():.0f}/3000km</span></div><div class="goal-bar"><div style="width:{min(100, df[df['Jaar']==datetime.now().year][df['Categorie']=='Fiets']['Afstand_km'].sum()/30):.1f}%; background:{COLORS['bike_out']};"></div></div></div>
            <div class="goal-item"><div class="goal-label"><span>👾 Zwift</span><span>{df[df['Jaar']==datetime.now().year][df['Categorie']=='Virtueel']['Afstand_km'].sum():.0f}/3000km</span></div><div class="goal-bar"><div style="width:{min(100, df[df['Jaar']==datetime.now().year][df['Categorie']=='Virtueel']['Afstand_km'].sum()/30):.1f}%; background:{COLORS['zwift']};"></div></div></div>
        </div>
        <div class="streaks-section">
            <h3 class="box-title">🔥 STREAK</h3>
            <div class="streak-row"><span class="label">Huidig:</span><span class="val">{s.get('cur_week', 0)} weken</span></div>
            <div class="streak-row"><span class="label">Record:</span><span class="val">{s.get('max_week', 0)} weken</span></div>
        </div>
    </div>"""

    for yr in years:
        df_yr = df[df['Jaar'] == yr]
        df_prev_yr = df[df['Jaar'] == yr-1]
        df_prev_comp = df_prev_yr[df_prev_yr['DagVanJaar'] <= datetime.now().timetuple().tm_yday] if yr == datetime.now().year else df_prev_yr
        
        kpis = f"""<div class="kpi-grid">
            {generate_kpi("Sessies", len(df_yr), "🔥", format_diff_html(len(df_yr), len(df_prev_comp)))}
            {generate_kpi("Totaal km", f"{df_yr['Afstand_km'].sum():,.0f} km", "📏", format_diff_html(df_yr['Afstand_km'].sum(), df_prev_comp['Afstand_km'].sum(), "km"))}
        </div>"""
        
        nav += f'<button class="nav-btn {"active" if yr == datetime.now().year else ""}" onclick="openTab(event, \'v-{int(yr)}\')">{int(yr)}</button>'
        sects += f"""<div id="v-{int(yr)}" class="tab-content" style="display:{"block" if yr == datetime.now().year else "none"}">
            <h2 class="section-title">Overzicht {int(yr)}</h2>
            {kpis}
            <h3 class="section-subtitle">Per Sport</h3>{generate_sport_cards(df_yr, df_prev_comp)}
            <h3 class="section-subtitle">Trends</h3>{create_monthly_charts(df_yr, df_prev_yr, int(yr))}
            <h3 class="section-subtitle">Jaarlijkse Records</h3>{generate_hall_of_fame(df_yr)}
        </div>"""

    nav += '<button class="nav-btn" onclick="openTab(event, \'v-Tot\')">Totaal</button>'
    nav += '<button class="nav-btn" onclick="openTab(event, \'v-Gar\')">Garage</button>'
    sects += f'<div id="v-Tot" class="tab-content" style="display:none"><h2 class="section-title">Carrière</h2>{create_evolution_chart(df)}{generate_hall_of_fame(df)}</div>'
    sects += f'<div id="v-Gar" class="tab-content" style="display:none"><h2 class="section-title">De Garage</h2>{generate_gear_section(df)}</div>'

    html = f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"><title>Sport Dashboard</title><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet"><style>
    :root{{--primary:#0f172a;--gold:#d4af37;--bg:#f8fafc;--card:#ffffff}}
    body{{font-family:'Inter',sans-serif;background:var(--bg);color:#1e293b;margin:0;padding:15px;padding-bottom:50px}}
    .container{{max-width:900px;margin:0 auto}}
    .nav{{display:flex;gap:8px;overflow-x:auto;margin-bottom:20px;scrollbar-width:none}}.nav::-webkit-scrollbar{{display:none}}
    .nav-btn{{flex:0 0 auto;background:white;border:1px solid #e2e8f0;padding:8px 16px;border-radius:20px;font-size:14px;font-weight:600;color:#64748b;cursor:pointer}}
    .nav-btn.active{{background:var(--primary);color:white;border-color:var(--primary)}}
    .kpi-grid, .sport-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:12px; margin-bottom:20px; }}
    .kpi-card, .sport-card, .chart-box, .hof-card{{background:white;border-radius:16px;padding:15px;border:1px solid #f1f5f9;box-shadow:0 1px 3px rgba(0,0,0,0.02)}}
    .stats-box-container {{ display:flex; gap:15px; margin-bottom:20px; flex-wrap:wrap; }}
    .goals-section, .streaks-section {{ flex:1; background:white; padding:15px; border-radius:12px; border:1px solid #e2e8f0; min-width:280px; }}
    .box-title {{ font-size:11px; color:#94a3b8; text-transform:uppercase; letter-spacing:1px; margin-bottom:12px; }}
    .goal-item {{ margin-bottom:10px; }}
    .goal-label {{ display:flex; justify-content:space-between; font-size:12px; font-weight:600; margin-bottom:4px; }}
    .goal-bar {{ background:#f1f5f9; height:6px; border-radius:3px; overflow:hidden; }}
    .goal-bar div {{ height:100%; border-radius:3px; }}
    .streak-row {{ display:flex; justify-content:space-between; margin-bottom:4px; font-size:13px; }}
    .streak-row .val {{ font-weight:700; color:var(--primary); }}
    .sport-icon-circle {{ width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:16px; }}
    .label {{ font-size:10px; color:#94a3b8; font-weight:700; text-transform:uppercase; }}
    .val {{ font-size:18px; font-weight:700; }}
    .sub {{ font-size:11px; }}
    .section-title {{ font-size:18px; margin-bottom:15px; }}
    .section-subtitle {{ font-size:11px; color:#94a3b8; text-transform:uppercase; margin:25px 0 12px 0; letter-spacing:1px; }}
    .hof-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(250px, 1fr)); gap:15px; }}
    .hof-header {{ font-weight:700; font-size:15px; margin-bottom:15px; }}
    .hof-sec {{ margin-bottom:12px; }}
    .sec-label {{ font-size:9px; color:#94a3b8; font-weight:700; text-transform:uppercase; margin-bottom:5px; }}
    .top3-item {{ display:flex; justify-content:space-between; font-size:12px; margin-bottom:3px; }}
    .date {{ font-size:10px; color:#94a3b8; }}
    .full-width {{ width: 100%; }}
    </style></head><body><div class="container">{stats_box}<div class="nav">{nav}</div>{sects}</div>
    <script>
    function openTab(e,n){{
        document.querySelectorAll('.tab-content').forEach(x=>x.style.display='none');
        document.querySelectorAll('.nav-btn').forEach(x=>x.classList.remove('active'));
        document.getElementById(n).style.display='block'; e.currentTarget.classList.add('active');
    }}
    </script></body></html>"""
    
    with open('dashboard.html', 'w', encoding='utf-8') as f: f.write(html)
    print("✅ Dashboard (V35.0) gegenereerd.")

if __name__ == "__main__":
    genereer_dashboard()
