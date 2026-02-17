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

# Pas deze grenzen aan op basis van jouw eigen hartslagzones!
HR_ZONES = {
    'Z1 Herstel': 135,   # Alles onder 135
    'Z2 Duur': 152,      # 135 - 152
    'Z3 Tempo': 168,     # 153 - 168
    'Z4 Drempel': 180,   # 169 - 180
    'Z5 Max': 220        # Alles boven 180
}

COLORS = {
    'primary': '#0f172a', 'gold': '#d4af37', 'bg': '#f1f5f9',
    'card': '#ffffff', 'text': '#1e293b', 'text_light': '#64748b',
    'zwift': '#ff6600', 'bike_out': '#0099ff', 'run': '#fbbf24', 
    'swim': '#3b82f6', 'padel': '#84cc16', 'walk': '#10b981', 
    'strength': '#8b5cf6', 'default': '#64748b', 'ref_gray': '#cbd5e1',
    # Zone kleuren
    'z1': '#a3e635', 'z2': '#facc15', 'z3': '#fb923c', 'z4': '#f87171', 'z5': '#ef4444'
}

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
    t = str(row['Activiteitstype']).lower().strip()
    n = str(row['Naam']).lower().strip()
    
    if any(x in t for x in ['kracht', 'power', 'gym', 'fitness', 'weight']) or \
       any(x in n for x in ['kracht', 'power', 'gym', 'fitness']): return 'Krachttraining'
    if 'virtu' in t or 'zwift' in n: return 'Zwift'
    if any(x in t for x in ['fiets', 'ride', 'gravel', 'mtb', 'cycle', 'wieler', 'velomobiel', 'e-bike']): return 'Fiets'
    if any(x in t for x in ['hardloop', 'run', 'jog', 'lopen', 'loop']): return 'Hardlopen'
    if 'zwem' in t: return 'Zwemmen'
    if any(x in t for x in ['wandel', 'hike', 'walk']): return 'Wandelen'
    if any(x in t for x in ['padel', 'tennis', 'squash']): return 'Padel'
    if any(x in t for x in ['train', 'work', 'fit']): return 'Padel' 
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
    if pd.isna(prev) and cur == 0: return '<span style="color:#ccc">-</span>'
    diff = cur - (prev if pd.notna(prev) else 0)
    color = '#10b981' if diff >= 0 else '#ef4444'
    arrow = "▲" if diff >= 0 else "▼"
    return f'<span style="color:{color}; font-weight:700; font-size:0.9em;">{arrow} {abs(diff):.1f} {unit}</span>'

# --- GRAFIEKEN & VISUALISATIES ---

def generate_ytd_history(df, current_year):
    is_current_active_year = (current_year == datetime.now().year)
    day_limit = datetime.now().timetuple().tm_yday if is_current_active_year else 366
    html = f"""<div class="chart-box full-width" style="margin-bottom:20px;">
        <h3 style="margin-top:0; margin-bottom:15px; font-size:16px;">📅 Verloop t.o.v. Vorige Jaren (Dezelfde Periode)</h3>
        <table class="history-table"><thead><tr><th>Jaar</th><th>Afstand</th><th>Tijd</th><th>Sessies</th></tr></thead><tbody>"""
    max_km = 0; history_data = []
    for y in range(current_year, current_year - 6, -1):
        df_y = df[df['Jaar'] == y]; df_y_ytd = df_y[df_y['Day'] <= day_limit]
        km = df_y_ytd['Afstand_km'].sum(); sec = df_y_ytd['Beweegtijd_sec'].sum(); count = len(df_y_ytd)
        if km > max_km: max_km = km
        history_data.append((y, km, sec, count))
    for y, km, sec, count in history_data:
        bar_w = (km / max_km * 100) if max_km > 0 else 0
        is_curr = (y == current_year)
        row_style = "font-weight:bold; background:#f8fafc;" if is_curr else ""
        bar_color = COLORS['primary'] if is_curr else '#cbd5e1'
        html += f"""<tr style="{row_style}"><td style="width:60px;">{y}</td><td><div style="display:flex; align-items:center; gap:10px;"><span style="width:70px; text-align:right;">{km:,.0f} km</span><div style="flex:1; background:#f1f5f9; height:8px; border-radius:4px; max-width:150px;"><div style="width:{bar_w}%; background:{bar_color}; height:100%; border-radius:4px;"></div></div></div></td><td style="width:80px; text-align:right;">{(sec/3600):.1f} uur</td><td style="width:60px; text-align:right;">{count}</td></tr>"""
    return html + "</tbody></table></div>"

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
        if (datetime.now().date() - days[-1]).days <= 1:
            cur_d = 1
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

