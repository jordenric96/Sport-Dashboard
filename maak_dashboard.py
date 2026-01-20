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

# --- DE ONVERWOESTBARE DATUM PARSER ---
def force_parse_date(date_str):
    if pd.isna(date_str) or str(date_str).strip() == "": return pd.NaT
    d_map = {'jan':1,'feb':2,'mrt':3,'apr':4,'mei':5,'jun':6,'jul':7,'aug':8,'sep':9,'okt':10,'nov':11,'dec':12}
    try:
        s = str(date_str).lower().replace(',', '').split()
        # Verwacht formaat: "20 jun 2017 15:10:32"
        day = int(s[0])
        month = d_map.get(s[1][:3], 1)
        year = int(s[2])
        return pd.Timestamp(year=year, month=month, day=day)
    except:
        return pd.to_datetime(date_str, dayfirst=True, errors='coerce')

# --- CATEGORISERING ---
def determine_category(row):
    atype = str(row['Activiteitstype']).lower().strip()
    anaam = str(row['Naam']).lower().strip()
    if 'virtu' in atype or 'zwift' in anaam: return 'Virtueel'
    if any(x in atype for x in ['fiets', 'ride', 'gravel', 'mtb', 'cycle']): return 'Fiets'
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

def format_diff(cur, prev, unit=""):
    if pd.isna(prev) or prev == 0: return ""
    diff = cur - prev
    color = '#10b981' if diff >= 0 else '#ef4444'
    arrow = "▲" if diff >= 0 else "▼"
    return f'<span style="color:{color}; font-size:10px; font-weight:700;">{arrow} {abs(diff):.1f}{unit}</span>'

# --- UI COMPONENTEN ---
def generate_sport_cards(df_yr, df_prev_comp):
    html = '<div class="sport-grid">'
    for cat in ['Fiets', 'Virtueel', 'Hardlopen', 'Padel', 'Wandelen', 'Zwemmen']:
        df_s = df_yr[df_yr['Categorie'] == cat]
        if df_s.empty: continue
        df_p = df_prev_comp[df_prev_comp['Categorie'] == cat] if df_prev_comp is not None else pd.DataFrame()
        
        icon, color = get_sport_style(cat)
        dist, p_dist = df_s['Afstand_km'].sum(), df_p['Afstand_km'].sum() if not df_p.empty else 0
        secs, p_secs = df_s['Beweegtijd_sec'].sum(), df_p['Beweegtijd_sec'].sum() if not df_p.empty else 0
        
        dist_html = f'<div><div class="label">Afstand</div><div class="val">{dist:,.1f} km</div>{format_diff(dist, p_dist, "km")}</div>' if cat not in ['Padel'] else ""
        
        html += f"""<div class="sport-card">
            <div class="sport-header"><span style="color:{color}">{icon}</span> <strong>{cat}</strong></div>
            <div class="sport-stats-row">
                <div><div class="label">Sessies</div><div class="val">{len(df_s)}</div>{format_diff(len(df_s), len(df_p))}</div>
                <div><div class="label">Duur</div><div class="val">{format_time(secs)}</div></div>
                {dist_html}
            </div>
        </div>"""
    return html + '</div>'

def create_vertical_charts(df_cur, df_prev, year):
    months = ['Jan','Feb','Mrt','Apr','Mei','Jun','Jul','Aug','Sep','Okt','Nov','Dec']
    def make_bar(cat, title, color):
        c_m = df_cur[df_cur['Categorie'] == cat].groupby(df_cur['Datum'].dt.month)['Afstand_km'].sum().reindex(range(1,13), fill_value=0)
        p_m = df_prev[df_prev['Categorie'] == cat].groupby(df_prev['Datum'].dt.month)['Afstand_km'].sum().reindex(range(1,13), fill_value=0)
        f = go.Figure()
        f.add_trace(go.Bar(x=months, y=p_m, name=f"{year-1}", marker_color=COLORS['ref_gray']))
        f.add_trace(go.Bar(x=months, y=c_m, name=f"{year}", marker_color=color))
        f.update_layout(title=title, template='plotly_white', barmode='group', margin=dict(t=40,b=20,l=20,r=20), height=220, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=True, legend=dict(orientation="h", y=1.2, x=0.5, xanchor="center"))
        return f.to_html(full_html=False, include_plotlyjs="cdn")
    
    return f'<div class="chart-box full-width">{make_bar("Fiets", "🚴 Fietsen Buiten (Maand)", COLORS["bike_out"])}</div>' + \
           f'<div class="chart-box full-width" style="margin-top:15px;">{make_bar("Hardlopen", "🏃 Hardlopen (Maand)", COLORS["run"])}</div>'

