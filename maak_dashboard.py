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
    'primary': '#0f172a', 'gold': '#d4af37', 'bg': '#f8fafc',
    'card': '#ffffff', 'text': '#1e293b', 'text_light': '#64748b',
    'zwift': '#ff6600', 'bike_out': '#0099ff', 'run': '#fbbf24', 
    'swim': '#3b82f6', 'padel': '#84cc16', 'walk': '#10b981', 
    'default': '#64748b', 'ref_gray': '#cbd5e1'
}

# --- DATUM FIX ---
def parse_dutch_date(date_str):
    if pd.isna(date_str) or str(date_str).strip() == "": return pd.NaT
    d_map = {'jan':1, 'feb':2, 'mrt':3, 'mar':3, 'apr':4, 'mei':5, 'may':5, 'jun':6, 'jul':7, 'aug':8, 'sep':9, 'okt':10, 'oct':10, 'nov':11, 'dec':12}
    try:
        s = re.sub(r'[^a-zA-Z0-9: ]', '', str(date_str).lower())
        parts = s.split()
        if len(parts) >= 3:
            day, month_str, year = int(parts[0]), parts[1][:3], int(parts[2])
            return pd.Timestamp(year=year, month=d_map.get(month_str, 1), day=day)
    except: pass
    return pd.to_datetime(date_str, errors='coerce')

# --- CATEGORISERING (STRIKT OP KOLOM) ---
def determine_category(row):
    atype = str(row['Activiteitstype']).lower().strip()
    
    # Zwift (Virtuele rit)
    if 'virtu' in atype or 'zwift' in atype: return 'Zwift'
    
    # Fietsen (Buiten)
    if any(x in atype for x in ['fiets', 'ride', 'gravel', 'mtb', 'cycle', 'wieler', 'velomobiel', 'e-bike']): return 'Fiets'
    
    # Hardlopen
    if any(x in atype for x in ['hardloop', 'run', 'jog']): return 'Hardlopen'
    
    # Padel / Training
    if any(x in atype for x in ['training', 'workout', 'kracht', 'padel', 'fitness', 'gym', 'weight']): return 'Padel'
    
    # Zwemmen
    if 'zwem' in atype or 'swim' in atype: return 'Zwemmen'
    
    # Wandelen
    if any(x in atype for x in ['wandel', 'hike', 'walk']): return 'Wandelen'
    
    return 'Overig'

def get_sport_style(cat):
    styles = {
        'Fiets': {'icon': '🚴', 'color': COLORS['bike_out']},
        'Zwift': {'icon': '👾', 'color': COLORS['zwift']},
        'Hardlopen': {'icon': '🏃', 'color': COLORS['run']},
        'Wandelen': {'icon': '🚶', 'color': COLORS['walk']},
        'Padel': {'icon': '🎾', 'color': COLORS['padel']},
        'Zwemmen': {'icon': '🏊', 'color': COLORS['swim']},
        'Overig': {'icon': '🏅', 'color': COLORS['default']}
    }
    return styles.get(cat, styles['Overig'])

# --- HELPERS ---
def format_time(seconds):
    if pd.isna(seconds) or seconds <= 0: return '-'
    h, r = divmod(int(seconds), 3600); m, _ = divmod(r, 60)
    return f'{h}u {m:02d}m'

def format_diff_html(cur, prev, unit=""):
    if pd.isna(prev) or prev == 0: return '<span style="color:#ccc">-</span>'
    diff = cur - prev
    color = '#10b981' if diff >= 0 else '#ef4444'
    arrow = "▲" if diff >= 0 else "▼"
    return f'<span style="color:{color}; font-weight:700; font-size:0.9em;">{arrow} {abs(diff):.1f} {unit}</span>'

