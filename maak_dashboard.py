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
    'primary': '#0f172a', 'gold': '#d4af37', 'bg': '#f1f5f9',
    'card': '#ffffff', 'text': '#1e293b', 'text_light': '#64748b',
    'zwift': '#ff6600', 'bike_out': '#0099ff', 'run': '#fbbf24', 
    'swim': '#3b82f6', 'padel': '#84cc16', 'walk': '#10b981', 
    'strength': '#8b5cf6', # Nieuwe kleur voor Kracht (Paars)
    'default': '#64748b', 'ref_gray': '#cbd5e1'
}

# --- DATUM FIX ---
def solve_dates(date_str):
    if pd.isna(date_str) or str(date_str).strip() == "": return pd.NaT
    d_map = {'jan':1,'feb':2,'mrt':3,'apr':4,'mei':5,'jun':6,'jul':7,'aug':8,'sep':9,'okt':10,'nov':11,'dec':12}
    try:
        clean = re.sub(r'[^a-zA-Z0-9\s:]', '', str(date_str).lower())
        parts = clean.split()
        day, month_str, year = int(parts[0]), parts[1][:3], int(parts[2])
        return pd.Timestamp(year=year, month=d_map.get(month_str, 1), day=day)
    except: return pd.to_datetime(date_str, errors='coerce')

# --- CATEGORIE (AANGEPAST) ---
def determine_category(row):
    t = str(row['Activiteitstype']).lower().strip()
    n = str(row['Naam']).lower().strip()
    
    # 1. Krachttraining (PRIORITEIT)
    # Checkt op 'kracht', 'fitness', 'gym', 'weight'
    if any(x in t for x in ['kracht', 'power', 'gym', 'fitness', 'weight']) or \
       any(x in n for x in ['kracht', 'power', 'gym', 'fitness']): 
        return 'Krachttraining'

    # 2. Zwift
    if 'virtu' in t or 'zwift' in n: return 'Zwift'
    
    # 3. Fietsen
    if any(x in t for x in ['fiets', 'ride', 'gravel', 'mtb', 'cycle', 'wieler', 'velomobiel', 'e-bike']): return 'Fiets'
    
    # 4. Hardlopen
    if any(x in t for x in ['hardloop', 'run', 'jog', 'lopen', 'loop']): return 'Hardlopen'
    
    # 5. Zwemmen
    if 'zwem' in t: return 'Zwemmen'
    
    # 6. Wandelen
    if any(x in t for x in ['wandel', 'hike', 'walk']): return 'Wandelen'
    
    # 7. Padel / Overig (Vangnet voor 'training' en 'workout' die geen kracht zijn)
    if any(x in t for x in ['padel', 'tennis', 'squash']): return 'Padel'
    
    # Als het 'training' of 'workout' is, maar niet hierboven afgevangen, is het waarschijnlijk Padel/Algemeen
    # (Of je kunt hier een categorie 'Algemeen' van maken als je wilt)
    if any(x in t for x in ['train', 'work', 'fit']): return 'Padel' 

    return 'Overig'

def get_sport_style(cat):
    styles = {
        'Fiets':('🚴', COLORS['bike_out']), 
        'Zwift':('👾', COLORS['zwift']), 
        'Hardlopen':('🏃', COLORS['run']),
        'Wandelen':('🚶', COLORS['walk']), 
        'Padel':('🎾', COLORS['padel']), 
        'Zwemmen':('🏊', COLORS['swim']),
        'Krachttraining': ('🏋️', COLORS['strength']) # Nieuw icoon
    }
    return styles.get(cat, ('🏅', COLORS['default']))

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