def generate_stats_box(df, current_year):
    df_cur = df[df['Jaar'] == current_year]
    b_km = df_cur[df_cur['Categorie'] == 'Fiets']['Afstand_km'].sum()
    z_km = df_cur[df_cur['Categorie'] == 'Zwift']['Afstand_km'].sum()
    r_km = df_cur[df_cur['Categorie'] == 'Hardlopen']['Afstand_km'].sum()
    b_pct, z_pct, r_pct = min(100, (b_km/GOALS['bike_out'])*100), min(100, (z_km/GOALS['zwift'])*100), min(100, (r_km/GOALS['run'])*100)
    s = calculate_streaks(df)
    return f"""<div class="stats-box-container"><div class="goals-section"><h3 class="box-title">🎯 DOELEN {current_year}</h3><div class="goal-item"><div class="goal-label"><span>🚴 Buiten: {b_km:.0f}/{GOALS['bike_out']}km</span><span>{b_pct:.1f}%</span></div><div class="goal-bar"><div style="width:{b_pct}%; background:{COLORS['bike_out']};"></div></div></div><div class="goal-item"><div class="goal-label"><span>👾 Zwift: {z_km:.0f}/{GOALS['zwift']}km</span><span>{z_pct:.1f}%</span></div><div class="goal-bar"><div style="width:{z_pct}%; background:{COLORS['zwift']};"></div></div></div><div class="goal-item"><div class="goal-label"><span>🏃 Lopen: {r_km:.0f}/{GOALS['run']}km</span><span>{r_pct:.1f}%</span></div><div class="goal-bar"><div style="width:{r_pct}%; background:{COLORS['run']};"></div></div></div></div><div class="streaks-section"><h3 class="box-title">🔥 REEKSEN</h3><div class="streak-row"><span class="label">Huidig Wekelijks:</span><span class="val">{s['cur_week']} weken</span></div><div class="streak-row"><span class="label">Record Wekelijks:</span><span class="val">{s['max_week']} weken</span></div><div class="streak-sub">{s['max_week_dates']}</div><div style="height:10px"></div><div class="streak-row"><span class="label">Huidig Dagelijks:</span><span class="val">{s['cur_day']} dagen</span></div><div class="streak-row"><span class="label">Record Dagelijks:</span><span class="val">{s['max_day']} dagen</span></div><div class="streak-sub">{s['max_day_dates']}</div></div></div>"""

# --- INTERACTIEVE SCATTER PLOT (MET FILTER) ---
def create_scatter_plot(df_yr):
    # Data voorbereiden voor de 3 hoofdsporten
    df_bike = df_yr[df_yr['Categorie'] == 'Fiets']
    df_zwift = df_yr[df_yr['Categorie'] == 'Zwift']
    df_run = df_yr[df_yr['Categorie'] == 'Hardlopen']

    fig = go.Figure()

    # Trace 0: Fiets
    fig.add_trace(go.Scatter(
        x=df_bike['Afstand_km'], y=df_bike['Gem_Snelheid'], mode='markers',
        name='Fiets', marker=dict(color=COLORS['bike_out'], size=8, opacity=0.6),
        text=df_bike['Naam'] + " (" + df_bike['Datum'].dt.strftime('%d-%m') + ")",
        visible=True # Default visible
    ))

    # Trace 1: Zwift
    fig.add_trace(go.Scatter(
        x=df_zwift['Afstand_km'], y=df_zwift['Gem_Snelheid'], mode='markers',
        name='Zwift', marker=dict(color=COLORS['zwift'], size=8, opacity=0.6),
        text=df_zwift['Naam'] + " (" + df_zwift['Datum'].dt.strftime('%d-%m') + ")",
        visible=True
    ))

    # Trace 2: Hardlopen
    fig.add_trace(go.Scatter(
        x=df_run['Afstand_km'], y=df_run['Gem_Snelheid'], mode='markers',
        name='Hardlopen', marker=dict(color=COLORS['run'], size=8, opacity=0.6),
        text=df_run['Naam'] + " (" + df_run['Datum'].dt.strftime('%d-%m') + ")",
        visible=True
    ))

    # Dropdown menu configuratie
    updatemenus = [dict(
        active=0,
        buttons=list([
            dict(label="Alle Sporten",
                 method="update",
                 args=[{"visible": [True, True, True]},
                       {"title": "⚡ Snelheid vs. Afstand (Alles)"}]),
            dict(label="🚴 Fietsen",
                 method="update",
                 args=[{"visible": [True, False, False]},
                       {"title": "⚡ Snelheid vs. Afstand (Fietsen)"}]),
            dict(label="👾 Zwift",
                 method="update",
                 args=[{"visible": [False, True, False]},
                       {"title": "⚡ Snelheid vs. Afstand (Zwift)"}]),
            dict(label="🏃 Hardlopen",
                 method="update",
                 args=[{"visible": [False, False, True]},
                       {"title": "⚡ Snelheid vs. Afstand (Hardlopen)"}]),
        ]),
        direction="down", pad={"r": 10, "t": 10}, showactive=True,
        x=1, xanchor="right", y=1.2, yanchor="top"
    )]

    fig.update_layout(
        title='⚡ Snelheid vs. Afstand', 
        template='plotly_white',
        updatemenus=updatemenus,
        margin=dict(t=50,b=20,l=20,r=20), height=350, 
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis_title="Afstand (km)", yaxis_title="Snelheid (km/u)",
        legend=dict(orientation="h", y=-0.2)
    )
    return f'<div class="chart-box full-width">{fig.to_html(full_html=False, include_plotlyjs="cdn")}</div>'

