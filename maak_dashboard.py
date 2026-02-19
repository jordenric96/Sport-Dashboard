import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import warnings
import re

warnings.filterwarnings("ignore", category=UserWarning)

# --- CONFIGURATIE ---
PLOT_CONFIG = {'displayModeBar': False, 'staticPlot': False, 'scrollZoom': False, 'responsive': True}

HR_ZONES = {'Z1 Herstel': 135, 'Z2 Duur': 152, 'Z3 Tempo': 168, 'Z4 Drempel': 180, 'Z5 Max': 220}

COLORS = {
    'primary': '#0f172a', 'gold': '#d4af37', 'bg': '#f8fafc',
    'card': '#ffffff', 'text': '#334155', 'text_light': '#64748b',
    'zwift': '#ff6600', 'bike_out': '#0ea5e9', 'run': '#f59e0b', 
    'swim': '#3b82f6', 'padel': '#84cc16', 'walk': '#10b981', 
    'strength': '#8b5cf6', 'default': '#64748b', 'ref_gray': '#cbd5e1',
    'z1': '#a3e635', 'z2': '#facc15', 'z3': '#fb923c', 'z4': '#f87171', 'z5': '#ef4444'
}

# Felle kleuren voor de jaren race
YEAR_COLORS = ['#2563eb', '#16a34a', '#ea580c', '#dc2626', '#9333ea', '#0891b2']

# --- DATUM FIX ---
def solve_dates(date_str):
    if pd.isna(date_str) or str(date_str).strip() == "": return pd.NaT
    d_map = {'jan':1,'feb':2,'mrt':3,'apr':4,'mei':5,'jun':6,'jul':7,'aug':8,'sep':9,'okt':10,'nov':11,'dec':12}
    try:
        clean = re.sub(r'[^a-zA-Z0-9\s:]', '', str(date_str).lower())
        parts = clean.split()
        day, month_str, year = int(parts[0]), parts[1][:3], int(parts[2])
        return pd.Timestamp(year=year, month=d_map.get(month_str, 1), day=day, hour=12) 
    except: return pd.to_datetime(date_str, errors='coerce')

# --- CATEGORIE LOGICA ---
def determine_category(row):
    t = str(row['Activiteitstype']).lower().strip(); n = str(row['Naam']).lower().strip()
    if any(x in t for x in ['kracht', 'power', 'gym', 'fitness', 'weight']) or any(x in n for x in ['kracht', 'power', 'gym', 'fitness']): return 'Krachttraining'
    if 'virtu' in t or 'zwift' in n: return 'Zwift'
    if any(x in t for x in ['fiets', 'ride', 'gravel', 'mtb', 'cycle', 'wieler', 'velomobiel', 'e-bike']): return 'Fiets'
    if any(x in t for x in ['hardloop', 'run', 'jog', 'lopen', 'loop']): return 'Hardlopen'
    if 'zwem' in t: return 'Zwemmen'
    if any(x in t for x in ['wandel', 'hike', 'walk']): return 'Wandelen'
    if any(x in t for x in ['padel', 'tennis', 'squash']): return 'Padel'
    return 'Overig'

def get_sport_style(cat):
    styles = {
        'Fiets':('🚴', COLORS['bike_out']), 'Zwift':('👾', COLORS['zwift']), 
        'Hardlopen':('🏃', COLORS['run']), 'Wandelen':('🚶', COLORS['walk']), 
        'Padel':('🎾', COLORS['padel']), 'Zwemmen':('🏊', COLORS['swim']),
        'Krachttraining': ('🏋️', COLORS['strength'])
    }
    return styles.get(cat, ('🏅', COLORS['default']))

def determine_zone(hr):
    if pd.isna(hr) or hr == 0: return 'Onbekend'
    if hr < HR_ZONES['Z1 Herstel']: return 'Z1 Herstel'
    if hr < HR_ZONES['Z2 Duur']: return 'Z2 Duur'
    if hr < HR_ZONES['Z3 Tempo']: return 'Z3 Tempo'
    if hr < HR_ZONES['Z4 Drempel']: return 'Z4 Drempel'
    return 'Z5 Max'

