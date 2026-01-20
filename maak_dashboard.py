import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

# --- CONFIGURATIE ---
GOALS = {
    'bike_out': 3000, 
    'zwift': 3000,    
    'run': 350        
}

COLORS = {
    'primary': '#0f172a', 
    'gold': '#d4af37', 
    'gold_bg': '#f59e0b',
    'bg': '#f8fafc', 
    'card': '#ffffff', 
    'text': '#1e293b', 
    'text_light': '#64748b',
    'zwift': '#ff6600',    
    'bike_out': '#0099ff', 
    'run': '#fbbf24',      
    'swim': '#3b82f6',     
    'padel': '#84cc16',    
    'walk': '#10b981',     
    'default': '#64748b'
}

# --- CATEGORISERING OP BASIS VAN ACTIVITEITSTYPE ---
def determine_category(row):
    atype = str(row['Activiteitstype']).strip()
    if atype == 'Virtuele fietsrit': return 'Virtueel'
    if atype == 'Fietsrit': return 'Fiets'
    if atype == 'Hardlopen': return 'Hardlopen'
    if atype == 'Wandelen': return 'Wandelen'
    if atype == 'Zwemmen': return 'Zwemmen'
    if atype in ['Training', 'Workout', 'Gewichtstraining', 'Fitness']: return 'Padel'
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
    h, r = divmod(int(seconds), 3600)
    m, _ = divmod(r, 60)
    return f'{h}u {m:02d}m'

def format_diff_html(cur, prev, unit=""):
    if pd.isna(prev): prev = 0
    diff = cur - prev
    if diff == 0: return '<span class="diff-neutral">-</span>'
    color = '#10b981' if diff > 0 else '#ef4444'
    arrow = "▲" if diff > 0 else "▼"
    return f'<span style="color:{color}; background:{color}15; padding:2px 6px; border-radius:4px; font-weight:700; font-size:0.85em;">{arrow} {abs(diff):.1f} {unit}</span>'

def generate_kpi(title, val, icon="", diff=""):
    return f"""
    <div class="kpi-card">
        <div class="kpi-icon-box">{icon}</div>
        <div class="kpi-content">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{val}</div>
            <div class="kpi-sub">{diff}</div>
        </div>
    </div>
    """

def robust_date_parser(date_series):
    dates = pd.to_datetime(date_series, dayfirst=True, errors='coerce')
    if dates.isna().sum() > len(dates) * 0.5:
        dutch = {'jan': 'Jan', 'feb': 'Feb', 'mrt': 'Mar', 'apr': 'Apr', 'mei': 'May', 'jun': 'Jun', 'jul': 'Jul', 'aug': 'Aug', 'sep': 'Sep', 'okt': 'Oct', 'nov': 'Nov', 'dec': 'Dec'}
        ds = date_series.astype(str).str.lower()
        for nl, en in dutch.items(): 
            ds = ds.str.replace(nl, en, regex=False)
        dates = pd.to_datetime(ds, format='%d %b %Y, %H:%M:%S', errors='coerce')
    return dates

# --- STREAKS ---
def calculate_streaks(df):
    if df.empty: return {}
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