# --- INTERACTIEVE ZONE PIE CHART (MET FILTER) ---
def create_zone_pie(df_yr):
    df_hr = df_yr[(df_yr['Hartslag'] > 0) & (df_yr['Hartslag'].notna())].copy()
    if df_hr.empty: return ""
    df_hr['Zone'] = df_hr['Hartslag'].apply(determine_zone)
    
    color_map = {'Z1 Herstel': COLORS['z1'], 'Z2 Duur': COLORS['z2'], 'Z3 Tempo': COLORS['z3'], 
                 'Z4 Drempel': COLORS['z4'], 'Z5 Max': COLORS['z5'], 'Onbekend': '#ccc'}
    zone_order = ['Z1 Herstel', 'Z2 Duur', 'Z3 Tempo', 'Z4 Drempel', 'Z5 Max']

    # Helper voor tellen
    def get_counts(sub_df):
        c = sub_df['Zone'].value_counts().reindex(zone_order, fill_value=0).reset_index()
        c.columns = ['Zone', 'Count']
        return c[c['Count'] > 0]

    all_counts = get_counts(df_hr)
    bike_counts = get_counts(df_hr[df_hr['Categorie'] == 'Fiets'])
    zwift_counts = get_counts(df_hr[df_hr['Categorie'] == 'Zwift'])
    run_counts = get_counts(df_hr[df_hr['Categorie'] == 'Hardlopen'])

    fig = go.Figure()

    # Trace 0: Alle
    fig.add_trace(go.Pie(labels=all_counts['Zone'], values=all_counts['Count'], name="Totaal", marker_colors=[color_map[z] for z in all_counts['Zone']], hole=0.5, visible=True))
    # Trace 1: Fiets
    fig.add_trace(go.Pie(labels=bike_counts['Zone'], values=bike_counts['Count'], name="Fiets", marker_colors=[color_map[z] for z in bike_counts['Zone']], hole=0.5, visible=False))
    # Trace 2: Zwift
    fig.add_trace(go.Pie(labels=zwift_counts['Zone'], values=zwift_counts['Count'], name="Zwift", marker_colors=[color_map[z] for z in zwift_counts['Zone']], hole=0.5, visible=False))
    # Trace 3: Run
    fig.add_trace(go.Pie(labels=run_counts['Zone'], values=run_counts['Count'], name="Run", marker_colors=[color_map[z] for z in run_counts['Zone']], hole=0.5, visible=False))

    updatemenus = [dict(
        active=0,
        buttons=list([
            dict(label="Alle Sporten", method="update", args=[{"visible": [True, False, False, False]}, {"title": "❤️ Intensiteit (Alle)"}]),
            dict(label="🚴 Fietsen", method="update", args=[{"visible": [False, True, False, False]}, {"title": "❤️ Intensiteit (Fietsen)"}]),
            dict(label="👾 Zwift", method="update", args=[{"visible": [False, False, True, False]}, {"title": "❤️ Intensiteit (Zwift)"}]),
            dict(label="🏃 Hardlopen", method="update", args=[{"visible": [False, False, False, True]}, {"title": "❤️ Intensiteit (Hardlopen)"}]),
        ]),
        direction="down", pad={"r": 10, "t": 10}, showactive=True, x=1, xanchor="right", y=1.2, yanchor="top"
    )]

    fig.update_layout(title='❤️ Training Intensiteit', template='plotly_white', updatemenus=updatemenus, margin=dict(t=50,b=20,l=20,r=20), height=350, paper_bgcolor='rgba(0,0,0,0)')
    return f'<div class="chart-box full-width">{fig.to_html(full_html=False, include_plotlyjs="cdn")}</div>'