# --- HELPERS ---
def format_time(seconds):
    if pd.isna(seconds) or seconds <= 0: return '-'
    h, r = divmod(int(seconds), 3600); m, _ = divmod(r, 60)
    return f'{h}u {m:02d}m'

def format_diff_html(cur, prev, unit=""):
    if pd.isna(prev) and cur == 0: return '<span style="color:#cbd5e1">-</span>'
    diff = cur - (prev if pd.notna(prev) else 0)
    color = '#10b981' if diff >= 0 else '#ef4444'
    arrow = "▲" if diff >= 0 else "▼"
    return f'<span style="color:{color}; font-weight:700; font-size:0.85em; font-family: monospace;">{arrow} {abs(diff):.1f} {unit}</span>'

# --- UI GENERATORS ---
def create_ytd_chart(df, current_year):
    fig = go.Figure()
    years_to_plot = sorted(df['Jaar'].unique(), reverse=True)[:5]
    
    for i, y in enumerate(years_to_plot):
        df_y = df[df['Jaar'] == y].groupby('Day')['Afstand_km'].sum().reset_index()
        if df_y.empty: continue
        
        all_days = pd.DataFrame({'Day': range(1, 367)})
        df_y = pd.merge(all_days, df_y, on='Day', how='left').fillna(0)
        df_y['Cum_Afstand'] = df_y['Afstand_km'].cumsum()
        
        if y == datetime.now().year:
            current_day = datetime.now().timetuple().tm_yday
            df_y.loc[df_y['Day'] > current_day, 'Cum_Afstand'] = np.nan
            
        color = YEAR_COLORS[i % len(YEAR_COLORS)]
        width = 4 if y == current_year else 2
        
        fig.add_trace(go.Scatter(
            x=df_y['Day'], y=df_y['Cum_Afstand'], 
            mode='lines', name=str(y), 
            line=dict(color=color, width=width),
            hovertemplate=f"<b>{y}</b><br>Dag %{{x}}<br>%{{y:.0f}} km<extra></extra>"
        ))
        
    fig.update_layout(
        title='📈 Aantal km\'s', 
        template='plotly_white', 
        margin=dict(t=40,b=10,l=0,r=10), # l=0 haalt witruimte aan linkerkant weg
        height=380, paper_bgcolor='rgba(0,0,0,0)', 
        xaxis=dict(title="", showgrid=False, fixedrange=True), 
        yaxis=dict(title="", showgrid=True, fixedrange=True, side="right"), # Getallen rechts voor meer ruimte links
        legend=dict(orientation="h", y=1.1, x=0)
    )
    return f'<div class="chart-box full-width" style="margin-bottom:25px; padding-left:5px;">{fig.to_html(full_html=False, include_plotlyjs="cdn", config=PLOT_CONFIG)}</div>'

def calculate_streaks(df):
    valid = df.dropna(subset=['Datum']).sort_values('Datum')
    if valid.empty: return {}
    valid['WeekStart'] = valid['Datum'].dt.to_period('W-MON').dt.start_time
    weeks = sorted(valid['WeekStart'].unique()); days = sorted(valid['Datum'].dt.date.unique())
    cur_wk, max_wk, max_wk_dates = 0, 0, "-"
    if weeks:
        if (pd.Timestamp.now().to_period('W-MON').start_time - weeks[-1]).days <= 7:
            cur_wk = 1
            for i in range(len(weeks)-2, -1, -1):
                if (weeks[i+1]-weeks[i]).days == 7: cur_wk+=1
                else: break
        temp, start = 1, weeks[0]; max_wk, max_wk_dates = 1, f"({weeks[0].strftime('%d %b %y')})"
        for i in range(1, len(weeks)):
            if (weeks[i]-weeks[i-1]).days == 7: temp+=1
            else:
                if temp > max_wk: max_wk = temp; max_wk_dates = f"({start.strftime('%d %b %y')} - {(weeks[i-1]+timedelta(days=6)).strftime('%d %b %y')})"
                temp = 1; start = weeks[i]
        if temp > max_wk: max_wk = temp; max_wk_dates = f"({start.strftime('%d %b %y')} - {(weeks[-1]+timedelta(days=6)).strftime('%d %b %y')})"
    cur_d, max_d, max_d_dates = 0, 0, "-"
    if days:
        if (datetime.now().date() - days[-1]).days <= 1: cur_d = 1
        for i in range(len(days)-2, -1, -1):
            if (days[i+1]-days[i]).days == 1: cur_d+=1
            else: break
        temp, start = 1, days[0]; max_d, max_d_dates = 1, f"({days[0].strftime('%d %b')})"
        for i in range(1, len(days)):
            if (days[i]-days[i-1]).days == 1: temp+=1
            else:
                if temp > max_d: max_d = temp; max_d_dates = f"({start.strftime('%d %b')} - {days[i-1].strftime('%d %b %y')})"
                temp = 1; start = days[i]
        if temp > max_d: max_d = temp; max_d_dates = f"({start.strftime('%d %b')} - {days[-1].strftime('%d %b %y')})"
    return {'cur_week':cur_wk, 'max_week':max_wk, 'max_week_dates':max_wk_dates, 'cur_day':cur_d, 'max_day':max_d, 'max_day_dates':max_d_dates}