# --- STREAK MET DATUMS ---
def calculate_streaks(df):
    valid = df.dropna(subset=['Datum']).sort_values('Datum')
    if valid.empty: return {}
    
    # --- WEKEN ---
    valid['WeekStart'] = valid['Datum'].dt.to_period('W-MON').dt.start_time
    weeks = sorted(valid['WeekStart'].unique())
    
    cur_wk = 0
    max_wk_val = 0
    max_wk_range = "-"
    
    if weeks:
        # Huidige
        now_wk = pd.Timestamp.now().to_period('W-MON').start_time
        if (now_wk - weeks[-1]).days <= 7:
            cur_wk = 1
            for i in range(len(weeks)-2, -1, -1):
                if (weeks[i+1] - weeks[i]).days == 7: cur_wk += 1
                else: break
        
        # Record met datums
        temp_len = 1
        temp_start = weeks[0]
        
        # Init record met eerste week
        max_wk_val = 1
        max_wk_range = f"({weeks[0].strftime('%d %b %y')})"

        for i in range(1, len(weeks)):
            if (weeks[i] - weeks[i-1]).days == 7:
                temp_len += 1
            else:
                if temp_len > max_wk_val:
                    max_wk_val = temp_len
                    end_date = weeks[i-1] + timedelta(days=6)
                    max_wk_range = f"({temp_start.strftime('%d %b %y')} - {end_date.strftime('%d %b %y')})"
                
                temp_len = 1
                temp_start = weeks[i]
        
        # Check laatste reeks
        if temp_len > max_wk_val:
            max_wk_val = temp_len
            end_date = weeks[-1] + timedelta(days=6)
            max_wk_range = f"({temp_start.strftime('%d %b %y')} - {end_date.strftime('%d %b %y')})"

    # --- DAGEN ---
    days = sorted(valid['Datum'].dt.date.unique())
    cur_day = 0
    max_day_val = 0
    max_day_range = "-"
    
    if days:
        # Huidig
        if (datetime.now().date() - days[-1]).days <= 1:
            cur_day = 1
            for i in range(len(days)-2, -1, -1):
                if (days[i+1] - days[i]).days == 1: cur_day += 1
                else: break
        
        # Record
        temp_len = 1
        temp_start = days[0]
        max_day_val = 1
        max_day_range = f"({days[0].strftime('%d %b')})"
        
        for i in range(1, len(days)):
            if (days[i] - days[i-1]).days == 1:
                temp_len += 1
            else:
                if temp_len > max_day_val:
                    max_day_val = temp_len
                    max_day_range = f"({temp_start.strftime('%d %b')} - {days[i-1].strftime('%d %b %y')})"
                temp_len = 1
                temp_start = days[i]
                
        if temp_len > max_day_val:
            max_day_val = temp_len
            max_day_range = f"({temp_start.strftime('%d %b')} - {days[-1].strftime('%d %b %y')})"

    return {
        'cur_week': cur_wk, 
        'max_week': f"{max_wk_val} weken", 
        'max_week_dates': max_wk_range,
        'cur_day': cur_day,
        'max_day': f"{max_day_val} dagen",
        'max_day_dates': max_day_range
    }

# --- UI GENERATOREN ---
def generate_stats_box(df, current_year):
    df_cur = df[df['Jaar'] == current_year]
    
    b_km = df_cur[df_cur['Categorie'] == 'Fiets']['Afstand_km'].sum()
    z_km = df_cur[df_cur['Categorie'] == 'Zwift']['Afstand_km'].sum()
    r_km = df_cur[df_cur['Categorie'] == 'Hardlopen']['Afstand_km'].sum()
    
    b_pct = min(100, (b_km / GOALS['bike_out']) * 100)
    z_pct = min(100, (z_km / GOALS['zwift']) * 100)
    r_pct = min(100, (r_km / GOALS['run']) * 100)
    
    s = calculate_streaks(df)
    
    return f"""
    <div class="stats-box-container">
        <div class="goals-section">
            <h3 class="box-title">🎯 DOELEN {current_year}</h3>
            <div class="goal-item">
                <div class="goal-label"><span>🚴 Buiten: {b_km:.0f} / {GOALS['bike_out']} km</span><span>{b_pct:.1f}%</span></div>
                <div class="goal-bar"><div style="width:{b_pct}%; background:{COLORS['bike_out']};"></div></div>
            </div>
            <div class="goal-item">
                <div class="goal-label"><span>👾 Zwift: {z_km:.0f} / {GOALS['zwift']} km</span><span>{z_pct:.1f}%</span></div>
                <div class="goal-bar"><div style="width:{z_pct}%; background:{COLORS['zwift']};"></div></div>
            </div>
            <div class="goal-item">
                <div class="goal-label"><span>🏃 Lopen: {r_km:.0f} / {GOALS['run']} km</span><span>{r_pct:.1f}%</span></div>
                <div class="goal-bar"><div style="width:{r_pct}%; background:{COLORS['run']};"></div></div>
            </div>
        </div>
        <div class="streaks-section">
            <h3 class="box-title">🔥 REEKSEN</h3>
            <div class="streak-row"><span class="label">Huidig Wekelijks:</span><span class="val">{s['cur_week']} weken</span></div>
            <div class="streak-row"><span class="label">Record Wekelijks:</span><span class="val">{s['max_week']}</span></div>
            <div class="streak-sub">{s['max_week_dates']}</div>
            <div style="height:10px"></div>
            <div class="streak-row"><span class="label">Huidig Dagelijks:</span><span class="val">{s['cur_day']} dagen</span></div>
            <div class="streak-row"><span class="label">Record Dagelijks:</span><span class="val">{s['max_day']}</span></div>
            <div class="streak-sub">{s['max_day_dates']}</div>
        </div>
    </div>"""