def create_heatmap(df_yr):
    df_hm = df_yr.copy()
    df_hm['Uur'] = df_hm['Datum'].dt.hour
    df_hm['Weekdag'] = df_hm['Datum'].dt.day_name()
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    nl_days = {'Monday':'Ma', 'Tuesday':'Di', 'Wednesday':'Wo', 'Thursday':'Do', 'Friday':'Vr', 'Saturday':'Za', 'Sunday':'Zo'}
    grouped = df_hm.groupby(['Weekdag', 'Uur']).size().reset_index(name='Aantal')
    pivot = grouped.pivot(index='Uur', columns='Weekdag', values='Aantal').fillna(0)
    pivot = pivot.reindex(columns=days_order)
    if pivot.empty: return ""
    fig = go.Figure(data=go.Heatmap(z=pivot.values, x=[nl_days[d] for d in pivot.columns], y=pivot.index, colorscale='Greens', showscale=False))
    fig.update_layout(title='📅 Trainingsmomenten', template='plotly_white', margin=dict(t=40,b=20,l=20,r=20), height=300, paper_bgcolor='rgba(0,0,0,0)', yaxis=dict(title='Uur van de dag', range=[6, 23]))
    return f'<div class="chart-box full-width">{fig.to_html(full_html=False, include_plotlyjs="cdn")}</div>'

def create_strength_freq_chart(df_yr):
    df_s = df_yr[df_yr['Categorie'] == 'Krachttraining']
    if df_s.empty: return ""
    counts = df_s.groupby(df_s['Datum'].dt.month).size().reindex(range(1,13), fill_value=0)
    months = ['Jan','Feb','Mrt','Apr','Mei','Jun','Jul','Aug','Sep','Okt','Nov','Dec']
    fig = go.Figure()
    fig.add_trace(go.Bar(x=months, y=counts, name="Sessies", marker_color=COLORS['strength'], text=counts, textposition='auto'))
    fig.add_shape(type="line", x0=-0.5, y0=8, x1=11.5, y1=8, line=dict(color="gray", width=2, dash="dot"))
    fig.update_layout(title='🏋️ Kracht Frequentie (Sessies per Maand)', template='plotly_white', margin=dict(t=40,b=20,l=20,r=20), height=300, paper_bgcolor='rgba(0,0,0,0)', yaxis=dict(title='Aantal Sessies'))
    return f'<div class="chart-box full-width">{fig.to_html(full_html=False, include_plotlyjs="cdn")}</div>'