def generate_streaks_box(df):
    s = calculate_streaks(df)
    return f"""<div class="streaks-section" style="margin-bottom:25px;">
        <h3 class="box-title">🔥 REEKSEN</h3>
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px;">
            <div>
                <div class="streak-row"><span class="label">Week:</span><span class="val">{s['cur_week']}</span></div>
                <div class="streak-sub">Rec: {s['max_week']}</div>
            </div>
            <div>
                <div class="streak-row"><span class="label">Dag:</span><span class="val">{s['cur_day']}</span></div>
                <div class="streak-sub">Rec: {s['max_day']}</div>
            </div>
        </div>
    </div>"""

def create_scatter_plot(df_yr):
    df_bike = df_yr[df_yr['Categorie'] == 'Fiets']; df_zwift = df_yr[df_yr['Categorie'] == 'Zwift']; df_run = df_yr[df_yr['Categorie'] == 'Hardlopen']
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_bike['Afstand_km'], y=df_bike['Gem_Snelheid'], mode='markers', name='Fiets', marker=dict(color=COLORS['bike_out'], size=8), text=df_bike['Naam']))
    fig.add_trace(go.Scatter(x=df_zwift['Afstand_km'], y=df_zwift['Gem_Snelheid'], mode='markers', name='Zwift', marker=dict(color=COLORS['zwift'], size=8), text=df_zwift['Naam']))
    fig.add_trace(go.Scatter(x=df_run['Afstand_km'], y=df_run['Gem_Snelheid'], mode='markers', name='Loop', marker=dict(color=COLORS['run'], size=8), text=df_run['Naam']))
    fig.update_layout(title='⚡ Snelheid', template='plotly_white', margin=dict(t=40,b=10,l=0,r=10), height=300, paper_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=-0.2))
    return f'<div class="chart-box">{fig.to_html(full_html=False, include_plotlyjs="cdn", config=PLOT_CONFIG)}</div>'

def create_zone_pie(df_yr):
    df_hr = df_yr[(df_yr['Hartslag'] > 0) & (df_yr['Hartslag'].notna())].copy()
    if df_hr.empty: return ""
    df_hr['Zone'] = df_hr['Hartslag'].apply(determine_zone)
    color_map = {'Z1 Herstel': COLORS['z1'], 'Z2 Duur': COLORS['z2'], 'Z3 Tempo': COLORS['z3'], 'Z4 Drempel': COLORS['z4'], 'Z5 Max': COLORS['z5']}
    counts = df_hr['Zone'].value_counts().reset_index()
    fig = go.Figure(data=[go.Pie(labels=counts['Zone'], values=counts['count'], hole=0.6, marker=dict(colors=[color_map.get(z, '#ccc') for z in counts['Zone']]))])
    fig.update_layout(title='❤️ Hartslag', template='plotly_white', margin=dict(t=40,b=10,l=0,r=10), height=300, paper_bgcolor='rgba(0,0,0,0)')
    return f'<div class="chart-box">{fig.to_html(full_html=False, include_plotlyjs="cdn", config=PLOT_CONFIG)}</div>'

