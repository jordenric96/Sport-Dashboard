import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import warnings
import re

warnings.filterwarnings("ignore", category=UserWarning)

# --- CONFIGURATIE ---
GOALS = {'bike_out': 3000, 'zwift': 3000, 'run': 350}
COLORS = {
    'primary': '#0f172a', 'gold': '#d4af37', 'gold_bg': '#f59e0b', 'bg': '#f8fafc',
    'card': '#ffffff', 'text': '#1e293b', 'zwift': '#ff6600', 'bike_out': '#0099ff',
    'run': '#fbbf24', 'swim': '#3b82f6', 'padel': '#84cc16', 'walk': '#10b981', 'default': '#64748b'
}

# --- DE ONVERWOESTBARE DATUM PARSER ---
def solve_dates(date_str):
    if pd.isna(date_str) or str(date_str).strip() == "": return pd.NaT
    d_map = {'jan':1,'feb':2,'mrt':3,'apr':4,'mei':5,'jun':6,'jul':7,'aug':8,'sep':9,'okt':10,'nov':11,'dec':12}
    try:
        clean = re.sub(r'[^a-zA-Z0-9\s:]', '', str(date_str).lower())
        parts = clean.split()
        day = int(parts[0])
        month = d_map.get(parts[1][:3], 1)
        year = int(parts[2])
        return pd.Timestamp(year=year, month=month, day=day)
    except:
        return pd.to_datetime(date_str, errors='coerce')

# --- CATEGORISERING ---
def determine_category(row):
    atype = str(row['Activiteitstype']).lower().strip()
    anaam = str(row['Naam']).lower().strip()
    if 'virtu' in atype or 'zwift' in anaam: return 'Virtueel'
    if any(x in atype for x in ['fiets', 'rit', 'gravel', 'mtb', 'cycle']): return 'Fiets'
    if any(x in atype for x in ['hardloop', 'run', 'jog', 'loop']): return 'Hardlopen'
    if any(x in atype for x in ['train', 'work', 'fit', 'kracht', 'padel', 'tennis']): return 'Padel'
    if 'zwem' in atype: return 'Zwemmen'
    if any(x in atype for x in ['wandel', 'hike', 'walk']): return 'Wandelen'
    return 'Overig'

def get_sport_style(cat):
    styles = {'Fiets':('🚴', COLORS['bike_out']), 'Virtueel':('👾', COLORS['zwift']), 'Hardlopen':('🏃', COLORS['run']),
              'Wandelen':('🚶', COLORS['walk']), 'Padel':('🎾', COLORS['padel']), 'Zwemmen':('🏊', COLORS['swim'])}
    return styles.get(cat, ('🏅', COLORS['default']))

# --- HELPERS ---
def format_time(seconds):
    if pd.isna(seconds) or seconds <= 0: return '0u 00m'
    h, r = divmod(int(seconds), 3600); m, _ = divmod(r, 60)
    return f'{h}u {m:02d}m'

def format_diff_html(cur, prev, unit=""):
    if pd.isna(prev) or prev == 0: return "-"
    diff = cur - prev
    color = '#10b981' if diff >= 0 else '#ef4444'
    arrow = "▲" if diff >= 0 else "▼"
    return f'<span style="color:{color}; font-weight:700;">{arrow} {abs(diff):.1f} {unit}</span>'

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