def create_monthly_charts(df_cur, df_prev, year):
    months = ['Jan','Feb','Mrt','Apr','Mei','Jun','Jul','Aug','Sep','Okt','Nov','Dec']
    def get_month_data(df, categories):
        mask = df['Categorie'].isin(categories)
        return df[mask].groupby(df['Datum'].dt.month)['Afstand_km'].sum().reindex(range(1,13), fill_value=0)
    prev_total = get_month_data(df_prev, ['Fiets', 'Zwift'])
    cur_zwift = get_month_data(df_cur, ['Zwift']); cur_out = get_month_data(df_cur, ['Fiets'])
    fig_bike = go.Figure()
    fig_bike.add_trace(go.Bar(x=months, y=prev_total, name=f"{year-1}", marker_color=COLORS['ref_gray'], offsetgroup=1))
    fig_bike.add_trace(go.Bar(x=months, y=cur_zwift, name=f"{year} Zwift", marker_color=COLORS['zwift'], offsetgroup=2))
    fig_bike.add_trace(go.Bar(x=months, y=cur_out, name=f"{year} Buiten", marker_color=COLORS['bike_out'], base=cur_zwift, offsetgroup=2))
    fig_bike.update_layout(title='🚴 Fietsen Totaal (km)', template='plotly_white', barmode='group', margin=dict(t=40,b=20,l=20,r=20), height=300, paper_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=1.1))
    prev_run = get_month_data(df_prev, ['Hardlopen']); cur_run = get_month_data(df_cur, ['Hardlopen'])
    fig_run = go.Figure()
    fig_run.add_trace(go.Bar(x=months, y=prev_run, name=f"{year-1}", marker_color=COLORS['ref_gray']))
    fig_run.add_trace(go.Bar(x=months, y=cur_run, name=f"{year}", marker_color=COLORS['run']))
    fig_run.update_layout(title='🏃 Hardlopen (km)', template='plotly_white', barmode='group', margin=dict(t=40,b=20,l=20,r=20), height=300, paper_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=1.1))
    return f'<div class="chart-grid"><div class="chart-box full-width">{fig_bike.to_html(full_html=False, include_plotlyjs="cdn")}</div><div class="chart-box full-width">{fig_run.to_html(full_html=False, include_plotlyjs="cdn")}</div></div>'

def generate_sport_cards(df_yr, df_prev_comp):
    html = '<div class="sport-grid">'
    cats_present = df_yr['Categorie'].unique()
    custom_order = ['Fiets', 'Zwift', 'Hardlopen', 'Krachttraining', 'Padel', 'Wandelen', 'Zwemmen', 'Overig']
    sorted_cats = [c for c in custom_order if c in cats_present] + [c for c in cats_present if c not in custom_order]
    for cat in sorted_cats:
        df_s = df_yr[df_yr['Categorie'] == cat]
        df_p = df_prev_comp[df_prev_comp['Categorie'] == cat] if df_prev_comp is not None else pd.DataFrame()
        if df_s.empty: continue
        icon, color = get_sport_style(cat)
        n_sessies = len(df_s); n_prev = len(df_p)
        dist = df_s['Afstand_km'].sum(); dist_p = df_p['Afstand_km'].sum() if not df_p.empty else 0
        tijd = df_s['Beweegtijd_sec'].sum(); tijd_p = df_p['Beweegtijd_sec'].sum() if not df_p.empty else 0
        hr = df_s['Hartslag'].mean(); watt = df_s['Wattage'].mean() if 'Wattage' in df_s.columns else None
        spd_val = "-"
        if cat == 'Hardlopen' and dist > 0: spd_val = f"{int((tijd/dist)//60)}:{int((tijd/dist)%60):02d} /km"
        elif tijd > 0 and cat not in ['Padel', 'Krachttraining']: spd_val = f"{(dist/(tijd/3600)):.1f} km/u"
        rows = f"""<div class="stat-row"><span>Sessies</span> <div class="val-group"><strong>{n_sessies}</strong> {format_diff_html(n_sessies, n_prev)}</div></div><div class="stat-row"><span>Tijd</span> <div class="val-group"><strong>{format_time(tijd)}</strong> {format_diff_html(tijd/3600, tijd_p/3600, "u")}</div></div>"""
        if cat not in ['Padel', 'Krachttraining']: rows += f"""<div class="stat-row"><span>Afstand</span> <div class="val-group"><strong>{dist:,.0f} km</strong> {format_diff_html(dist, dist_p)}</div></div><div class="stat-row"><span>Snelheid</span> <strong>{spd_val}</strong></div>"""
        if cat == 'Zwift' and pd.notna(watt) and watt > 0: rows += f'<div class="stat-row"><span>Wattage</span> <strong>⚡ {watt:.0f} W</strong></div>'
        if pd.notna(hr): rows += f'<div class="stat-row"><span>Hartslag</span> <strong class="hr-blur">❤️ {hr:.0f}</strong></div>'
        html += f"""<div class="sport-card"><div class="sport-header" style="color:{color}"><div class="icon-circle" style="background:{color}15">{icon}</div><h3>{cat}</h3></div><div class="sport-body">{rows}</div></div>"""
    return html + '</div>'