# --- 5-JAREN VERGELIJKING (YTD) ---
def generate_ytd_history(df, current_year):
    is_current_active_year = (current_year == datetime.now().year)
    day_limit = datetime.now().timetuple().tm_yday if is_current_active_year else 366
    
    html = f"""
    <div class="chart-box full-width" style="margin-bottom:20px;">
        <h3 style="margin-top:0; margin-bottom:15px; font-size:16px;">📅 Verloop t.o.v. Vorige Jaren (Dezelfde Periode)</h3>
        <table class="history-table">
            <thead>
                <tr><th>Jaar</th><th>Afstand</th><th>Tijd</th><th>Sessies</th></tr>
            </thead>
            <tbody>
    """
    max_km = 0
    history_data = []
    
    for y in range(current_year, current_year - 6, -1):
        df_y = df[df['Jaar'] == y]
        df_y_ytd = df_y[df_y['Day'] <= day_limit]
        
        km = df_y_ytd['Afstand_km'].sum()
        sec = df_y_ytd['Beweegtijd_sec'].sum()
        count = len(df_y_ytd)
        if km > max_km: max_km = km
        history_data.append((y, km, sec, count))
    
    for y, km, sec, count in history_data:
        bar_w = (km / max_km * 100) if max_km > 0 else 0
        is_curr = (y == current_year)
        row_style = "font-weight:bold; background:#f8fafc;" if is_curr else ""
        bar_color = COLORS['primary'] if is_curr else '#cbd5e1'
        hours = sec / 3600
        
        html += f"""
        <tr style="{row_style}">
            <td style="width:60px;">{y}</td>
            <td>
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="width:70px; text-align:right;">{km:,.0f} km</span>
                    <div style="flex:1; background:#f1f5f9; height:8px; border-radius:4px; max-width:150px;">
                        <div style="width:{bar_w}%; background:{bar_color}; height:100%; border-radius:4px;"></div>
                    </div>
                </div>
            </td>
            <td style="width:80px; text-align:right;">{hours:.1f} uur</td>
            <td style="width:60px; text-align:right;">{count}</td>
        </tr>
        """
    return html + "</tbody></table></div>"

# --- STREAK ---
def calculate_streaks(df):
    valid = df.dropna(subset=['Datum']).sort_values('Datum')
    if valid.empty: return {}
    valid['WeekStart'] = valid['Datum'].dt.to_period('W-MON').dt.start_time
    weeks = sorted(valid['WeekStart'].unique())
    days = sorted(valid['Datum'].dt.date.unique())
    
    cur_wk, max_wk, max_wk_dates = 0, 0, "-"
    if weeks:
        if (pd.Timestamp.now().to_period('W-MON').start_time - weeks[-1]).days <= 7:
            cur_wk = 1
            for i in range(len(weeks)-2, -1, -1):
                if (weeks[i+1]-weeks[i]).days == 7: cur_wk+=1
                else: break
        
        temp, start = 1, weeks[0]
        max_wk, max_wk_dates = 1, f"({weeks[0].strftime('%d %b %y')})"
        for i in range(1, len(weeks)):
            if (weeks[i]-weeks[i-1]).days == 7: temp+=1
            else:
                if temp > max_wk:
                    max_wk = temp
                    max_wk_dates = f"({start.strftime('%d %b %y')} - {(weeks[i-1]+timedelta(days=6)).strftime('%d %b %y')})"
                temp = 1; start = weeks[i]
        if temp > max_wk:
            max_wk = temp
            max_wk_dates = f"({start.strftime('%d %b %y')} - {(weeks[-1]+timedelta(days=6)).strftime('%d %b %y')})"

    cur_d, max_d, max_d_dates = 0, 0, "-"
    if days:
        if (datetime.now().date() - days[-1]).days <= 1:
            cur_d = 1
            for i in range(len(days)-2, -1, -1):
                if (days[i+1]-days[i]).days == 1: cur_d+=1
                else: break
        
        temp, start = 1, days[0]
        max_d, max_d_dates = 1, f"({days[0].strftime('%d %b')})"
        for i in range(1, len(days)):
            if (days[i]-days[i-1]).days == 1: temp+=1
            else:
                if temp > max_d:
                    max_d = temp
                    max_d_dates = f"({start.strftime('%d %b')} - {days[i-1].strftime('%d %b %y')})"
                temp = 1; start = days[i]
        if temp > max_d:
            max_d = temp
            max_d_dates = f"({start.strftime('%d %b')} - {days[-1].strftime('%d %b %y')})"

    return {'cur_week':cur_wk, 'max_week':max_wk, 'max_week_dates':max_wk_dates, 'cur_day':cur_d, 'max_day':max_d, 'max_day_dates':max_d_dates}