def generate_sport_cards(df_yr, df_prev_comp):
    html = '<div class="sport-grid">'
    for cat in ['Fiets', 'Zwift', 'Hardlopen', 'Krachttraining', 'Padel']:
        df_s = df_yr[df_yr['Categorie'] == cat]; df_p = df_prev_comp[df_prev_comp['Categorie'] == cat] if df_prev_comp is not None else pd.DataFrame()
        if df_s.empty: continue
        icon, color = get_sport_style(cat)
        n=len(df_s); np=len(df_p); d=df_s['Afstand_km'].sum(); dp=df_p['Afstand_km'].sum() if not df_p.empty else 0
        t=df_s['Beweegtijd_sec'].sum(); tp=df_p['Beweegtijd_sec'].sum() if not df_p.empty else 0
        
        rows = f'<div class="stat-row"><span>Sessies</span><div class="val-group"><strong>{n}</strong>{format_diff_html(n,np)}</div></div>'
        rows += f'<div class="stat-row"><span>Tijd</span><div class="val-group"><strong>{format_time(t)}</strong>{format_diff_html(t/3600,tp/3600,"u")}</div></div>'
        if cat not in ['Krachttraining', 'Padel']:
            rows += f'<div class="stat-row"><span>Afstand</span><div class="val-group"><strong>{d:,.0f} km</strong>{format_diff_html(d,dp)}</div></div>'
            
        html += f"""<div class="sport-card"><div class="sport-header" style="color:{color}"><div class="icon-circle" style="background:{color}15">{icon}</div><h3>{cat}</h3></div><div class="sport-body">{rows}</div></div>"""
    return html + '</div>'

def generate_yearly_gear(df_yr, df_all, all_time_mode=False):
    df_g = df_all if all_time_mode else df_yr
    df_g = df_g.dropna(subset=['Gear']).copy()
    df_g = df_g[df_g['Gear'].str.strip() != '']
    if df_g.empty: return '<p style="color:#64748b; font-size:13px; padding:20px;">Geen materiaalgegevens bekend.</p>'
    
    gears = df_g['Gear'].unique()
    html = '<div class="kpi-grid">'
    for g in gears:
        dy = df_g[df_g['Gear'] == g]
        ky = dy['Afstand_km'].sum()
        sy = dy['Beweegtijd_sec'].sum()
        act_mode = dy['Categorie'].mode()[0] if not dy.empty else 'Fiets'
        icon = '👟' if act_mode in ['Hardlopen', 'Wandelen'] else '🚲'
        verb = 'Gelopen' if icon == '👟' else 'Gereden'
        
        html += f"""
        <div class="kpi-card" style="padding:15px;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                <span style="font-size:20px;">{icon}</span>
                <strong style="font-size:13px; color:{COLORS['primary']};">{g}</strong>
            </div>
            <div style="font-size:10px; color:#64748b; text-transform:uppercase; font-weight:700;">{verb}</div>
            <div style="font-size:20px; font-weight:800; color:{COLORS['primary']};">{ky:,.0f} km</div>
        </div>"""
    return html + "</div>"

def generate_hall_of_fame(df):
    html = '<div class="hof-grid">'
    for cat in ['Fiets', 'Zwift', 'Hardlopen']:
        df_s = df[df['Categorie'] == cat]
        if df_s.empty: continue
        icon, color = get_sport_style(cat)
        def t3(col,u):
            ds = df_s.sort_values(col, ascending=False).head(3); r=""
            for i,(_,row) in enumerate(ds.iterrows()):
                r += f'<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;"><span>{"🥇🥈🥉"[i]} {row[col]:.1f}{u}</span><span style="color:#94a3b8">{row["Datum"].strftime("%d-%m-%y")}</span></div>'
            return r
        html += f"""<div class="hof-card"><div style="color:{color};font-weight:700;margin-bottom:10px;">{icon} {cat}</div><div class="sec-lbl">Afstand</div>{t3("Afstand_km","km")}<div class="sec-lbl" style="margin-top:10px;">Snelheid</div>{t3("Gem_Snelheid","km/u")}</div>"""
    return html + '</div>'