def generate_sport_cards(df_yr, df_prev_comp):
    html = '<div class="sport-grid">'
    categories = sorted(df_yr['Categorie'].unique())
    for cat in categories:
        df_s = df_yr[df_yr['Categorie'] == cat]
        df_p = df_prev_comp[df_prev_comp['Categorie'] == cat] if df_prev_comp is not None else pd.DataFrame()
        if df_s.empty: continue
        
        style = get_sport_style(cat)
        n_sessies = len(df_s); n_prev = len(df_p)
        dist = df_s['Afstand_km'].sum(); dist_p = df_p['Afstand_km'].sum() if not df_p.empty else 0
        tijd = df_s['Beweegtijd_sec'].sum()
        hr = df_s['Hartslag'].mean()
        
        spd_val = "-"
        if cat == 'Hardlopen' and dist > 0: spd_val = f"{int((tijd/dist)//60)}:{int((tijd/dist)%60):02d} /km"
        elif tijd > 0: spd_val = f"{(dist/(tijd/3600)):.1f} km/u"

        dist_row = f'<div class="stat-row"><span>Afstand</span> <div class="val-group"><strong>{dist:,.0f} km</strong> {format_diff_html(dist, dist_p)}</div></div>' if cat not in ['Padel', 'Overig'] else ""
        hr_row = f'<div class="stat-row"><span>Hartslag</span> <strong class="hr-blur">❤️ {hr:.0f}</strong></div>' if pd.notna(hr) else ""

        html += f"""<div class="sport-card">
            <div class="sport-header" style="color:{style['color']}"><div class="icon-circle" style="background:{style['color']}15">{style['icon']}</div><h3>{cat}</h3></div>
            <div class="sport-body">
                <div class="stat-row"><span>Sessies</span> <div class="val-group"><strong>{n_sessies}</strong> {format_diff_html(n_sessies, n_prev)}</div></div>
                <div class="stat-row"><span>Tijd</span> <strong>{format_time(tijd)}</strong></div>
                {dist_row}
                <div class="stat-row"><span>Snelheid</span> <strong>{spd_val}</strong></div>
                {hr_row}
            </div>
        </div>"""
    return html + '</div>'

def generate_hall_of_fame(df):
    html = '<div class="hof-grid">'
    df_hof = df.dropna(subset=['Datum']).copy()
    for cat in ['Fiets', 'Zwift', 'Hardlopen']:
        df_s = df_hof[df_hof['Categorie'] == cat].copy()
        if df_s.empty: continue
        style = get_sport_style(cat)
        def top3(col, unit, is_pace=False):
            d_sorted = df_s.sort_values(col, ascending=False).head(3)
            res = ""
            for i, (_, r) in enumerate(d_sorted.iterrows()):
                v = r[col]
                val = f"{v:.1f}{unit}" if not is_pace else f"{int((3600/v)//60)}:{int((3600/v)%60):02d}/km"
                res += f'<div class="top3-item"><span>{"🥇🥈🥉"[i]} {val}</span><span class="date">{r["Datum"].strftime("%d-%m-%y")}</span></div>'
            return res
        html += f"""<div class="hof-card"><div class="hof-header" style="color:{style['color']}">{style['icon']} {cat}</div><div class="hof-sec"><div class="sec-lbl">Langste</div>{top3('Afstand_km', 'km')}</div><div class="hof-sec"><div class="sec-lbl">Snelste</div>{top3('Gem_Snelheid', 'km/u', cat=='Hardlopen')}</div></div>"""
    return html + '</div>'