def generate_hall_of_fame(df):
    html = '<div class="hof-grid">'
    df_hof = df.dropna(subset=['Datum']).copy()
    for cat in ['Fiets', 'Zwift', 'Hardlopen']:
        df_s = df_hof[df_hof['Categorie'] == cat].copy()
        if df_s.empty: continue
        icon, color = get_sport_style(cat)
        def top3(col, unit, is_pace=False):
            d_sorted = df_s.sort_values(col, ascending=False).head(3); res = ""
            for i, (_, r) in enumerate(d_sorted.iterrows()):
                v = r[col]; val = f"{v:.1f} {unit}"
                if is_pace: val = f"{int((3600/v)//60)}:{int((3600/v)%60):02d}/km"
                elif unit == 'W': val = f"{v:.0f} W"
                res += f'<div class="top3-item"><span>{"🥇🥈🥉"[i]} {val}</span><span class="date">{r["Datum"].strftime("%d-%m-%y")}</span></div>'
            return res
        sections = f'<div class="hof-sec"><div class="sec-lbl">Langste Afstand</div>{top3("Afstand_km", "km")}</div>'
        if cat == 'Zwift' and 'Wattage' in df_s.columns: sections += f'<div class="hof-sec"><div class="sec-lbl">Hoogste Wattage (Gem)</div>{top3("Wattage", "W")}</div>'
        else: sections += f'<div class="hof-sec"><div class="sec-lbl">Snelste Gem.</div>{top3("Gem_Snelheid", "km/u", cat=="Hardlopen")}</div>'
        html += f"""<div class="hof-card"><div class="hof-header" style="color:{color}">{icon} {cat}</div>{sections}</div>"""
    return html + '</div>'

def generate_gear_section(df):
    dfg = df.dropna(subset=['Gear']).copy(); dfg = dfg[dfg['Gear'].str.strip() != '']
    if dfg.empty: return "<p>Geen data</p>"
    stats = dfg.groupby('Gear').agg(Count=('Categorie','count'), Km=('Afstand_km','sum'), Type=('Categorie', lambda x: x.mode()[0])).reset_index().sort_values('Km', ascending=False)
    html = '<div class="kpi-grid">'
    for _, r in stats.iterrows():
        icon = '🚲' if r['Type'] in ['Fiets', 'Zwift'] else '👟'
        html += f"""<div class="kpi-card" style="padding:15px;"><div style="display:flex;align-items:center;gap:10px;margin-bottom:8px"><span style="font-size:20px;">{icon}</span><strong style="font-size:13px;">{r['Gear']}</strong></div><div style="font-size:18px;font-weight:700;color:{COLORS['primary']}">{r['Km']:,.0f} km</div><div style="font-size:11px;color:{COLORS['text_light']}">{r['Count']} act.</div></div>"""
    return html + "</div>"

def generate_logbook(df, yr):
    rows = ""
    for _, r in df.sort_values('Datum', ascending=False).iterrows():
        km = f"{r['Afstand_km']:.1f}" if r['Categorie'] not in ['Padel', 'Krachttraining'] and r['Afstand_km'] > 0 else "-"
        rows += f"<tr><td>{r['Datum'].strftime('%d-%m')}</td><td>{get_sport_style(r['Categorie'])[0]}</td><td>{r['Naam']}</td><td align='right'>{km}</td></tr>"
    return f'<div class="chart-box full-width" style="margin-top:20px;max-height:400px;overflow-y:auto"><table class="log-table"><thead><tr><th>Datum</th><th>Type</th><th>Naam</th><th align="right">Km</th></tr></thead><tbody>{rows}</tbody></table></div>'

def generate_kpi(lbl, val, icon, diff_html):
    return f"""<div class="kpi-card"><div style="display:flex;justify-content:space-between;"><div style="font-size:11px;color:#64748b;font-weight:700;text-transform:uppercase">{lbl}</div><div style="font-size:16px;">{icon}</div></div><div style="font-size:24px;font-weight:700;color:#0f172a;margin:5px 0">{val}</div><div style="font-size:12px;">{diff_html}</div></div>"""