# --- DASHBOARD ONDERDELEN ---
def generate_stats_box(df, current_year):
    df_cur = df[df['Jaar'] == current_year]
    b_km = df_cur[df_cur['Categorie'] == 'Fiets']['Afstand_km'].sum()
    z_km = df_cur[df_cur['Categorie'] == 'Virtueel']['Afstand_km'].sum()
    r_km = df_cur[df_cur['Categorie'] == 'Hardlopen']['Afstand_km'].sum()
    b_pct, z_pct, r_pct = min(100, (b_km/GOALS['bike_out'])*100), min(100, (z_km/GOALS['zwift'])*100), min(100, (r_km/GOALS['run'])*100)
    s = calculate_streaks(df)
    return f"""
    <div class="stats-box-container">
        <div class="goals-section">
            <h3 class="box-title">🎯 DOELEN {current_year}</h3>
            <div class="goal-item">
                <div class="goal-label"><span>🚴 Buiten: {b_km:.0f}/{GOALS['bike_out']}km</span><span>{b_pct:.1f}%</span></div>
                <div class="goal-bar"><div style="width:{b_pct}%; background:{COLORS['bike_out']};"></div></div>
            </div>
            <div class="goal-item">
                <div class="goal-label"><span>👾 Zwift: {z_km:.0f}/{GOALS['zwift']}km</span><span>{z_pct:.1f}%</span></div>
                <div class="goal-bar"><div style="width:{z_pct}%; background:{COLORS['zwift']};"></div></div>
            </div>
            <div class="goal-item">
                <div class="goal-label"><span>🏃 Lopen: {r_km:.0f}/{GOALS['run']}km</span><span>{r_pct:.1f}%</span></div>
                <div class="goal-bar"><div style="width:{r_pct}%; background:{COLORS['run']};"></div></div>
            </div>
        </div>
        <div class="streaks-section">
            <h3 class="box-title">🔥 REEKSEN</h3>
            <div class="streak-row"><span class="label">Huidige Week Streak:</span><span class="val">{s.get('cur_week', 0)} weken</span></div>
            <div class="streak-row"><span class="label">Record Week Streak:</span><span class="val">{s.get('max_week', 0)} weken</span></div>
        </div>
    </div>
    """

def generate_gear_section(df):
    if 'Uitrusting voor activiteit' not in df.columns: return ""
    dfg = df.copy()
    dfg['Uitrusting voor activiteit'] = dfg['Uitrusting voor activiteit'].fillna('').astype(str)
    dfg = dfg[dfg['Uitrusting voor activiteit'].str.strip() != '']
    if dfg.empty: return "<p style='text-align:center;color:#94a3b8;'>Geen uitrusting data gevonden.</p>"
    stats = dfg.groupby('Uitrusting voor activiteit').agg(Count=('Categorie','count'), Km=('Afstand_km','sum'), Type=('Categorie', lambda x: x.mode()[0] if not x.mode().empty else 'Onbekend')).reset_index().sort_values('Km', ascending=False)
    html = '<div class="sport-grid">'
    for _, r in stats.iterrows():
        icon = '🚲' if 'Fiets' in str(r['Type']) or 'Virtueel' in str(r['Type']) else '👟'
        html += f"""<div class="kpi-card" style="display:block; padding:20px;"><div style="display:flex;align-items:center;gap:12px;margin-bottom:15px;"><div style="font-size:24px;background:#f1f5f9;width:50px;height:50px;border-radius:12px;display:flex;align-items:center;justify-content:center">{icon}</div><div><div style="font-weight:700;font-size:14px;">{r['Uitrusting voor activiteit']}</div><div style="font-size:12px;color:#64748b;">{r['Count']} activiteiten</div></div></div><div style="font-size:22px;font-weight:700;">{r['Km']:,.0f} km</div></div>"""
    return html + '</div>'

def generate_hall_of_fame(df):
    html = '<div class="hof-grid">'
    for cat in ['Fiets', 'Virtueel', 'Hardlopen']:
        df_s = df[(df['Categorie'] == cat) & (df['Afstand_km'] > 1.0)].copy()
        if df_s.empty: continue
        style = get_sport_style(cat)
        def get_top3(col, unit, is_pace=False):
            d_sorted = df_s.sort_values(col, ascending=False).head(3)
            res = ""
            medals = ['🥇','🥈','🥉']
            for i, (_, r) in enumerate(d_sorted.iterrows()):
                v = r[col]
                date = r['Datum'].strftime('%d %b %Y')
                val_str = f"{v:.1f} {unit}" if not is_pace else f"{int((3600/v)//60)}:{int((3600/v)%60):02d} /km"
                res += f'<div class="top3-item"><span>{medals[i]} {val_str}</span><span class="date">{date}</span></div>'
            return res
        html += f"""<div class="hof-card"><div class="hof-header" style="color:{style['color']}">{style['icon']} {cat}</div><div class="hof-sec"><div class="sec-label">Langste</div>{get_top3('Afstand_km', 'km')}</div><div class="hof-sec"><div class="sec-label">Snelste ⚡</div>{get_top3('Gemiddelde_Snelheid_km_u', 'km/u' if cat!='Hardlopen' else '', cat=='Hardlopen')}</div></div>"""
    return html + "</div>"