# --- MAIN ENGINE ---
def genereer_dashboard():
    print("🚀 Start V37.0 (The Final Session Count Fix)...")
    try: 
        df = pd.read_csv('activities.csv')
        nm = {'Datum van activiteit': 'Datum', 'Naam activiteit': 'Naam', 'Activiteitstype': 'Activiteitstype', 'Beweegtijd': 'Beweegtijd_sec', 'Afstand': 'Afstand_km'}
        df = df.rename(columns={k:v for k,v in nm.items() if k in df.columns})
        df['Afstand_km'] = pd.to_numeric(df['Afstand_km'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        df['Beweegtijd_sec'] = pd.to_numeric(df['Beweegtijd_sec'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        
        # De cruciale fix: forceer de datum parsing
        df['Datum'] = df['Datum'].apply(force_parse_date)
        df = df.dropna(subset=['Datum']) # Gooi rijen weg die ECHT geen datum hebben
        df['Categorie'] = df.apply(determine_category, axis=1)
        df['Jaar'] = df['Datum'].dt.year
        df['DagVanJaar'] = df['Datum'].dt.dayofyear
        
        print(f"✅ Data geladen. Totaal sessies in 2025: {len(df[df['Jaar']==2025])}")

        years = sorted(df['Jaar'].unique(), reverse=True)
        nav, sects = "", ""

        for yr in years:
            df_yr = df[df['Jaar'] == yr]
            df_prev_yr = df[df['Jaar'] == yr-1]
            # Vergelijking met zelfde periode vorig jaar
            now = datetime.now()
            comp_mask = df_prev_yr['Datum'].dt.dayofyear <= now.timetuple().tm_yday
            df_p_comp = df_prev_yr[comp_mask] if yr == now.year else df_prev_yr
            
            kpis = f"""<div class="kpi-grid">
                {generate_kpi("Sessies", len(df_yr), "🔥", format_diff(len(df_yr), len(df_p_comp)))}
                {generate_kpi("Afstand", f"{df_yr['Afstand_km'].sum():,.0f} km", "📏", format_diff(df_yr['Afstand_km'].sum(), df_p_comp['Afstand_km'].sum(), "km"))}
                {generate_kpi("Tijd", format_time(df_yr['Beweegtijd_sec'].sum()), "⏱️")}
            </div>"""

            nav += f'<button class="nav-btn {"active" if yr == now.year else ""}" onclick="openTab(event, \'v-{int(yr)}\')">{int(yr)}</button>'
            sects += f"""<div id="v-{int(yr)}" class="tab-content" style="display:{"block" if yr == now.year else "none"}">
                <h2 class="section-title">Overzicht {int(yr)}</h2>{kpis}
                <h3 class="section-subtitle">Stats per Sport</h3>{generate_sport_cards(df_yr, df_p_comp)}
                <h3 class="section-subtitle">Maandoverzicht</h3>{create_vertical_charts(df_yr, df_prev_yr, int(yr))}
            </div>"""

        # HTML Structure
        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Sport Jorden</title><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet"><style>
        :root{{--primary:#0f172a;--gold:#d4af37;--bg:#f8fafc;--card:#ffffff;--text:#1e293b;--label:#94a3b8}}
        body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);margin:0;padding:15px;padding-bottom:60px}}
        .container{{max-width:800px;margin:0 auto}}
        .nav{{display:flex;gap:8px;overflow-x:auto;margin-bottom:20px;padding-bottom:5px;scrollbar-width:none}}
        .nav-btn{{flex:0 0 auto;background:white;border:1px solid #e2e8f0;padding:8px 16px;border-radius:20px;font-size:14px;font-weight:600;color:#64748b;cursor:pointer}}
        .nav-btn.active{{background:var(--primary);color:white;border-color:var(--primary)}}
        .kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px;margin-bottom:25px}}
        .kpi-card{{background:white;padding:15px;border-radius:16px;border:1px solid #f1f5f9;box-shadow:0 1px 3px rgba(0,0,0,0.02)}}
        .kpi-title{{font-size:11px;color:var(--label);text-transform:uppercase;font-weight:700}}
        .kpi-value{{font-size:20px;font-weight:700;margin:4px 0}}
        .sport-grid{{display:grid;grid-template-columns:1fr;gap:12px;margin-bottom:25px}}
        .sport-card{{background:white;padding:15px;border-radius:16px;border:1px solid #f1f5f9}}
        .sport-header{{display:flex;align-items:center;gap:10px;margin-bottom:12px;font-size:18px}}
        .sport-stats-row{{display:flex;justify-content:space-between;gap:10px}}
        .label{{font-size:10px;color:var(--label);text-transform:uppercase;font-weight:700}}
        .val{{font-size:16px;font-weight:700}}
        .chart-box{{background:white;padding:15px;border-radius:16px;border:1px solid #f1f5f9;margin-bottom:15px}}
        .full-width{{width:100%}}
        .section-title{{font-size:20px;margin-bottom:15px}}
        .section-subtitle{{font-size:12px;color:var(--label);text-transform:uppercase;margin:25px 0 10px 0;letter-spacing:1px}}
        </style></head><body><div class="container">
        <h1 style="font-size:24px;margin-bottom:20px;">Sport Dashboard Jorden</h1>
        <div class="nav">{nav}</div>{sects}</div>
        <script>
        function openTab(e,n){{
            document.querySelectorAll('.tab-content').forEach(x=>x.style.display='none');
            document.querySelectorAll('.nav-btn').forEach(x=>x.classList.remove('active'));
            document.getElementById(n).style.display='block'; e.currentTarget.classList.add('active');
        }}
        </script></body></html>"""
        
        with open('dashboard.html', 'w', encoding='utf-8') as f: f.write(html)
        print("✅ Dashboard (V37.0) gegenereerd.")

    except Exception as e:
        print(f"❌ Fout tijdens generatie: {e}")

if __name__ == "__main__":
    genereer_dashboard()