# --- MAIN ---
def genereer_dashboard():
    print("🚀 Start V53.0 (Interactive Filtering)...")
    try:
        df = pd.read_csv('activities.csv')
        nm = {'Datum van activiteit':'Datum', 'Naam activiteit':'Naam', 'Activiteitstype':'Activiteitstype', 
              'Beweegtijd':'Beweegtijd_sec', 'Afstand':'Afstand_km', 'Gemiddelde hartslag':'Hartslag', 
              'Gemiddelde snelheid':'Gem_Snelheid', 'Uitrusting voor activiteit':'Gear', 'Gemiddeld wattage':'Wattage'}
        df = df.rename(columns={k:v for k,v in nm.items() if k in df.columns})
        
        for c in ['Afstand_km', 'Beweegtijd_sec', 'Gem_Snelheid']:
            if c in df.columns: df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        df['Hartslag'] = pd.to_numeric(df['Hartslag'], errors='coerce')
        if 'Wattage' in df.columns: df['Wattage'] = pd.to_numeric(df['Wattage'], errors='coerce')
        
        df['Datum'] = df['Datum'].apply(solve_dates)
        df = df.dropna(subset=['Datum'])
        df['Categorie'] = df.apply(determine_category, axis=1)
        df['Jaar'] = df['Datum'].dt.year; df['Day'] = df['Datum'].dt.dayofyear
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
            
            scatter_html = create_scatter_plot(df_yr)
            zone_html = create_zone_pie(df_yr)
            hm_html = create_heatmap(df_yr)
            str_html = create_strength_freq_chart(df_yr)
            
            nav += f'<button class="nav-btn {"active" if yr == datetime.now().year else ""}" onclick="openTab(event, \'v-{yr}\')">{yr}</button>'
            sects += f"""<div id="v-{yr}" class="tab-content" style="display:{"block" if yr == datetime.now().year else "none"}">
                <h2 class="sec-title">Overzicht {yr}</h2>
                <div class="kpi-grid">
                    {generate_kpi("Sessies", len(df_yr), "🔥", format_diff_html(len(df_yr), len(df_prev_comp)))}
                    {generate_kpi("Totaal Afstand", f"{df_yr['Afstand_km'].sum():,.0f} km", "📏", format_diff_html(df_yr['Afstand_km'].sum(), df_prev_comp['Afstand_km'].sum(), "km"))}
                    {generate_kpi("Totaal Tijd", format_time(df_yr['Beweegtijd_sec'].sum()), "⏱️", format_diff_html(df_yr['Beweegtijd_sec'].sum()/3600, df_prev_comp['Beweegtijd_sec'].sum()/3600, "u"))}
                </div>
                {generate_ytd_history(df, yr)}
                <h3 class="sec-sub">Per Sport</h3>{generate_sport_cards(df_yr, df_prev_comp)}
                <h3 class="sec-sub">Maandelijkse Voortgang</h3>{create_monthly_charts(df_yr, df_prev, yr)}
                <h3 class="sec-sub">Diepte-analyse</h3>
                <div class="chart-grid">{scatter_html}{zone_html}</div>
                <div class="chart-grid">{hm_html}{str_html}</div>
                <h3 class="sec-sub">Records {yr}</h3>{generate_hall_of_fame(df_yr)}
                <h3 class="sec-sub">Logboek {yr}</h3>{generate_logbook(df_yr, yr)}
            </div>"""
            
        nav += '<button class="nav-btn" onclick="openTab(event, \'v-Tot\')">Carrière</button>'
        sects += f'<div id="v-Tot" class="tab-content" style="display:none"><h2 class="sec-title">All-Time Records</h2>{generate_hall_of_fame(df)}<h2 class="sec-title" style="margin-top:30px">De Garage</h2>{generate_gear_section(df)}</div>'
        
        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Sportoverzicht Jorden</title><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet"><style>
        :root{{--primary:#0f172a;--bg:#f8fafc;--card:#ffffff;--text:#1e293b;--label:#94a3b8}}
        body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);margin:0;padding:20px;padding-bottom:60px}}
        .container{{max-width:1200px;margin:0 auto}}
        .header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}}
        .lock-btn{{background:white;border:1px solid #cbd5e1;padding:6px 12px;border-radius:20px;cursor:pointer}}
        .hr-blur{{filter:blur(5px);transition:0.3s}}
        .nav{{display:flex;gap:8px;overflow-x:auto;margin-bottom:20px;padding-bottom:5px;scrollbar-width:none}}
        .nav-btn{{flex:0 0 auto;background:white;border:1px solid #e2e8f0;padding:8px 16px;border-radius:20px;font-size:13px;font-weight:600;color:#64748b;cursor:pointer}}
        .nav-btn.active{{background:var(--primary);color:white;border-color:var(--primary)}}
        .stats-box-container{{display:flex;gap:15px;margin-bottom:25px;flex-wrap:wrap}}
        .goals-section, .streaks-section{{flex:1;background:white;padding:15px;border-radius:16px;border:1px solid #e2e8f0;min-width:300px}}
        .box-title{{font-size:11px;color:var(--label);text-transform:uppercase;margin-bottom:12px;letter-spacing:1px;font-weight:700}}
        .goal-item{{margin-bottom:10px}}.goal-label{{display:flex;justify-content:space-between;font-size:12px;font-weight:600;margin-bottom:4px}}
        .goal-bar{{background:#f1f5f9;height:6px;border-radius:3px;overflow:hidden}}.goal-bar div{{height:100%;border-radius:3px}}
        .streak-row{{display:flex;justify-content:space-between;margin-bottom:4px;font-size:13px}}.streak-row .val{{font-weight:700;color:var(--primary)}}
        .streak-sub{{font-size:10px;color:var(--label);text-align:right;font-style:italic}}
        .kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:15px;margin-bottom:25px}}
        .kpi-card{{background:white;padding:15px;border-radius:16px;border:1px solid #e2e8f0}}
        .sport-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:15px;margin-bottom:25px}}
        .sport-card{{background:white;padding:15px;border-radius:16px;border:1px solid #e2e8f0}}
        .sport-header{{display:flex;align-items:center;gap:10px;margin-bottom:12px;font-size:16px}}
        .icon-circle{{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center}}
        .stat-row{{display:flex;justify-content:space-between;margin-bottom:6px;font-size:13px;color:#64748b}}
        .stat-row strong{{color:var(--text)}} .val-group{{display:flex;gap:6px;align-items:center}}
        .hof-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:15px;margin-bottom:20px}}
        .hof-card{{background:white;padding:15px;border-radius:16px;border:1px solid #e2e8f0}}
        .hof-sec{{margin-bottom:12px}} .sec-lbl{{font-size:9px;color:var(--label);text-transform:uppercase;font-weight:700;margin-bottom:4px}}
        .top3-item{{display:flex;justify-content:space-between;font-size:12px;margin-bottom:2px}}
        .sec-title{{font-size:20px;font-weight:700;margin-bottom:15px}}
        .sec-sub{{font-size:12px;color:var(--label);text-transform:uppercase;font-weight:700;margin:30px 0 10px 0;letter-spacing:1px;border-bottom:1px solid #e2e8f0;padding-bottom:5px}}
        .chart-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(350px,1fr));gap:15px;margin-bottom:15px}}
        .chart-box{{background:white;padding:15px;border-radius:16px;border:1px solid #e2e8f0}}
        .full-width{{width:100%;box-sizing:border-box}}
        .log-table{{width:100%;border-collapse:collapse;font-size:12px}} .log-table th{{text-align:left;color:var(--label);padding:8px}} .log-table td{{padding:8px;border-top:1px solid #f1f5f9}}
        .history-table{{width:100%; border-collapse:collapse; font-size:13px;}} .history-table th{{text-align:left; color:var(--label); padding:8px; border-bottom:1px solid #e2e8f0;}} .history-table td{{padding:8px; border-bottom:1px solid #f1f5f9;}}
        </style></head><body><div class="container">
        <div class="header"><h1 style="font-size:24px;margin:0">Sportoverzicht Jorden</h1><button class="lock-btn" onclick="unlock()">❤️ 🔒</button></div>
        {stats_box}<div class="nav">{nav}</div>{sects}</div>
        <script>
        function openTab(e,n){{document.querySelectorAll('.tab-content').forEach(x=>x.style.display='none');document.querySelectorAll('.nav-btn').forEach(x=>x.classList.remove('active'));document.getElementById(n).style.display='block';e.currentTarget.classList.add('active');}}
        function unlock(){{if(prompt("Wachtwoord:")==='Nala'){{document.querySelectorAll('.hr-blur').forEach(e=>e.classList.remove('hr-blur'));document.querySelector('.lock-btn').style.display='none';}}}}
        </script></body></html>"""
        
        with open('dashboard.html', 'w', encoding='utf-8') as f: f.write(html)
        print("✅ Dashboard (V53.0) gegenereerd!")

    except Exception as e:
        print(f"❌ Fout: {e}")

if __name__ == "__main__":
    genereer_dashboard()