def create_monthly_charts(df_cur, df_prev, year):
    months = ['Jan','Feb','Mrt','Apr','Mei','Jun','Jul','Aug','Sep','Okt','Nov','Dec']
    def make_chart(cat, title, color):
        c_m = df_cur[df_cur['Categorie'] == cat].groupby(df_cur['Datum'].dt.month)['Afstand_km'].sum().reindex(range(1,13), fill_value=0)
        p_m = df_prev[df_prev['Categorie'] == cat].groupby(df_prev['Datum'].dt.month)['Afstand_km'].sum().reindex(range(1,13), fill_value=0)
        if c_m.sum() == 0 and p_m.sum() == 0: return ""
        f = go.Figure()
        f.add_trace(go.Bar(x=months, y=p_m, name=f"{year-1}", marker_color=COLORS['ref_gray']))
        f.add_trace(go.Bar(x=months, y=c_m, name=f"{year}", marker_color=color))
        f.update_layout(title=title, template='plotly_white', barmode='group', margin=dict(t=40,b=20,l=20,r=20), height=220, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=True, legend=dict(orientation="h", y=1.1))
        return f'<div class="chart-box full-width">{f.to_html(full_html=False, include_plotlyjs="cdn")}</div>'
    
    return f"""{make_chart('Fiets', '🚴 Fietsen Buiten (km)', COLORS['bike_out'])}
               <div style="height:15px"></div>
               {make_chart('Zwift', '👾 Zwift (km)', COLORS['zwift'])}
               <div style="height:15px"></div>
               {make_chart('Hardlopen', '🏃 Hardlopen (km)', COLORS['run'])}"""

def generate_gear_section(df):
    dfg = df.dropna(subset=['Gear']).copy()
    dfg = dfg[dfg['Gear'].str.strip() != '']
    if dfg.empty: return "<p>Geen data</p>"
    stats = dfg.groupby('Gear').agg(Count=('Categorie','count'), Km=('Afstand_km','sum'), Type=('Categorie', lambda x: x.mode()[0])).reset_index().sort_values('Km', ascending=False)
    html = '<div class="kpi-grid">'
    for _, r in stats.iterrows():
        icon = '🚲' if r['Type'] in ['Fiets', 'Zwift'] else '👟'
        html += f"""<div class="kpi-card" style="padding:15px;"><div style="display:flex;align-items:center;gap:10px;margin-bottom:8px"><span style="font-size:20px;">{icon}</span><strong style="font-size:13px;">{r['Gear']}</strong></div><div style="font-size:18px;font-weight:700;color:{COLORS['primary']}">{r['Km']:,.0f} km</div><div style="font-size:11px;color:{COLORS['text_light']}">{r['Count']} act.</div></div>"""
    return html + "</div>"

def generate_kpi(lbl, val, icon, diff_html):
    return f"""<div class="kpi-card"><div style="display:flex;justify-content:space-between;"><div style="font-size:11px;color:#64748b;font-weight:700;text-transform:uppercase">{lbl}</div><div style="font-size:16px;">{icon}</div></div><div style="font-size:24px;font-weight:700;color:#0f172a;margin:5px 0">{val}</div><div style="font-size:12px;">{diff_html}</div></div>"""