# --- UI ELEMENTEN ---
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
    </div>"""

def generate_hall_of_fame(df):
    html = '<div class="hof-grid">'
    df_hof = df.dropna(subset=['Datum']).copy()
    for cat in ['Fiets', 'Virtueel', 'Hardlopen']:
        df_s = df_hof[df_hof['Categorie'] == cat].copy()
        if df_s.empty: continue
        icon, color = get_sport_style(cat)
        def get_top3(col, unit, is_pace=False):
            d_sorted = df_s.sort_values(col, ascending=False).head(3)
            res = ""
            for i, (_, r) in enumerate(d_sorted.iterrows()):
                v = r[col]
                val = f"{v:.1f}{unit}" if not is_pace else f"{int((3600/v)//60)}:{int((3600/v)%60):02d}/km"
                res += f'<div class="top3-item"><span>{"🥇🥈🥉"[i]} {val}</span><span class="date">{r["Datum"].strftime("%d %b %y")}</span></div>'
            return res
        html += f"""<div class="hof-card"><div class="hof-header" style="color:{color}">{icon} {cat}</div><div class="hof-sec"><div class="sec-label">Langste</div>{get_top3('Afstand_km', 'km')}</div><div class="hof-sec"><div class="sec-label">Snelste ⚡</div>{get_top3('Gem_Snelheid', 'km/u', cat=='Hardlopen')}</div></div>"""
    return html + "</div>"

def generate_sport_cards(df_yr, df_prev_comp):
    html = '<div class="sport-grid">'
    for cat in sorted(df_yr['Categorie'].unique()):
        df_s = df_yr[df_yr['Categorie'] == cat]
        df_p = df_prev_comp[df_prev_comp['Categorie'] == cat] if df_prev_comp is not None else pd.DataFrame()
        icon, color = get_sport_style(cat)
        dist = df_s['Afstand_km'].sum(); secs = df_s['Beweegtijd_sec'].sum(); hr = df_s['Hartslag'].mean()
        spd = f"{(dist/(secs/3600)):.1f} km/u" if secs > 0 else "-"
        if cat == 'Hardlopen' and dist > 0:
            p_sec = secs / dist; spd = f"{int(p_sec//60)}:{int(p_sec%60):02d} /km"
        
        html += f"""<div class="sport-card">
            <div class="sport-header"><span style="color:{color}">{icon}</span> <strong>{cat}</strong></div>
            <div class="sport-stats-row">
                <div><div class="label">Sessies</div><div class="val">{len(df_s)}</div></div>
                <div><div class="label">Duur</div><div class="val">{format_time(secs)}</div></div>
                {f'<div><div class="label">Afstand</div><div class="val">{dist:,.0f} km</div></div>' if cat!='Padel' else ''}
                <div><div class="label">Snelheid</div><div class="val">{spd}</div></div>
                {f'<div><div class="label">Hartslag</div><div class="val">❤️ {hr:.0f}</div></div>' if pd.notna(hr) else ''}
            </div>
        </div>"""
    return html + '</div>'

def create_monthly_charts(df_cur, df_prev, year):
    months = ['Jan','Feb','Mrt','Apr','Mei','Jun','Jul','Aug','Sep','Okt','Nov','Dec']
    def bar(cat, title, color):
        c_m = df_cur[df_cur['Categorie'] == cat].groupby(df_cur['Datum'].dt.month)['Afstand_km'].sum().reindex(range(1,13), fill_value=0)
        p_m = df_prev[df_prev['Categorie'] == cat].groupby(df_prev['Datum'].dt.month)['Afstand_km'].sum().reindex(range(1,13), fill_value=0)
        f = go.Figure()
        f.add_trace(go.Bar(x=months, y=p_m, name=f"{year-1}", marker_color='#e2e8f0'))
        f.add_trace(go.Bar(x=months, y=c_m, name=f"{year}", marker_color=color))
        f.update_layout(title=title, template='plotly_white', barmode='group', margin=dict(t=40,b=10,l=10,r=10), height=220, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=True, legend=dict(orientation="h", y=1.2, x=0.5, xanchor="center"))
        return f.to_html(full_html=False, include_plotlyjs="cdn")
    return f'<div class="chart-box">{bar("Fiets", "🚴 Fietsen Buiten per Maand", COLORS["bike_out"])}</div><div class="chart-box" style="margin-top:15px;">{bar("Hardlopen", "🏃 Hardlopen per Maand", COLORS["run"])}</div>'

# --- MAIN ---
def genereer_dashboard():
    print("🚀 Start V39.0 (Full Content & Session Fix)...")
    try: 
        df = pd.read_csv('activities.csv')
        nm = {'Datum van activiteit':'Datum', 'Naam activiteit':'Naam', 'Activiteitstype':'Activiteitstype', 'Beweegtijd':'Beweegtijd_sec', 'Afstand':'Afstand_km', 'Gemiddelde hartslag':'Hartslag', 'Gemiddelde snelheid':'Gem_Snelheid', 'Uitrusting voor activiteit':'Gear'}
        df = df.rename(columns={k:v for k,v in nm.items() if k in df.columns})
        df['Afstand_km'] = pd.to_numeric(df['Afstand_km'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        df['Beweegtijd_sec'] = pd.to_numeric(df['Beweegtijd_sec'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        df['Gem_Snelheid'] = pd.to_numeric(df['Gem_Snelheid'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        df['Hartslag'] = pd.to_numeric(df['Hartslag'], errors='coerce')
        
        df['Datum'] = df['Datum'].apply(solve_dates)
        df = df.dropna(subset=['Datum'])
        df['Categorie'] = df.apply(determine_category, axis=1)
        df['Jaar'] = df['Datum'].dt.year
        df['Day'] = df['Datum'].dt.dayofyear
        
        print(f"📊 Controle: {len(df[df['Jaar']==2025])} sessies in 2025.")

        years = sorted(df['Jaar'].unique(), reverse=True)
        nav, sects = "", ""
        stats_box = generate_stats_box(df, datetime.now().year)

        for yr in years:
            df_yr = df[df['Jaar'] == yr]
            df_prev_yr = df[df['Jaar'] == yr-1]
            df_p_comp = df_prev_yr[df_prev_yr['Day'] <= datetime.now().timetuple().tm_yday] if yr == datetime.now().year else df_prev_yr
            
            nav += f'<button class="nav-btn {"active" if yr == datetime.now().year else ""}" onclick="openTab(event, \'v-{int(yr)}\')">{int(yr)}</button>'
            sects += f"""<div id="v-{int(yr)}" class="tab-content" style="display:{"block" if yr == datetime.now().year else "none"}">
                <h2 class="section-title">Overzicht {int(yr)}</h2>
                {generate_sport_cards(df_yr, df_p_comp)}
                <h3 class="section-subtitle">Trends</h3>{create_monthly_charts(df_yr, df_prev_yr, int(yr))}
                <h3 class="section-subtitle">Records {int(yr)}</h3>{generate_hall_of_fame(df_yr)}
            </div>"""

        nav += '<button class="nav-btn" onclick="openTab(event, \'v-Tot\')">Totaal</button>'
        sects += f'<div id="v-Tot" class="tab-content" style="display:none"><h2 class="section-title">Carrière</h2>{generate_hall_of_fame(df)}</div>'

        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Dashboard</title><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet"><style>
        :root{{--primary:#0f172a;--gold:#d4af37;--bg:#f8fafc;--card:#ffffff;--text:#1e293b;--label:#94a3b8}}
        body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);margin:0;padding:15px;padding-bottom:60px}}
        .container{{max-width:900px;margin:0 auto}}
        .nav{{display:flex;gap:8px;overflow-x:auto;margin-bottom:20px;scrollbar-width:none}}.nav::-webkit-scrollbar{{display:none}}
        .nav-btn{{flex:0 0 auto;background:white;border:1px solid #e2e8f0;padding:10px 20px;border-radius:25px;font-size:14px;font-weight:600;color:#64748b;cursor:pointer}}
        .nav-btn.active{{background:var(--primary);color:white;border-color:var(--primary)}}
        .stats-box-container{{display:flex;gap:15px;margin-bottom:20px;flex-wrap:wrap}}
        .goals-section, .streaks-section{{flex:1;background:white;padding:15px;border-radius:12px;border:1px solid #e2e8f0;min-width:280px}}
        .box-title{{font-size:11px;color:var(--label);text-transform:uppercase;margin-bottom:12px;letter-spacing:1px}}
        .goal-item{{margin-bottom:10px}}.goal-label{{display:flex;justify-content:space-between;font-size:12px;font-weight:600;margin-bottom:4px}}
        .goal-bar{{background:#f1f5f9;height:6px;border-radius:3px;overflow:hidden}}.goal-bar div{{height:100%;border-radius:3px}}
        .streak-row{{display:flex;justify-content:space-between;margin-bottom:4px;font-size:13px}}.streak-row .val{{font-weight:700;color:var(--primary)}}
        .sport-grid{{display:grid;grid-template-columns:1fr;gap:15px;margin-bottom:25px}}
        .sport-card{{background:white;padding:20px;border-radius:16px;border:1px solid #f1f5f9;box-shadow:0 2px 4px rgba(0,0,0,0.02)}}
        .sport-header{{display:flex;align-items:center;gap:10px;margin-bottom:15px;font-size:18px}}
        .sport-stats-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:15px}}
        .label{{font-size:10px;color:var(--label);text-transform:uppercase;font-weight:700;margin-bottom:4px}}
        .val{{font-size:16px;font-weight:700}}.sub{{font-size:11px}}
        .chart-box{{background:white;padding:15px;border-radius:16px;border:1px solid #f1f5f9;width:100%;box-sizing:border-box}}
        .hof-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:15px}}
        .hof-card{{background:white;padding:15px;border-radius:16px;border:1px solid #f1f5f9}}
        .hof-header{{font-weight:700;font-size:16px;margin-bottom:12px}}
        .sec-label{{font-size:9px;color:var(--label);text-transform:uppercase;margin-bottom:5px;font-weight:700}}
        .top3-item{{display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px}}
        .date{{font-size:10px;color:var(--label)}}
        .gold-banner {{ background:linear-gradient(135deg, var(--gold) 0%, #f59e0b 100%); color:white; padding:15px; border-radius:12px; margin-bottom:15px; cursor:pointer; font-weight:700; }}
        </style></head><body><div class="container">
        <div class="gold-banner" onclick="window.location.reload()">🏆 Sport Dashboard Jorden</div>
        {stats_box}<div class="nav">{nav}</div>{sects}</div>
        <script>
        function openTab(e,n){{
            document.querySelectorAll('.tab-content').forEach(x=>x.style.display='none');
            document.querySelectorAll('.nav-btn').forEach(x=>x.classList.remove('active'));
            document.getElementById(n).style.display='block'; e.currentTarget.classList.add('active');
        }}
        </script></body></html>"""
        
        with open('dashboard.html', 'w', encoding='utf-8') as f: f.write(html)
        print("✅ Dashboard gereed.")

    except Exception as e: print(f"❌ Fout: {e}")

if __name__ == "__main__": genereer_dashboard()