# --- UI ---
def generate_stats_box(df, current_year):
    df_cur = df[df['Jaar'] == current_year]
    b_km = df_cur[df_cur['Categorie'] == 'Fiets']['Afstand_km'].sum()
    z_km = df_cur[df_cur['Categorie'] == 'Zwift']['Afstand_km'].sum()
    r_km = df_cur[df_cur['Categorie'] == 'Hardlopen']['Afstand_km'].sum()
    
    b_pct = min(100, (b_km / GOALS['bike_out']) * 100)
    z_pct = min(100, (z_km / GOALS['zwift']) * 100)
    r_pct = min(100, (r_km / GOALS['run']) * 100)
    
    s = calculate_streaks(df)
    
    return f"""<div class="stats-box-container">
        <div class="goals-section">
            <h3 class="box-title">🎯 DOELEN {current_year}</h3>
            <div class="goal-item"><div class="goal-label"><span>🚴 Buiten: {b_km:.0f}/{GOALS['bike_out']}km</span><span>{b_pct:.1f}%</span></div><div class="goal-bar"><div style="width:{b_pct}%; background:{COLORS['bike_out']};"></div></div></div>
            <div class="goal-item"><div class="goal-label"><span>👾 Zwift: {z_km:.0f}/{GOALS['zwift']}km</span><span>{z_pct:.1f}%</span></div><div class="goal-bar"><div style="width:{z_pct}%; background:{COLORS['zwift']};"></div></div></div>
            <div class="goal-item"><div class="goal-label"><span>🏃 Lopen: {r_km:.0f}/{GOALS['run']}km</span><span>{r_pct:.1f}%</span></div><div class="goal-bar"><div style="width:{r_pct}%; background:{COLORS['run']};"></div></div></div>
        </div>
        <div class="streaks-section">
            <h3 class="box-title">🔥 REEKSEN</h3>
            <div class="streak-row"><span class="label">Huidig Wekelijks:</span><span class="val">{s['cur_week']} weken</span></div>
            <div class="streak-row"><span class="label">Record Wekelijks:</span><span class="val">{s['max_week']} weken</span></div>
            <div class="streak-sub">{s['max_week_dates']}</div>
            <div style="height:10px"></div>
            <div class="streak-row"><span class="label">Huidig Dagelijks:</span><span class="val">{s['cur_day']} dagen</span></div>
            <div class="streak-row"><span class="label">Record Dagelijks:</span><span class="val">{s['max_day']} dagen</span></div>
            <div class="streak-sub">{s['max_day_dates']}</div>
        </div>
    </div>"""