def create_monthly_charts(df, year):
    df_cur = df[df['Jaar'] == year].copy(); df_prev = df[df['Jaar'] == year - 1].copy()
    df_cur['Maand'] = df_cur['Datum'].dt.month; df_prev['Maand'] = df_prev['Datum'].dt.month
    months = ['Jan','Feb','Mrt','Apr','Mei','Jun','Jul','Aug','Sep','Okt','Nov','Dec']
    def bar(cat, title, color):
        c_m = df_cur[df_cur['Categorie'] == cat].groupby('Maand')['Afstand_km'].sum().reindex(range(1,13), fill_value=0)
        p_m = df_prev[df_prev['Categorie'] == cat].groupby('Maand')['Afstand_km'].sum().reindex(range(1,13), fill_value=0)
        f = go.Figure()
        f.add_trace(go.Bar(x=months, y=p_m, name=str(year-1), marker_color='#cbd5e1'))
        f.add_trace(go.Bar(x=months, y=c_m, name=str(year), marker_color=color))
        f.update_layout(title=title, template='plotly_white', barmode='group', margin=dict(t=40,b=20,l=20,r=20), height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
        return f.to_html(full_html=False, include_plotlyjs="cdn")
    return f'<div class="chart-box">{bar("Fiets", "🚴 Afstand Fietsen per Maand", COLORS["bike_out"])}</div><div class="chart-box" style="margin-top:15px;">{bar("Hardlopen", "🏃 Afstand Lopen per Maand", COLORS["run"])}</div>'

# --- MAIN ---
def genereer_dashboard():
    print("🚀 Start V33.1 (Fixing NameError & Restoring Garage)...")
    try: df = pd.read_csv('activities.csv')
    except: return print("❌ Geen activities.csv gevonden!")
    
    nm = {'Datum van activiteit': 'Datum', 'Naam activiteit': 'Naam', 'Activiteitstype': 'Activiteitstype', 'Beweegtijd': 'Beweegtijd_sec', 'Afstand': 'Afstand_km', 'Uitrusting voor activiteit': 'Uitrusting voor activiteit'}
    df = df.rename(columns={k:v for k,v in nm.items() if k in df.columns})
    for c in ['Afstand_km', 'Beweegtijd_sec']:
        if c in df.columns: df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce')

    df['Datum'] = robust_date_parser(df['Datum'])
    df['Categorie'] = df.apply(determine_category, axis=1)
    df['Jaar'] = df['Datum'].dt.year
    df['Gemiddelde_Snelheid_km_u'] = (df['Afstand_km'] / (df['Beweegtijd_sec'] / 3600)).replace([np.inf, -np.inf], 0)
    
    years = sorted(df['Jaar'].dropna().unique(), reverse=True)
    nav, sects = "", ""
    stats_box = generate_stats_box(df, datetime.now().year)

    for yr in years:
        is_cur = (yr == datetime.now().year)
        df_yr = df[df['Jaar'] == yr]
        df_prev_comp = df[(df['Jaar'] == yr-1) & (df['Datum'].dt.dayofyear <= datetime.now().timetuple().tm_yday)] if is_cur else df[df['Jaar'] == yr-1]
        
        kpis = f"""<div class="kpi-grid">
            {generate_kpi("Sessies", len(df_yr), "🔥", format_diff_html(len(df_yr), len(df_prev_comp)))}
            {generate_kpi("Afstand", f"{df_yr['Afstand_km'].sum():,.0f} km", "📏", format_diff_html(df_yr['Afstand_km'].sum(), df_prev_comp['Afstand_km'].sum(), "km"))}
            {generate_kpi("Tijd", format_time(df_yr['Beweegtijd_sec'].sum()), "⏱️")}
        </div>"""
        
        nav += f'<button class="nav-btn {"active" if is_cur else ""}" onclick="openTab(event, \'v-{int(yr)}\')">{int(yr)}</button>'
        sects += f"""<div id="v-{int(yr)}" class="tab-content" style="display:{"block" if is_cur else "none"}">
            <h2 class="section-title">Overzicht {int(yr)}</h2>{kpis}
            <h3 class="section-subtitle">Maandoverzicht</h3>{create_monthly_charts(df, int(yr))}
        </div>"""

    nav += '<button class="nav-btn" onclick="openTab(event, \'v-Gar\')">Garage</button>'
    sects += f"""<div id="v-Gar" class="tab-content" style="display:none"><h2 class="section-title">De Garage</h2>{generate_gear_section(df)}</div>"""

    html = f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"><title>Sport Dashboard</title><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet"><style>
    :root{{--primary:#0f172a;--gold:#d4af37;--bg:#f8fafc;--card:#ffffff;--text:#1e293b}}
    body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);margin:0;padding:15px;padding-bottom:50px}}
    .container{{max-width:900px;margin:0 auto}}
    .nav{{display:flex;gap:8px;overflow-x:auto;margin-bottom:20px;scrollbar-width:none}}.nav::-webkit-scrollbar{{display:none}}
    .nav-btn{{flex:0-0-auto;background:white;border:1px solid #e2e8f0;padding:8px 16px;border-radius:20px;font-size:14px;font-weight:600;color:#64748b;cursor:pointer}}
    .nav-btn.active{{background:var(--primary);color:white;border-color:var(--primary)}}
    .stats-box-container {{ display:flex; gap:15px; margin-bottom:20px; flex-wrap:wrap; }}
    .goals-section, .streaks-section {{ flex:1; background:white; padding:15px; border-radius:12px; border:1px solid #e2e8f0; min-width:300px; }}
    .box-title {{ font-size:13px; color:#64748b; margin-bottom:12px; text-transform:uppercase; }}
    .goal-item {{ margin-bottom:12px; }}
    .goal-label {{ display:flex; justify-content:space-between; font-size:12px; font-weight:700; margin-bottom:4px; }}
    .goal-bar {{ background:#f1f5f9; height:8px; border-radius:4px; overflow:hidden; }}
    .goal-bar div {{ height:100%; border-radius:4px; }}
    .streak-row {{ display:flex; justify-content:space-between; font-size:13px; margin-bottom:5px; }}
    .kpi-grid, .sport-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px; margin-bottom:20px; }}
    .kpi-card, .chart-box, .hof-card{{background:white;border-radius:16px;padding:15px;border:1px solid #f1f5f9;box-shadow:0 1px 3px rgba(0,0,0,0.02)}}
    .hof-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(250px,1fr)); gap:15px; }}
    .hof-header {{ font-weight:700; font-size:16px; margin-bottom:15px; }}
    .sec-label {{ font-size:10px; color:#94a3b8; font-weight:700; text-transform:uppercase; margin-bottom:8px; }}
    .top3-item {{ display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px; }}
    .gold-banner {{ background:linear-gradient(135deg, var(--gold) 0%, #f59e0b 100%); color:white; padding:15px; border-radius:12px; margin-bottom:15px; cursor:pointer; font-weight:700; }}
    </style></head><body><div class="container">
    <div class="gold-banner" onclick="toggleHOF()">🏆 Eregalerij & Records <span style="float:right">▼</span></div>
    <div id="hof-container" style="display:none; margin-bottom:20px;">{generate_hall_of_fame(df)}</div>
    {stats_box}<div class="nav">{nav}</div>{sects}</div>
    <script>
    function openTab(e,n){{
        document.querySelectorAll('.tab-content').forEach(x=>x.style.display='none');
        document.querySelectorAll('.nav-btn').forEach(x=>x.classList.remove('active'));
        document.getElementById(n).style.display='block';
        e.currentTarget.classList.add('active');
    }}
    function toggleHOF() {{
        var x = document.getElementById('hof-container');
        x.style.display = (x.style.display === 'none') ? 'block' : 'none';
    }}
    </script></body></html>"""
    with open('dashboard.html', 'w', encoding='utf-8') as f: f.write(html)
    print("✅ Dashboard (V33.1) gegenereerd.")

if __name__ == "__main__":
    genereer_dashboard()