# --- MAIN ---
def genereer_dashboard():
    print("🚀 Start V44.0 (Zwift, Streaks & Lopen Fix)...")
    try:
        df = pd.read_csv('activities.csv')
        nm = {'Datum van activiteit':'Datum', 'Naam activiteit':'Naam', 'Activiteitstype':'Activiteitstype', 
              'Beweegtijd':'Beweegtijd_sec', 'Afstand':'Afstand_km', 'Gemiddelde hartslag':'Hartslag', 
              'Gemiddelde snelheid':'Gem_Snelheid', 'Uitrusting voor activiteit':'Gear'}
        df = df.rename(columns={k:v for k,v in nm.items() if k in df.columns})
        
        for c in ['Afstand_km', 'Beweegtijd_sec', 'Gem_Snelheid']:
            if c in df.columns: df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        df['Hartslag'] = pd.to_numeric(df['Hartslag'], errors='coerce')
        
        df['Datum'] = df['Datum'].apply(parse_dutch_date)
        df = df.dropna(subset=['Datum'])
        df['Categorie'] = df.apply(determine_category, axis=1)
        df['Jaar'] = df['Datum'].dt.year
        df['Day'] = df['Datum'].dt.dayofyear
        if df['Gem_Snelheid'].mean() < 10: df['Gem_Snelheid'] *= 3.6
        
        print(f"✅ Data geladen. Sessies in 2025: {len(df[df['Jaar']==2025])}")
        
        years = sorted(df['Jaar'].unique(), reverse=True)
        nav, sects = "", ""
        stats_box = generate_stats_box(df, datetime.now().year)
        
        for yr in years:
            df_yr = df[df['Jaar'] == yr]
            df_prev = df[df['Jaar'] == yr-1]
            ytd = datetime.now().timetuple().tm_yday
            df_prev_comp = df_prev[df_prev['Day'] <= ytd] if yr == datetime.now().year else df_prev
            nav += f'<button class="nav-btn {"active" if yr == datetime.now().year else ""}" onclick="openTab(event, \'v-{yr}\')">{yr}</button>'
            sects += f"""<div id="v-{yr}" class="tab-content" style="display:{"block" if yr == datetime.now().year else "none"}"><h2 class="sec-title">Overzicht {yr}</h2><div class="kpi-grid">{generate_kpi("Sessies", len(df_yr), "🔥", format_diff_html(len(df_yr), len(df_prev_comp)))}{generate_kpi("Totaal Afstand", f"{df_yr['Afstand_km'].sum():,.0f} km", "📏", format_diff_html(df_yr['Afstand_km'].sum(), df_prev_comp['Afstand_km'].sum(), "km"))}{generate_kpi("Tijd", format_time(df_yr['Beweegtijd_sec'].sum()), "⏱️", "")}</div><h3 class="sec-sub">Stats per Sport</h3>{generate_sport_cards(df_yr, df_prev_comp)}<h3 class="sec-sub">Maandelijkse Voortgang</h3>{create_monthly_charts(df_yr, df_prev, yr)}<h3 class="sec-sub">Records {yr}</h3>{generate_hall_of_fame(df_yr)}</div>"""
            
        nav += '<button class="nav-btn" onclick="openTab(event, \'v-Tot\')">Carrière</button>'
        sects += f'<div id="v-Tot" class="tab-content" style="display:none"><h2 class="sec-title">All-Time Records</h2>{generate_hall_of_fame(df)}<h2 class="sec-title" style="margin-top:30px">De Garage</h2>{generate_gear_section(df)}</div>'
        
        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Sportoverzicht Jorden</title><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet"><style>
        :root{{--primary:#0f172a;--bg:#f8fafc;--card:#ffffff;--text:#1e293b;--label:#94a3b8}}
        body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);margin:0;padding:15px;padding-bottom:60px}}
        .container{{max-width:800px;margin:0 auto}}
        .header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}}
        .lock-btn{{background:white;border:1px solid #cbd5e1;padding:6px 12px;border-radius:20px;cursor:pointer}}
        .hr-blur{{filter:blur(5px);transition:0.3s}}
        .gold-banner{{background:linear-gradient(135deg, #d4af37 0%, #f59e0b 100%);color:white;padding:15px;border-radius:12px;margin-bottom:20px;font-weight:700;display:flex;align-items:center;cursor:pointer}}
        .nav{{display:flex;gap:8px;overflow-x:auto;margin-bottom:20px;padding-bottom:5px;scrollbar-width:none}}
        .nav-btn{{flex:0 0 auto;background:white;border:1px solid #e2e8f0;padding:8px 16px;border-radius:20px;font-size:13px;font-weight:600;color:#64748b;cursor:pointer}}
        .nav-btn.active{{background:var(--primary);color:white;border-color:var(--primary)}}
        .stats-box-container{{display:flex;gap:15px;margin-bottom:25px;flex-wrap:wrap}}
        .goals-section, .streaks-section{{flex:1;background:white;padding:15px;border-radius:16px;border:1px solid #e2e8f0;min-width:280px}}
        .box-title{{font-size:11px;color:var(--label);text-transform:uppercase;margin-bottom:12px;letter-spacing:1px;font-weight:700}}
        .goal-item{{margin-bottom:10px}}.goal-label{{display:flex;justify-content:space-between;font-size:12px;font-weight:600;margin-bottom:4px}}
        .goal-bar{{background:#f1f5f9;height:6px;border-radius:3px;overflow:hidden}}.goal-bar div{{height:100%;border-radius:3px}}
        .streak-row{{display:flex;justify-content:space-between;margin-bottom:4px;font-size:13px}}.streak-row .val{{font-weight:700;color:var(--primary)}}
        .streak-sub{{font-size:10px;color:var(--label);text-align:right;font-style:italic}}
        .kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:10px;margin-bottom:25px}}
        .kpi-card{{background:white;padding:15px;border-radius:16px;border:1px solid #e2e8f0}}
        .sport-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:15px;margin-bottom:25px}}
        .sport-card{{background:white;padding:15px;border-radius:16px;border:1px solid #e2e8f0}}
        .sport-header{{display:flex;align-items:center;gap:10px;margin-bottom:12px;font-size:16px}}
        .icon-circle{{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center}}
        .stat-row{{display:flex;justify-content:space-between;margin-bottom:6px;font-size:13px;color:#64748b}}
        .stat-row strong{{color:var(--text)}} .val-group{{display:flex;gap:6px;align-items:center}}
        .hof-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin-bottom:20px}}
        .hof-card{{background:white;padding:15px;border-radius:16px;border:1px solid #e2e8f0}}
        .hof-sec{{margin-bottom:12px}} .sec-lbl{{font-size:9px;color:var(--label);text-transform:uppercase;font-weight:700;margin-bottom:4px}}
        .top3-item{{display:flex;justify-content:space-between;font-size:12px;margin-bottom:2px}}
        .medal{{margin-right:5px}} .t3-val{{font-weight:600}} .t3-date{{color:var(--label);font-size:10px}}
        .sec-title{{font-size:20px;font-weight:700;margin-bottom:15px}}
        .sec-sub{{font-size:12px;color:var(--label);text-transform:uppercase;font-weight:700;margin:25px 0 10px 0;letter-spacing:1px}}
        .chart-box{{background:white;padding:15px;border-radius:16px;border:1px solid #e2e8f0}}
        .full-width{{width:100%;box-sizing:border-box}}
        </style></head><body><div class="container">
        <div class="header"><h1 style="font-size:22px;margin:0">Sportoverzicht Jorden</h1><button class="lock-btn" onclick="unlock()">❤️ 🔒</button></div>
        <div class="gold-banner" onclick="window.location.reload()">🏆 Eregalerij & Records</div>
        {stats_box}<div class="nav">{nav}</div>{sects}</div>
        <script>
        function openTab(e,n){{document.querySelectorAll('.tab-content').forEach(x=>x.style.display='none');document.querySelectorAll('.nav-btn').forEach(x=>x.classList.remove('active'));document.getElementById(n).style.display='block';e.currentTarget.classList.add('active');}}
        function unlock(){{if(prompt("Wachtwoord:")==='Nala'){{document.querySelectorAll('.hr-blur').forEach(e=>e.classList.remove('hr-blur'));document.querySelector('.lock-btn').style.display='none';}}}}
        </script></body></html>"""
        
        with open('dashboard.html', 'w', encoding='utf-8') as f: f.write(html)
        print("✅ Dashboard (V44.0) gegenereerd!")

    except Exception as e:
        print(f"❌ Fout: {e}")

if __name__ == "__main__":
    genereer_dashboard()