def generate_sport_cards(df_yr, df_prev_comp):
    html = '<div class="sport-grid">'
    # Specifieke volgorde voor cards: eerst de grote 3, dan kracht, dan rest
    cats_present = df_yr['Categorie'].unique()
    custom_order = ['Fiets', 'Zwift', 'Hardlopen', 'Krachttraining', 'Padel', 'Wandelen', 'Zwemmen', 'Overig']
    # Filter only present categories, keep order
    sorted_cats = [c for c in custom_order if c in cats_present]
    # Add any remaining categories not in list
    for c in cats_present:
        if c not in sorted_cats: sorted_cats.append(c)

    for cat in sorted_cats:
        df_s = df_yr[df_yr['Categorie'] == cat]
        df_p = df_prev_comp[df_prev_comp['Categorie'] == cat] if df_prev_comp is not None else pd.DataFrame()
        if df_s.empty: continue
        
        icon, color = get_sport_style(cat)
        
        n_sessies = len(df_s); n_prev = len(df_p)
        dist = df_s['Afstand_km'].sum(); dist_p = df_p['Afstand_km'].sum() if not df_p.empty else 0
        tijd = df_s['Beweegtijd_sec'].sum(); tijd_p = df_p['Beweegtijd_sec'].sum() if not df_p.empty else 0
        hr = df_s['Hartslag'].mean()
        watt = df_s['Wattage'].mean() if 'Wattage' in df_s.columns else None
        
        spd_val = "-"
        if cat == 'Hardlopen' and dist > 0: spd_val = f"{int((tijd/dist)//60)}:{int((tijd/dist)%60):02d} /km"
        elif tijd > 0 and cat not in ['Padel', 'Krachttraining']: spd_val = f"{(dist/(tijd/3600)):.1f} km/u"

        rows = f"""<div class="stat-row"><span>Sessies</span> <div class="val-group"><strong>{n_sessies}</strong> {format_diff_html(n_sessies, n_prev)}</div></div>
                   <div class="stat-row"><span>Tijd</span> <div class="val-group"><strong>{format_time(tijd)}</strong> {format_diff_html(tijd/3600, tijd_p/3600, "u")}</div></div>"""
        
        if cat not in ['Padel', 'Krachttraining']:
            rows += f"""<div class="stat-row"><span>Afstand</span> <div class="val-group"><strong>{dist:,.0f} km</strong> {format_diff_html(dist, dist_p)}</div></div>
                        <div class="stat-row"><span>Snelheid</span> <strong>{spd_val}</strong></div>"""
        
        if cat == 'Zwift' and pd.notna(watt) and watt > 0:
            rows += f'<div class="stat-row"><span>Wattage</span> <strong>⚡ {watt:.0f} W</strong></div>'
            
        if pd.notna(hr):
            rows += f'<div class="stat-row"><span>Hartslag</span> <strong class="hr-blur">❤️ {hr:.0f}</strong></div>'

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
            d_sorted = df_s.sort_values(col, ascending=False).head(3)
            res = ""
            for i, (_, r) in enumerate(d_sorted.iterrows()):
                v = r[col]
                val = f"{v:.1f} {unit}"
                if is_pace: val = f"{int((3600/v)//60)}:{int((3600/v)%60):02d}/km"
                elif unit == 'W': val = f"{v:.0f} W"
                res += f'<div class="top3-item"><span>{"🥇🥈🥉"[i]} {val}</span><span class="date">{r["Datum"].strftime("%d-%m-%y")}</span></div>'
            return res
        
        sections = f'<div class="hof-sec"><div class="sec-lbl">Langste Afstand</div>{top3("Afstand_km", "km")}</div>'
        if cat == 'Zwift' and 'Wattage' in df_s.columns:
            sections += f'<div class="hof-sec"><div class="sec-lbl">Hoogste Wattage (Gem)</div>{top3("Wattage", "W")}</div>'
        else:
            sections += f'<div class="hof-sec"><div class="sec-lbl">Snelste Gem.</div>{top3("Gem_Snelheid", "km/u", cat=="Hardlopen")}</div>'

        html += f"""<div class="hof-card"><div class="hof-header" style="color:{color}">{icon} {cat}</div>{sections}</div>"""
    return html + '</div>'