def generate_logbook(df):
    rows = ""
    for _, r in df.sort_values('Datum', ascending=False).iterrows():
        km = f"{r['Afstand_km']:.1f}" if r['Afstand_km'] > 0 else "-"
        rows += f"<tr><td>{r['Datum'].strftime('%d-%m')}</td><td>{get_sport_style(r['Categorie'])[0]}</td><td>{r['Naam']}</td><td align='right'><strong>{km}</strong></td></tr>"
    return f'<div class="chart-box full-width" style="overflow-x:auto;"><table class="log-table"><thead><tr><th>Datum</th><th>T</th><th>Naam</th><th align="right">km</th></tr></thead><tbody>{rows}</tbody></table></div>'

def generate_kpi(lbl, val, icon, diff_html):
    return f"""<div class="kpi-card"><div style="display:flex;justify-content:space-between;"><div class="lbl" style="font-size:11px;color:#64748b;font-weight:700;">{lbl}</div><div style="font-size:16px;">{icon}</div></div><div class="val" style="font-size:24px;font-weight:800;color:#0f172a;margin:5px 0;">{val}</div><div style="font-size:12px;">{diff_html}</div></div>"""

# --- MAIN ---
def genereer_dashboard():
    print("🚀 Start V61.0 (Kleurrijke Race, Geoptimaliseerde breedte)...")
    try:
        df = pd.read_csv('activities.csv')
        nm = {'Datum van activiteit':'Datum', 'Naam activiteit':'Naam', 'Activiteitstype':'Activiteitstype', 'Beweegtijd':'Beweegtijd_sec', 'Afstand':'Afstand_km', 'Gemiddelde hartslag':'Hartslag', 'Gemiddelde snelheid':'Gem_Snelheid', 'Uitrusting voor activiteit':'Gear', 'Calorieën':'Calorieën'}
        df = df.rename(columns={k:v for k,v in nm.items() if k in df.columns})
        
        for c in ['Afstand_km', 'Beweegtijd_sec', 'Gem_Snelheid', 'Calorieën']:
            if c in df.columns: df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        
        df['Datum'] = df['Datum'].apply(solve_dates); df = df.dropna(subset=['Datum'])
        df['Categorie'] = df.apply(determine_category, axis=1); df['Jaar'] = df['Datum'].dt.year; df['Day'] = df['Datum'].dt.dayofyear
        if df['Gem_Snelheid'].mean() < 10: df['Gem_Snelheid'] *= 3.6
        
        years = sorted(df['Jaar'].unique(), reverse=True)
        nav, sects = "", ""
        
        for yr in years:
            df_yr = df[df['Jaar'] == yr]; df_prev = df[df['Jaar'] == yr-1]
            ytd = datetime.now().timetuple().tm_yday
            df_prev_comp = df_prev[df_prev['Day'] <= ytd] if yr == datetime.now().year else df_prev
            
            # Motivatie reeksen alleen tonen bij huidige jaar tab
            streaks_html = generate_streaks_box(df) if yr == datetime.now().year else ""
            
            sects += f"""<div id="v-{yr}" class="tab-content" style="display:{"block" if yr == datetime.now().year else "none"}">
                <div class="kpi-grid">
                    {generate_kpi("Sessies", len(df_yr), "👟", format_diff_html(len(df_yr), len(df_prev_comp)))}
                    {generate_kpi("Afstand", f"{df_yr['Afstand_km'].sum():,.0f} km", "📏", format_diff_html(df_yr['Afstand_km'].sum(), df_prev_comp['Afstand_km'].sum(), "km"))}
                    {generate_kpi("Tijd", format_time(df_yr['Beweegtijd_sec'].sum()), "⏱️", format_diff_html(df_yr['Beweegtijd_sec'].sum()/3600, df_prev_comp['Beweegtijd_sec'].sum()/3600, "u"))}
                    {generate_kpi("Energie", f"{df_yr['Calorieën'].sum():,.0f} kcal", "🔥", format_diff_html(df_yr['Calorieën'].sum(), df_prev_comp['Calorieën'].sum() if not df_prev_comp.empty else 0, "kcal"))}
                </div>
                {streaks_html}
                {create_ytd_chart(df, yr)}
                <h3 class="sec-sub">Per Sport</h3>{generate_sport_cards(df_yr, df_prev_comp)}
                <h3 class="sec-sub">Materiaal {yr}</h3>{generate_yearly_gear(df_yr, df)}
                <div class="chart-grid">{create_scatter_plot(df_yr)}{create_zone_pie(df_yr)}</div>
                <h3 class="sec-sub">Records {yr}</h3>{generate_hall_of_fame(df_yr)}
                <h3 class="sec-sub">Logboek</h3>{generate_logbook(df_yr)}
            </div>"""
            nav += f'<button class="nav-btn {"active" if yr == datetime.now().year else ""}" onclick="openTab(event, \'v-{yr}\')">{yr}</button>'
            
        nav += '<button class="nav-btn" onclick="openTab(event, \'v-Tot\')">Garage</button>'
        sects += f'<div id="v-Tot" class="tab-content" style="display:none"><h2 class="sec-title">All-Time Garage</h2>{generate_yearly_gear(df, df, True)}<h3 class="sec-sub">All-Time Records</h3>{generate_hall_of_fame(df)}</div>'
        
        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
        :root{{--primary:#0f172a;--bg:#f8fafc;--card:#ffffff;--text:#1e293b;--label:#64748b}}
        body{{font-family:'Poppins',sans-serif;background:var(--bg);color:var(--text);margin:0;padding:20px 0;}}
        .container{{width:96%; max-width:1400px; margin:0 auto;}}
        .nav{{display:flex;gap:8px;overflow-x:auto;padding:10px 0;scrollbar-width:none;position:sticky;top:0;z-index:100;background:var(--bg);}}
        .nav-btn{{font-family:inherit;background:white;border:1px solid #e2e8f0;padding:8px 16px;border-radius:20px;font-size:13px;font-weight:600;cursor:pointer;}}
        .nav-btn.active{{background:var(--primary);color:white;}}
        .kpi-grid, .sport-grid, .hof-grid, .chart-grid {{display:grid; gap:12px; margin-bottom:20px;}}
        .kpi-grid{{grid-template-columns:repeat(2, 1fr);}}
        @media(min-width:768px){{.kpi-grid{{grid-template-columns:repeat(4, 1fr);}}}}
        .sport-grid, .hof-grid{{grid-template-columns:repeat(auto-fit,minmax(280px,1fr));}}
        .chart-grid{{grid-template-columns:repeat(auto-fit,minmax(280px,1fr));}}
        .kpi-card, .sport-card, .hof-card, .chart-box, .streaks-section {{background:white; padding:15px; border-radius:16px; border:1px solid #f1f5f9; box-shadow:0 1px 3px rgba(0,0,0,0.05);}}
        .sec-sub{{font-size:12px;text-transform:uppercase;letter-spacing:1px;margin:30px 0 10px 0;border-bottom:2px solid #f1f5f9;padding-bottom:5px;color:var(--primary);font-weight:800;}}
        .sec-lbl{{font-size:10px;text-transform:uppercase;color:var(--label);font-weight:700;margin-top:5px;}}
        .stat-row{{display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;}}
        .log-table{{width:100%;border-collapse:collapse;font-size:12px;}} .log-table th{{text-align:left;padding:8px;border-bottom:1px solid #eee;color:var(--label);}} .log-table td{{padding:8px;border-bottom:1px solid #f9f9f9;}}
        .streak-row{{display:flex;justify-content:space-between;font-size:16px;font-weight:800;color:var(--primary);}}
        .streak-sub{{font-size:10px;color:var(--label);text-transform:uppercase;}}
        .icon-circle{{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;margin-bottom:10px;}}
        </style></head><body><div class="container">
        <div class="nav">{nav}</div>{sects}</div>
        <script>
        function openTab(e,n){{document.querySelectorAll('.tab-content').forEach(x=>x.style.display='none');document.querySelectorAll('.nav-btn').forEach(x=>x.classList.remove('active'));document.getElementById(n).style.display='block';e.currentTarget.classList.add('active');}}
        </script></body></html>"""
        
        with open('dashboard.html', 'w', encoding='utf-8') as f: f.write(html)
        print("✅ Dashboard (V61.0) klaar!")
    except Exception as e: print(f"❌ Fout: {e}")

if __name__ == "__main__": genereer_dashboard()