# --- NIEUWE CHART FUNCTIE (STACKED & GROUPED) ---
def create_monthly_charts(df_cur, df_prev, year):
    months = ['Jan','Feb','Mrt','Apr','Mei','Jun','Jul','Aug','Sep','Okt','Nov','Dec']
    
    # Hulpfunctie
    def get_month_data(df, categories):
        mask = df['Categorie'].isin(categories)
        return df[mask].groupby(df['Datum'].dt.month)['Afstand_km'].sum().reindex(range(1,13), fill_value=0)
    
    # Krachttraining is gebaseerd op TIJD (want afstand = 0)
    def get_month_time(df, categories):
        mask = df['Categorie'].isin(categories)
        return df[mask].groupby(df['Datum'].dt.month)['Beweegtijd_sec'].sum().reindex(range(1,13), fill_value=0) / 3600 # Naar Uur

    # 1. FIETSEN GRAFIEK (Buiten + Zwift)
    prev_total = get_month_data(df_prev, ['Fiets', 'Zwift'])
    cur_zwift = get_month_data(df_cur, ['Zwift'])
    cur_out = get_month_data(df_cur, ['Fiets'])

    fig_bike = go.Figure()
    fig_bike.add_trace(go.Bar(x=months, y=prev_total, name=f"{year-1} Totaal", marker_color=COLORS['ref_gray'], offsetgroup=1))
    fig_bike.add_trace(go.Bar(x=months, y=cur_zwift, name=f"{year} Zwift", marker_color=COLORS['zwift'], offsetgroup=2))
    fig_bike.add_trace(go.Bar(x=months, y=cur_out, name=f"{year} Buiten", marker_color=COLORS['bike_out'], base=cur_zwift, offsetgroup=2))
    fig_bike.update_layout(title='🚴 Fietsen Totaal (Buiten + Zwift)', template='plotly_white', barmode='group', margin=dict(t=40,b=20,l=20,r=20), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=True, legend=dict(orientation="h", y=1.1))

    # 2. HARDLOPEN GRAFIEK
    prev_run = get_month_data(df_prev, ['Hardlopen'])
    cur_run = get_month_data(df_cur, ['Hardlopen'])
    fig_run = go.Figure()
    fig_run.add_trace(go.Bar(x=months, y=prev_run, name=f"{year-1}", marker_color=COLORS['ref_gray']))
    fig_run.add_trace(go.Bar(x=months, y=cur_run, name=f"{year}", marker_color=COLORS['run']))
    fig_run.update_layout(title='🏃 Hardlopen (km)', template='plotly_white', barmode='group', margin=dict(t=40,b=20,l=20,r=20), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=True, legend=dict(orientation="h", y=1.1))

    # 3. KRACHT GRAFIEK (Op basis van UREN, want afstand is 0)
    # Alleen tonen als er data is
    prev_str = get_month_time(df_prev, ['Krachttraining'])
    cur_str = get_month_time(df_cur, ['Krachttraining'])
    
    fig_str_html = ""
    if prev_str.sum() > 0 or cur_str.sum() > 0:
        fig_str = go.Figure()
        fig_str.add_trace(go.Bar(x=months, y=prev_str, name=f"{year-1}", marker_color=COLORS['ref_gray']))
        fig_str.add_trace(go.Bar(x=months, y=cur_str, name=f"{year}", marker_color=COLORS['strength']))
        fig_str.update_layout(title='🏋️ Kracht (Uren)', template='plotly_white', barmode='group', margin=dict(t=40,b=20,l=20,r=20), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=True, legend=dict(orientation="h", y=1.1))
        fig_str_html = f'<div class="chart-box full-width">{fig_str.to_html(full_html=False, include_plotlyjs="cdn")}</div>'

    return f"""
    <div class="chart-grid">
        <div class="chart-box full-width">{fig_bike.to_html(full_html=False, include_plotlyjs="cdn")}</div>
        <div class="chart-box full-width">{fig_run.to_html(full_html=False, include_plotlyjs="cdn")}</div>
        {fig_str_html}
    </div>
    """

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

def generate_logbook(df, yr):
    rows = ""
    for _, r in df.sort_values('Datum', ascending=False).iterrows():
        # Geen KM tonen bij Padel of Kracht
        km = f"{r['Afstand_km']:.1f}" if r['Categorie'] not in ['Padel', 'Krachttraining'] and r['Afstand_km'] > 0 else "-"
        rows += f"<tr><td>{r['Datum'].strftime('%d-%m')}</td><td>{get_sport_style(r['Categorie'])[0]}</td><td>{r['Naam']}</td><td align='right'>{km}</td></tr>"
    return f'<div class="chart-box full-width" style="margin-top:20px;max-height:400px;overflow-y:auto"><table class="log-table"><thead><tr><th>Datum</th><th>Type</th><th>Naam</th><th align="right">Km</th></tr></thead><tbody>{rows}</tbody></table></div>'

def generate_kpi(lbl, val, icon, diff_html):
    return f"""<div class="kpi-card"><div style="display:flex;justify-content:space-between;"><div style="font-size:11px;color:#64748b;font-weight:700;text-transform:uppercase">{lbl}</div><div style="font-size:16px;">{icon}</div></div><div style="font-size:24px;font-weight:700;color:#0f172a;margin:5px 0">{val}</div><div style="font-size:12px;">{diff_html}</div></div>"""

# --- MAIN ---
def genereer_dashboard():
    print("🚀 Start V51.0 (Fix Krachttraining & Charts)...")
    try:
        df = pd.
