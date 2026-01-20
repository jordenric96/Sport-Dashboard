import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime, timedelta
import json
import os
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

# --- CONFIGURATIE ---
GOALS = {
    'bike_out': 3000, # Buiten
    'zwift': 3000,    # Binnen
    'run': 350        # Lopen
}

COLORS = {
    'primary': '#0f172a', 
    'gold': '#d4af37', 
    'gold_bg': '#f59e0b',
    'bg': '#f8fafc', 
    'card': '#ffffff', 
    'text': '#1e293b', 
    'text_light': '#64748b',
    
    # DISTINCTE KLEUREN
    'zwift': '#ff6600',    # Oranje
    'bike_out': '#0099ff', # Blauw
    'run': '#fbbf24',      # Goud
    'swim': '#3b82f6',     
    'padel': '#84cc16',    
    'walk': '#10b981',     
    'default': '#64748b',
    
    # 2025 (LICHT/PASTEL)
    'zwift_prev': '#fdba74', 
    'bike_out_prev': '#93c5fd', 
    'run_prev': '#cbd5e1'    
}

# Mapping voor iconen en kleuren
SPORT_CONFIG = {
    'Fiets': {'icon': '🚴', 'color': COLORS['bike_out']},
    'Virtueel': {'icon': '👾', 'color': COLORS['zwift']},
    'Hardlopen': {'icon': '🏃', 'color': COLORS['run']},
    'Wandelen': {'icon': '🚶', 'color': COLORS['walk']},
    'Padel': {'icon': '🎾', 'color': COLORS['padel']},
    'Zwemmen': {'icon': '🏊', 'color': COLORS['swim']},
    'Overig': {'icon': '🏅', 'color': COLORS['default']}
}

def get_sport_style(cat):
    return SPORT_CONFIG.get(cat, SPORT_CONFIG['Overig'])

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

def robust_date_parser(date_series):
    dates = pd.to_datetime(date_series, dayfirst=True, errors='coerce')
    # Fallback voor Nederlandse maanden als standaard parse faalt
    if dates.isna().sum() > len(dates) * 0.5:
        dutch = {'jan': 'Jan', 'feb': 'Feb', 'mrt': 'Mar', 'apr': 'Apr', 'mei': 'May', 'jun': 'Jun', 'jul': 'Jul', 'aug': 'Aug', 'sep': 'Sep', 'okt': 'Oct', 'nov': 'Nov', 'dec': 'Dec'}
        ds = date_series.astype(str).str.lower()
        for nl, en in dutch.items(): 
            ds = ds.str.replace(nl, en, regex=False)
        dates = pd.to_datetime(ds, format='%d %b %Y, %H:%M:%S', errors='coerce')
    return dates

# --- CORE CATEGORIZATION LOGIC ---
def determine_category(row):
    """Bepaalt de hoofdcategorie op basis van Activiteitstype en Naam"""
    atype = str(row['Activiteitstype']).lower()
    anaam = str(row['Naam activiteit']).lower()
    
    # 1. ZWIFT / VIRTUEEL (Heeft voorrang)
    # Als 'virtu' in type staat OF 'zwift' in de naam -> Virtueel
    if 'virtu' in atype or 'zwift' in anaam:
        return 'Virtueel'
    
    # 2. FIETSEN (Buiten)
    # Zoek naar typische fietswoorden
    if any(x in atype for x in ['fiets', 'ride', 'gravel', 'mtb', 'mountainbike', 'cycle', 'e-bike']):
        return 'Fiets'
        
    # 3. HARDLOPEN
    if any(x in atype for x in ['hardloop', 'run', 'jog']):
        return 'Hardlopen'
        
    # 4. PADEL / TRAINING (Zoals gevraagd: training = padel)
    if any(x in atype for x in ['training', 'workout', 'fitness', 'kracht', 'padel', 'tennis']):
        return 'Padel'
        
    # 5. ZWEMMEN
    if 'zwem' in atype:
        return 'Zwemmen'
        
    # 6. WANDELEN
    if any(x in atype for x in ['wandel', 'hike', 'walk']):
        return 'Wandelen'
        
    return 'Overig'

def apply_data_logic(df):
    df['Datum'] = robust_date_parser(df['Datum'])
    
    # CATEGORIE BEPALEN (De "Sorteerhoed")
    df['Categorie'] = df.apply(determine_category, axis=1)
    
    # Eenheden correcties
    # Zwemmen is vaak in meters, Strava export is meestal km of meters afh van settings. 
    # We nemen aan dat input 'Afstand' in km is, behalve als het heel groot is? 
    # Nee, user zei eerder "delen door 1000 voor zwemmen".
    # We passen dit toe op de rows die 'Zwemmen' zijn geworden.
    df.loc[df['Categorie'] == 'Zwemmen', 'Afstand_km'] /= 1000
    
    # Proracer fix (Oude fietsritten)
    merida_rides = df[df['Uitrusting voor activiteit'].str.contains('Merida', case=False, na=False)]
    if not merida_rides.empty:
        first_merida_date = merida_rides['Datum'].min()
        mask = (
            (df['Datum'] < first_merida_date) & 
            (df['Categorie'] == 'Fiets') &
            (df['Uitrusting voor activiteit'].isna() | (df['Uitrusting voor activiteit'] == '') | (df['Uitrusting voor activiteit'] == 'nan'))
        )
        if mask.sum() > 0: df.loc[mask, 'Uitrusting voor activiteit'] = 'Proracer'
            
    # Snelheid Fix (m/s -> km/u)
    if 'Gemiddelde_Snelheid_km_u' in df.columns:
        if df['Gemiddelde_Snelheid_km_u'].mean() < 10: df['Gemiddelde_Snelheid_km_u'] *= 3.6
    
    # Fallback snelheid
    df['Calc_Speed'] = (df['Afstand_km'] / (df['Beweegtijd_sec'] / 3600)).replace([np.inf, -np.inf], 0)
    
    if 'Gemiddelde_Snelheid_km_u' not in df.columns:
        df['Gemiddelde_Snelheid_km_u'] = df['Calc_Speed']
    else:
        df['Gemiddelde_Snelheid_km_u'] = df['Gemiddelde_Snelheid_km_u'].fillna(df['Calc_Speed'])
        # Vul nullen ook in
        df.loc[df['Gemiddelde_Snelheid_km_u'] == 0, 'Gemiddelde_Snelheid_km_u'] = df.loc[df['Gemiddelde_Snelheid_km_u'] == 0, 'Calc_Speed']

    return df

# --- STREAKS ---
def calculate_streaks(df):
    if df.empty: return {}
    valid = df.dropna(subset=['Datum']).sort_values('Datum')
    if valid.empty: return {}
    
    # Dagelijks
    dates = sorted(valid['Datum'].dt.date.unique())
    cur_day = 0; max_day = 0
    
    # Huidig
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    date_set = set(dates)
    
    if today in date_set:
        cur_day = 1
        check = yesterday
        while check in date_set: cur_day += 1; check -= timedelta(days=1)
    elif yesterday in date_set:
        cur_day = 1
        check = yesterday - timedelta(days=1)
        while check in date_set: cur_day += 1; check -= timedelta(days=1)
        
    # Max
    temp = 1; max_day = 1
    max_end = dates[0]
    for i in range(1, len(dates)):
        if (dates[i] - dates[i-1]).days == 1: temp += 1
        else:
            if temp > max_day: max_day = temp; max_end = dates[i-1]
            temp = 1
    if temp > max_day: max_day = temp; max_end = dates[-1]
    max_start = max_end - timedelta(days=max_day-1)
    
    # Wekelijks (ISO Weken)
    # We groeperen op jaar-week. 
    valid['ISO_Week'] = valid['Datum'].dt.isocalendar().year * 100 + valid['Datum'].dt.isocalendar().week
    weeks = sorted(valid['ISO_Week'].unique())
    
    cur_week = 0; max_week = 0
    if len(weeks) > 0:
        curr_iso = datetime.now().isocalendar().year * 100 + datetime.now().isocalendar().week
        prev_iso = (datetime.now() - timedelta(weeks=1)).isocalendar().year * 100 + (datetime.now() - timedelta(weeks=1)).isocalendar().week
        
        # Check current streak
        last_w = weeks[-1]
        # Simpele check: als laatste week == deze week of vorige week
        # Let op: jaarwissel (202552 -> 202601) is lastig met simpele wiskunde.
        # We gebruiken datum-diff van de 'WeekStart' logica die we eerder hadden, die was beter.
        
    # Herkans met datum-based week logic
    valid['WeekStart'] = valid['Datum'].dt.to_period('W').dt.start_time
    wk_dates = sorted(valid['WeekStart'].unique())
    
    cur_wk_streak = 0
    max_wk_streak = 0
    
    if len(wk_dates) > 0:
        last = wk_dates[-1]
        now_wk = pd.Timestamp.now().to_period('W').start_time
        
        if (now_wk - last).days <= 7:
            cur_wk_streak = 1
            for i in range(len(wk_dates)-2, -1, -1):
                if (wk_dates[i+1] - wk_dates[i]).days == 7: cur_wk_streak += 1
                else: break
                
        temp = 1; max_wk_streak = 1
        max_wk_end = wk_dates[0]
        for i in range(1, len(wk_dates)):
            if (wk_dates[i] - wk_dates[i-1]).days == 7: temp += 1
            else:
                if temp > max_wk_streak: max_wk_streak = temp; max_wk_end = wk_dates[i-1]
                temp = 1
        if temp > max_wk_streak: max_wk_streak = temp; max_wk_end = wk_dates[-1]
        max_wk_start = max_wk_end - timedelta(weeks=max_wk_streak-1)
    else:
        max_wk_start = datetime.now(); max_wk_end = datetime.now()

    return {
        'cur_day': cur_day,
        'max_day': max_day,
        'max_day_range': f"{max_start.strftime('%d %b %y')} - {max_end.strftime('%d %b %y')}",
        'cur_week': cur_wk_streak,
        'max_week': max_wk_streak,
        'max_week_range': f"{max_wk_start.strftime('%d %b %y')} - {max_wk_end.strftime('%d %b %y')}"
    }

# --- HTML GENERATOREN ---
def generate_kpi(title, val, icon="", diff=""):
    return f"""<div class="kpi-card"><div class="kpi-icon-box">{icon}</div><div class="kpi-content"><div class="kpi-title">{title}</div><div class="kpi-value">{val}</div><div class="kpi-sub">{diff}</div></div></div>"""

def generate_gold_banner():
    return """
    <div class="gold-banner" onclick="toggleHOF()">
        <div style="display:flex; align-items:center; gap:10px;">
            <div class="gold-icon">🏆</div>
            <div style="font-weight:700; font-size:16px;">Eregalerij & Records</div>
        </div>
        <div style="margin-left:auto; font-size:12px; opacity:0.9;">▼ Klik voor details</div>
    </div>
    """

def generate_stats_box(df, current_year):
    df_cur = df[df['Jaar'] == current_year]
    
    # Gebruik nu de 'Categorie' kolom voor de tellers
    bike_out_km = df_cur[df_cur['Categorie'] == 'Fiets']['Afstand_km'].sum()
    zwift_km = df_cur[df_cur['Categorie'] == 'Virtueel']['Afstand_km'].sum()
    run_km = df_cur[df_cur['Categorie'] == 'Hardlopen']['Afstand_km'].sum()
    
    bike_pct = min(100, (bike_out_km / GOALS['bike_out']) * 100)
    zwift_pct = min(100, (zwift_km / GOALS['zwift']) * 100)
    run_pct = min(100, (run_km / GOALS['run']) * 100)
    
    streaks = calculate_streaks(df)
    
    return f"""
    <div class="stats-box-container">
        <div class="goals-section">
            <h3 style="margin:0 0 10px 0; font-size:14px; color:#64748b;">DOELEN {current_year}</h3>
            
            <div class="goal-item">
                <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:13px; font-weight:600;">
                    <span>🚴 Buiten: {bike_out_km:.0f} / {GOALS['bike_out']} km</span><span>{bike_pct:.1f}%</span>
                </div>
                <div style="background:#e2e8f0; height:8px; border-radius:4px; overflow:hidden;">
                    <div style="width:{bike_pct}%; background:{COLORS['bike_out']}; height:100%;"></div>
                </div>
            </div>
            
            <div class="goal-item" style="margin-top:12px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:13px; font-weight:600;">
                    <span>👾 Zwift: {zwift_km:.0f} / {GOALS['zwift']} km</span><span>{zwift_pct:.1f}%</span>
                </div>
                <div style="background:#e2e8f0; height:8px; border-radius:4px; overflow:hidden;">
                    <div style="width:{zwift_pct}%; background:{COLORS['zwift']}; height:100%;"></div>
                </div>
            </div>
            
            <div class="goal-item" style="margin-top:12px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:13px; font-weight:600;">
                    <span>🏃 Lopen: {run_km:.0f} / {GOALS['run']} km</span><span>{run_pct:.1f}%</span>
                </div>
                <div style="background:#e2e8f0; height:8px; border-radius:4px; overflow:hidden;">
                    <div style="width:{run_pct}%; background:{COLORS['run']}; height:100%;"></div>
                </div>
            </div>
        </div>
        
        <div class="streaks-section">
            <h3 style="margin:0 0 10px 0; font-size:14px; color:#64748b;">REEKSEN (STREAKS)</h3>
            <div class="streak-row"><span class="streak-label">🔥 Dagelijks:</span><span class="streak-val">{streaks.get('cur_day', 0)} dagen</span></div>
            <div class="streak-row"><span class="streak-label">📅 Record Dag:</span><span class="streak-val">{streaks.get('max_day', 0)} dagen</span></div>
            <div class="streak-sub">{streaks.get('max_day_range', '-')}</div>
            <div class="streak-row" style="margin-top:8px;"><span class="streak-label">⚡ Wekelijks:</span><span class="streak-val">{streaks.get('cur_week', 0)} weken</span></div>
            <div class="streak-row"><span class="streak-label">🗓️ Record Week:</span><span class="streak-val">{streaks.get('max_week', 0)} weken</span></div>
            <div class="streak-sub">{streaks.get('max_week_range', '-')}</div>
        </div>
    </div>
    """

def generate_sport_cards(df_cur, df_prev):
    html = '<div class="sport-grid">'
    # We itereren nu over de nieuwe Categorie kolom
    for cat in sorted(df_cur['Categorie'].unique()):
        if cat == 'Overig': continue # Sla overig even over voor netheid, of voeg toe indien gewenst
        
        dfs = df_cur[df_cur['Categorie'] == cat]
        dfp = pd.DataFrame()
        if df_prev is not None and not df_prev.empty:
            dfp = df_prev[df_prev['Categorie'] == cat]
        
        st = get_sport_style(cat)
        n = len(dfs); dist = dfs['Afstand_km'].sum(); tm = dfs['Beweegtijd_sec'].sum(); pn = len(dfp)
        
        dist_html = f'<div class="stat-col"><div class="label">Km</div><div class="val">{dist:,.0f}</div><div class="sub">{format_diff_html(dist, dfp["Afstand_km"].sum() if not dfp.empty else 0, "km")}</div></div>'
        if cat == 'Padel' or cat == 'Overig': 
            dist_html = '<div class="stat-col" style="opacity:0.3"><div class="label">Km</div><div class="val">-</div></div>'
        
        hr = dfs['Gemiddelde_Hartslag'].mean()
        hr_html = f'<div class="stat-row"><span>Hartslag</span> <strong class="hr-blur">{hr:.0f}</strong></div>' if pd.notna(hr) else ""

        html += f"""<div class="sport-card"><div class="sport-header"><div class="sport-icon-circle" style="color:{st['color']};background:{st['color']}20">{st['icon']}</div><h3>{cat}</h3></div>
        <div class="sport-body"><div class="stat-main"><div class="stat-col"><div class="label">Sessies</div><div class="val">{n}</div><div class="sub">{format_diff_html(n, pn)}</div></div><div class="stat-divider"></div>{dist_html}</div>
        <div class="sport-details"><div class="stat-row"><span>Tijd</span> <strong>{format_time(tm)}</strong></div>{hr_html}</div></div></div>"""
    return html + '</div>'

def generate_top3_list(df, col, unit, ascending=False, is_pace=False):
    df_sorted = df.sort_values(col, ascending=ascending).head(3)
    if df_sorted.empty: return ""
    html = '<div class="top3-list">'
    medals = ['🥇', '🥈', '🥉']
    for i, (idx, row) in enumerate(df_sorted.iterrows()):
        val = row[col]
        date_str = row['Datum'].strftime('%d %b %Y') if pd.notna(row['Datum']) else "-"
        val_str = ""
        if is_pace:
            pace_sec = 3600 / val if val > 0 else 0
            val_str = f"{int(pace_sec//60)}:{int(pace_sec%60):02d} /km"
        else:
            val_str = f"{val:.1f} {unit}"
            if unit == 'u': val_str = format_time(val)
        html += f"""<div class="top3-item"><span class="medal">{medals[i]}</span><span class="top3-val">{val_str}</span><span class="top3-date">{date_str}</span></div>"""
    return html + '</div>'

def generate_hall_of_fame(df):
    html = '<div class="hof-grid">'
    # Gebruik Categorie
    cats = ['Fiets', 'Virtueel', 'Hardlopen']
    for cat in cats:
        df_s = df[(df['Categorie'] == cat) & (df['Afstand_km'] > 1.0)].copy()
        if df_s.empty: continue
        
        style = get_sport_style(cat)
        speed_icon = "⚡"
        if cat == 'Fiets': speed_icon = "🚴⚡"
        if cat == 'Virtueel': speed_icon = "👾⚡"
        if cat == 'Hardlopen': speed_icon = "🏃⚡"
        
        t3_dist = generate_top3_list(df_s, 'Afstand_km', 'km', ascending=False)
        t3_time = generate_top3_list(df_s, 'Beweegtijd_sec', 'u', ascending=False)
        
        t3_speed = ""
        if cat == 'Fiets' or cat == 'Virtueel':
            df_spd = df_s[(df_s['Gemiddelde_Snelheid_km_u'] > 10) & (df_s['Gemiddelde_Snelheid_km_u'] < 85)]
            t3_speed = generate_top3_list(df_spd, 'Gemiddelde_Snelheid_km_u', 'km/u', ascending=False)
        elif cat == 'Hardlopen':
            df_spd = df_s[(df_s['Gemiddelde_Snelheid_km_u'] > 5) & (df_s['Gemiddelde_Snelheid_km_u'] < 30)]
            t3_speed = generate_top3_list(df_spd, 'Gemiddelde_Snelheid_km_u', '', ascending=False, is_pace=True)
            
        html += f"""<div class="hof-card"><div class="hof-header" style="color:{style['color']}"><span style="font-size:20px;margin-right:8px">{style['icon']}</span> {cat}</div><div class="hof-section"><div class="hof-label">Langste Afstand</div>{t3_dist}</div><div class="hof-section"><div class="hof-label">Snelste (Gem.) <span style="font-size:12px">{speed_icon}</span></div>{t3_speed if t3_speed else '<span style="color:#ccc;font-size:11px">-</span>'}</div><div class="hof-section" style="border:none"><div class="hof-label">Langste Duur</div>{t3_time}</div></div>"""
    return html + "</div>"

def generate_detail_table(df, uid):
    if df.empty: return "<p style='text-align:center;color:#999'>Geen activiteiten gevonden.</p>"
    # Filter dropdown op Categorie
    opts = "".join([f'<option value="{s}">{s}</option>' for s in sorted(df['Categorie'].unique())])
    rows = ""
    for _, r in df.sort_values('Datum', ascending=False).iterrows():
        st = get_sport_style(r['Categorie'])
        hr = f"{r['Gemiddelde_Hartslag']:.0f}" if pd.notna(r['Gemiddelde_Hartslag']) else "-"
        date_str = r["Datum"].strftime("%d-%m-%y") if pd.notna(r["Datum"]) else "-"
        rows += f'<tr data-sport="{r["Categorie"]}"><td><div style="width:8px;height:8px;border-radius:50%;background:{st["color"]}"></div></td><td>{date_str}</td><td>{r["Categorie"]}</td><td>{r["Naam"]}</td><td class="num">{r["Afstand_km"]:.1f}</td><td class="num hr-blur">{hr}</td></tr>'
    return f"""<div class="detail-section"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px"><h3 style="margin:0;font-size:16px;">Logboek</h3><select id="sf-{uid}" onchange="filterTable('{uid}')" style="padding:5px;border-radius:6px;border:1px solid #ddd"><option value="ALL">Alles</option>{opts}</select></div><div style="overflow-x:auto"><table id="dt-{uid}"><thead><tr><th></th><th>Datum</th><th>Type</th><th>Naam</th><th class="num">Km</th><th class="num">❤️</th></tr></thead><tbody>{rows}</tbody></table></div></div>"""

def create_cycling_chart(df_yr, df_prev, year):
    # Gebruik Categorie ipv regex in chart
    df_yr = df_yr.sort_values('DagVanJaar'); df_prev = df_prev.sort_values('DagVanJaar')
    
    df_zwift = df_yr[df_yr['Categorie'] == 'Virtueel'].copy()
    df_zwift['C'] = df_zwift['Afstand_km'].cumsum()
    df_out = df_yr[df_yr['Categorie'] == 'Fiets'].copy()
    df_out['C'] = df_out['Afstand_km'].cumsum()
    
    df_zwift_prev = df_prev[df_prev['Categorie'] == 'Virtueel'].copy()
    df_zwift_prev['C'] = df_zwift_prev['Afstand_km'].cumsum()
    df_out_prev = df_prev[df_prev['Categorie'] == 'Fiets'].copy()
    df_out_prev['C'] = df_out_prev['Afstand_km'].cumsum()
    
    if df_zwift.empty and df_out.empty and df_out_prev.empty and df_zwift_prev.empty: return ""

    fig = px.line(title=f"🚴 Wieler-Koers {year}")
    if not df_out_prev.empty: fig.add_scatter(x=df_out_prev['DagVanJaar'], y=df_out_prev['C'], name=f"🚴 Buiten {int(year)-1}", line_color=COLORS['bike_out_prev'], line_dash='dot')
    if not df_zwift_prev.empty: fig.add_scatter(x=df_zwift_prev['DagVanJaar'], y=df_zwift_prev['C'], name=f"👾 Zwift {int(year)-1}", line_color=COLORS['zwift_prev'], line_dash='dot')
    if not df_out.empty: fig.add_scatter(x=df_out['DagVanJaar'], y=df_out['C'], name=f"🚴 Buiten {int(year)}", line_color=COLORS['bike_out'], line_width=3)
    if not df_zwift.empty: fig.add_scatter(x=df_zwift['DagVanJaar'], y=df_zwift['C'], name=f"👾 Zwift {int(year)}", line_color=COLORS['zwift'], line_width=3)

    fig.update_layout(template='plotly_white', margin=dict(t=40,b=20,l=20,r=20), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=1.1))
    return f'<div class="chart-box full-width">{fig.to_html(full_html=False, include_plotlyjs="cdn")}</div>'

def create_running_chart(df_yr, df_prev, year):
    df_yr = df_yr.sort_values('DagVanJaar'); df_prev = df_prev.sort_values('DagVanJaar')
    df_run = df_yr[df_yr['Categorie'] == 'Hardlopen'].copy()
    df_run['C'] = df_run['Afstand_km'].cumsum()
    df_ref = df_prev[df_prev['Categorie'] == 'Hardlopen'].copy()
    df_ref['C'] = df_ref['Afstand_km'].cumsum()
    
    if df_run.empty and df_ref.empty: return ""
    fig = px.line(title=f"🏃 Hardloop-Koers {year}")
    if not df_ref.empty: fig.add_scatter(x=df_ref['DagVanJaar'], y=df_ref['C'], name=f"🏃 {int(year)-1}", line_color=COLORS['run_prev'], line_dash='dot')
    if not df_run.empty: fig.add_scatter(x=df_run['DagVanJaar'], y=df_run['C'], name=f"🏃 {int(year)}", line_color=COLORS['run'], line_width=3)
    fig.update_layout(template='plotly_white', margin=dict(t=40,b=20,l=20,r=20), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=1.1))
    return f'<div class="chart-box full-width">{fig.to_html(full_html=False, include_plotlyjs="cdn")}</div>'

def create_donut_chart(df, year):
    if df.empty: return ""
    stats = df.groupby('Categorie')['Beweegtijd_sec'].sum().reset_index()
    if stats.empty: return ""
    colors = []
    for cat in stats['Categorie']:
        st = get_sport_style(cat)
        colors.append(st['color'])
    fig = px.pie(stats, values='Beweegtijd_sec', names='Categorie', title=f"Tijdsverdeling {year}", hole=0.5, color_discrete_sequence=colors)
    fig.update_layout(template='plotly_white', margin=dict(t=40,b=20,l=20,r=20), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
    fig.update_traces(textinfo='percent+label', hovertemplate='%{label}: %{percent}')
    return f'<div class="chart-box full-width">{fig.to_html(full_html=False, include_plotlyjs="cdn")}</div>'

def create_monthly_split(df, year):
    df_cur = df[df['Jaar'] == year].copy(); df_prev = df[df['Jaar'] == year - 1].copy()
    if df_cur.empty and df_prev.empty: return ""
    df_cur['Maand'] = df_cur['Datum'].dt.month; df_prev['Maand'] = df_prev['Datum'].dt.month
    months = ['Jan','Feb','Mrt','Apr','Mei','Jun','Jul','Aug','Sep','Okt','Nov','Dec']
    
    # 1. FIETS (Buiten + Virtueel voor maandoverzicht? Nee, splitsen is beter of samen? 
    # User vroeg "afstand per maand opsplitsen in lopen en fietsen". Fietsen is meestal alles fietsen.
    # Laten we Buiten + Virtueel samenvoegen voor "Fietsen totaal" in de maandgrafiek, 
    # OF enkel buiten. Gezien de focus op doelen splitsen we ze misschien best?
    # De user zei: "opsplitsen in lopen en fietsen". Ik pak ALLE fietsen (binnen+buiten) hier.
    
    cur_bike = df_cur[df_cur['Categorie'].isin(['Fiets', 'Virtueel'])]
    prev_bike = df_prev[df_prev['Categorie'].isin(['Fiets', 'Virtueel'])]
    
    bike_m_cur = cur_bike.groupby('Maand')['Afstand_km'].sum().reindex(range(1,13), fill_value=0)
    bike_m_prev = prev_bike.groupby('Maand')['Afstand_km'].sum().reindex(range(1,13), fill_value=0)
    
    fig_bike = go.Figure()
    fig_bike.add_trace(go.Bar(x=months, y=bike_m_prev, name=str(year-1), marker_color='#cbd5e1'))
    fig_bike.add_trace(go.Bar(x=months, y=bike_m_cur, name=str(year), marker_color=COLORS['bike_out']))
    fig_bike.update_layout(title="🚴 Afstand Fietsen (Totaal)", template='plotly_white', barmode='group', margin=dict(t=40,b=20,l=20,r=20), height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
    
    # 2. LOOP
    cur_run = df_cur[df_cur['Categorie'] == 'Hardlopen']
    prev_run = df_prev[df_prev['Categorie'] == 'Hardlopen']
    
    run_m_cur = cur_run.groupby('Maand')['Afstand_km'].sum().reindex(range(1,13), fill_value=0)
    run_m_prev = prev_run.groupby('Maand')['Afstand_km'].sum().reindex(range(1,13), fill_value=0)
    
    fig_run = go.Figure()
    fig_run.add_trace(go.Bar(x=months, y=run_m_prev, name=str(year-1), marker_color='#cbd5e1'))
    fig_run.add_trace(go.Bar(x=months, y=run_m_cur, name=str(year), marker_color=COLORS['run']))
    fig_run.update_layout(title="🏃 Afstand Lopen", template='plotly_white', barmode='group', margin=dict(t=40,b=20,l=20,r=20), height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
    
    return f"""<div style="display:flex; flex-wrap:wrap; gap:10px;"><div style="flex:1; min-width:300px;" class="chart-box">{fig_bike.to_html(full_html=False, include_plotlyjs="cdn")}</div><div style="flex:1; min-width:300px;" class="chart-box">{fig_run.to_html(full_html=False, include_plotlyjs="cdn")}</div></div>"""

def create_yearly_evolution(df):
    stats = df.groupby(['Jaar', 'Categorie'])['Afstand_km'].sum().unstack(fill_value=0)
    if stats.empty: return ""
    years = stats.index
    fig = go.Figure()
    # Stapelen we Binnen en Buiten op voor "Fietsen"?
    # User: "grafiek afstand totaal per fiets en lopen apart"
    
    # Fiets Totaal (Buiten + Virtueel)
    bike_tot = stats.get('Fiets', 0) + stats.get('Virtueel', 0)
    run_tot = stats.get('Hardlopen', 0)
    
    fig.add_trace(go.Bar(x=years, y=bike_tot, name='Fietsen (Tot)', marker_color=COLORS['bike_out']))
    fig.add_trace(go.Bar(x=years, y=run_tot, name='Lopen', marker_color=COLORS['run']))
        
    fig.update_layout(title="Evolutie Totaal per Jaar", template='plotly_white', barmode='group', margin=dict(t=40,b=20,l=20,r=20), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=1.1))
    return f'<div class="chart-box full-width">{fig.to_html(full_html=False, include_plotlyjs="cdn")}</div>'

def create_heatmap(df, year):
    df_yr = df[df['Jaar'] == year].copy()
    if df_yr.empty: return ""
    df_yr['Week'] = df_yr['Datum'].dt.isocalendar().week
    df_yr['Dag'] = df_yr['Datum'].dt.dayofweek
    heatmap_data = df_yr.groupby(['Week', 'Dag'])['Beweegtijd_sec'].sum().reset_index()
    heatmap_data['Minuten'] = heatmap_data['Beweegtijd_sec'] / 60
    matrix = np.zeros((7, 53))
    for _, row in heatmap_data.iterrows():
        w = int(row['Week']) - 1; d = int(row['Dag'])
        if 0 <= w < 53: matrix[d, w] = row['Minuten']
    days = ['Ma', 'Di', 'Wo', 'Do', 'Vr', 'Za', 'Zo']
    fig = go.Figure(data=go.Heatmap(z=matrix, x=list(range(1, 54)), y=days, colorscale=[[0, '#f1f5f9'], [0.01, '#bbf7d0'], [0.5, '#22c55e'], [1, '#14532d']], showscale=False, ygap=2, xgap=2))
    fig.update_layout(title=f"Consistentie {year}", height=200, margin=dict(t=30,b=20,l=30,r=20), xaxis=dict(showgrid=False, zeroline=False, tickmode='array', tickvals=[1,10,20,30,40,50], ticktext=['Jan','Mrt','Mei','Jul','Sep','Nov']), yaxis=dict(showgrid=False, zeroline=False, autorange='reversed'), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return f'<div class="chart-box full-width">{fig.to_html(full_html=False, include_plotlyjs="cdn")}</div>'

# --- MAIN ---
def genereer_dashboard():
    print("🚀 Start V31.0 (Strict Categorization)...")
    try: df = pd.read_csv('activities.csv')
    except: return print("❌ Geen activities.csv gevonden!")

    nm = {
        'Datum van activiteit': 'Datum', 'Naam activiteit': 'Naam', 'Activiteitstype': 'Activiteitstype',
        'Beweegtijd': 'Beweegtijd_sec', 'Afstand': 'Afstand_km', 'Totale stijging': 'Hoogte_m',
        'Gemiddelde hartslag': 'Gemiddelde_Hartslag', 'Gemiddelde snelheid': 'Gemiddelde_Snelheid_km_u',
        'Max. snelheid': 'Max_Snelheid_km_u', 'Uitrusting voor activiteit': 'Uitrusting voor activiteit'
    }
    df = df.rename(columns={k:v for k,v in nm.items() if k in df.columns})
    for c in ['Afstand_km', 'Hoogte_m', 'Gemiddelde_Hartslag', 'Gemiddelde_Snelheid_km_u', 'Max_Snelheid_km_u']:
        if c in df.columns: df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce')

    df = apply_data_logic(df)
    df['Jaar'] = df['Datum'].dt.year
    df['DagVanJaar'] = df['Datum'].dt.dayofyear
    
    genereer_manifest()
    
    nav, sects = "", ""
    today_doy = datetime.now().timetuple().tm_yday
    years = sorted(df['Jaar'].dropna().unique(), reverse=True)
    gold_banner = generate_gold_banner()
    global_hof = generate_hall_of_fame(df)
    current_year = datetime.now().year
    stats_box = generate_stats_box(df, current_year)
    
    for yr in years:
        is_cur = (yr == datetime.now().year)
        df_yr = df[df['Jaar'] == yr]
        df_prev_yr = df[df['Jaar'] == yr-1]
        df_prev_comp = df_prev_yr[df_prev_yr['DagVanJaar'] <= today_doy] if is_cur else df_prev_yr
        
        sc = {'n': len(df_yr), 'km': df_yr['Afstand_km'].sum(), 'h': df_yr['Hoogte_m'].sum(), 't': df_yr['Beweegtijd_sec'].sum()}
        sp = {'n': len(df_prev_comp), 'km': df_prev_comp['Afstand_km'].sum(), 'h': df_prev_comp['Hoogte_m'].sum(), 't': df_prev_comp['Beweegtijd_sec'].sum()}
        
        kpis = f"""<div class="kpi-grid">{generate_kpi("Sessies", sc['n'], "🔥", format_diff_html(sc['n'], sp['n']))}
        {generate_kpi("Afstand", f"{sc['km']:,.0f} km", "📏", format_diff_html(sc['km'], sp['km'], "km"))}
        {generate_kpi("Hoogtemeters", f"{sc['h']:,.0f} m", "⛰️", format_diff_html(sc['h'], sp['h'], "m"))}
        {generate_kpi("Tijd", format_time(sc['t']), "⏱️", format_diff_html((sc['t']-sp['t'])/3600, 0, "u"))}</div>"""
        
        chart_fiets = create_cycling_chart(df_yr, df_prev_yr, yr)
        chart_loop = create_running_chart(df_yr, df_prev_yr, yr)
        chart_donut = create_donut_chart(df_yr, int(yr))
        chart_monthly_split = create_monthly_split(df, int(yr))
        chart_heatmap = create_heatmap(df, int(yr))
        
        top3 = f'<h3 class="section-subtitle">Top Prestaties {int(yr)}</h3>{generate_hall_of_fame(df_yr)}'
        tbl = generate_detail_table(df_yr, str(int(yr)))

        nav += f'<button class="nav-btn {"active" if is_cur else ""}" onclick="openTab(event, \'v-{int(yr)}\')">{int(yr)}</button>'
        sects += f"""<div id="v-{int(yr)}" class="tab-content" style="display:{"block" if is_cur else "none"}"><h2 class="section-title">Overzicht {int(yr)}</h2>{kpis}<h3 class="section-subtitle">Per Sport</h3>{generate_sport_cards(df_yr, df_prev_comp)}<h3 class="section-subtitle">Maandelijkse Voortgang</h3>{chart_monthly_split}<div style="display:flex; gap:10px; overflow-x:auto;"><div style="flex:1; min-width:280px;">{chart_donut}</div></div><h3 class="section-subtitle">Koersverloop</h3>{chart_fiets}{chart_loop}<h3 class="section-subtitle">Consistentie</h3>{chart_heatmap}{top3}{tbl}</div>"""

    tbl_tot = generate_detail_table(df, "Tot")
    chart_donut_tot = create_donut_chart(df, "Totaal")
    chart_yearly_evol = create_yearly_evolution(df)
    
    nav += '<button class="nav-btn" onclick="openTab(event, \'v-Tot\')">Totaal</button>'
    sects += f"""<div id="v-Tot" class="tab-content" style="display:none"><h2 class="section-title">Carrière</h2><div class="kpi-grid">
        {generate_kpi("Sessies", len(df), "🏆")}
        {generate_kpi("Km", f"{df['Afstand_km'].sum():,.0f}", "🌍")}
        {generate_kpi("Tijd", format_time(df['Beweegtijd_sec'].sum()), "⏱️")}
        </div>{generate_sport_cards(df, pd.DataFrame())}
        <h3 class="section-subtitle">Jarenvergelijking</h3>{chart_yearly_evol}{chart_donut_tot}{tbl_tot}</div>"""
    
    nav += '<button class="nav-btn" onclick="openTab(event, \'v-Gar\')">Garage</button>'
    sects += f'<div id="v-Gar" class="tab-content" style="display:none"><h2 class="section-title">De Garage</h2>{generate_gear_section(df)}</div>'
    sects += f'<div id="v-HOF-overlay" style="display:none; margin-top:20px; border-top:2px dashed #e2e8f0; padding-top:20px;"><h2 class="section-title">All-Time Eregalerij</h2>{global_hof}</div>'

    html = f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"><link rel="manifest" href="manifest.json"><link rel="apple-touch-icon" href="1768922516256~2.jpg"><title>Sport Jorden</title><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"><style>
    :root{{--primary:{COLORS['primary']};--gold:{COLORS['gold']};--gold-bg:{COLORS['gold_bg']};--bg:{COLORS['bg']};--card:{COLORS['card']};--text:{COLORS['text']}}}
    body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);margin:0;padding:20px;padding-bottom:80px;-webkit-tap-highlight-color:transparent}}
    .container{{max-width:1000px;margin:0 auto}}
    h1{{margin:0;font-size:24px;font-weight:700;color:var(--primary);display:flex;align-items:center;gap:10px}}
    h1::after{{content:'';display:block;width:40px;height:3px;background:var(--gold);border-radius:2px}}
    .header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:15px}}
    .lock-btn{{background:white;border:1px solid #cbd5e1;padding:6px 12px;border-radius:20px;font-size:13px;font-weight:600;color:#64748b;transition:0.2s}}
    .gold-banner {{ cursor:pointer; background: linear-gradient(135deg, var(--gold) 0%, var(--gold-bg) 100%); color:white; border-radius:12px; padding:12px 16px; margin-bottom:20px; display:flex; align-items:center; gap:12px; box-shadow:0 4px 6px -1px rgba(212, 175, 55, 0.3); transition: transform 0.1s; }}
    .gold-banner:active {{ transform: scale(0.98); }}
    .gold-icon {{ font-size:24px; }}
    .stats-box-container {{ display:flex; gap:15px; margin-bottom:20px; flex-wrap:wrap; }}
    .goals-section, .streaks-section {{ flex:1; background:white; padding:15px; border-radius:12px; border:1px solid #e2e8f0; min-width:280px; }}
    .streak-row {{ display:flex; justify-content:space-between; margin-bottom:2px; font-size:13px; font-weight:600; }}
    .streak-label {{ color:#64748b; }}
    .streak-val {{ color:var(--primary); }}
    .streak-sub {{ font-size:11px; color:#94a3b8; text-align:right; margin-bottom:4px; font-style:italic; }}
    .nav{{display:flex;gap:8px;overflow-x:auto;padding-bottom:10px;margin-bottom:20px;scrollbar-width:none}}.nav::-webkit-scrollbar{{display:none}}
    .nav-btn{{flex:0 0 auto;background:white;border:1px solid #e2e8f0;padding:8px 16px;border-radius:20px;font-size:14px;font-weight:600;color:#64748b;transition:0.2s}}
    .nav-btn.active{{background:var(--primary);color:white;border-color:var(--primary)}}
    .kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:25px}}
    .sport-grid,.hof-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:15px;margin-bottom:25px}}
    .kpi-card,.sport-card,.chart-box,.detail-section,.hof-card{{background:var(--card);border-radius:16px;padding:16px;box-shadow:0 2px 4px rgba(0,0,0,0.03);border:1px solid #f1f5f9}}
    .sport-header{{display:flex;align-items:center;gap:10px;margin-bottom:12px}}
    .sport-icon-circle{{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px}}
    .stat-main{{display:flex;margin-bottom:12px}}
    .stat-col{{flex:1}}
    .stat-divider{{width:1px;background:#e2e8f0;margin:0 12px}}
    .label{{font-size:10px;text-transform:uppercase;color:#94a3b8;font-weight:700}}
    .val{{font-size:18px;font-weight:700;color:var(--primary)}}
    .sub{{font-size:11px;margin-top:2px}}
    .sport-details{{background:#f8fafc;padding:10px;border-radius:8px;font-size:12px}}
    .stat-row{{display:flex;justify-content:space-between;margin-bottom:4px;color:#64748b}}
    .stat-row strong{{color:var(--text)}}
    table{{width:100%;border-collapse:collapse;font-size:13px}}
    th{{text-align:left;color:#94a3b8;font-size:10px;text-transform:uppercase;padding:10px}}
    td{{padding:10px;border-bottom:1px solid #f1f5f9}}
    .num{{text-align:right;font-weight:600}}
    .hr-blur{{filter:blur(4px);background:#e2e8f0;border-radius:4px;color:transparent;transition:0.3s}}
    .section-title{{font-size:18px;font-weight:700;margin-bottom:15px;color:var(--primary)}}
    .section-subtitle{{font-size:12px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin:25px 0 10px 0}}
    .hof-card {{ display:flex; flex-direction:column; gap:12px; }}
    .hof-section {{ border-bottom:1px solid #f1f5f9; padding-bottom:8px; }}
    .hof-label {{ font-size:10px; text-transform:uppercase; color:#94a3b8; font-weight:700; margin-bottom:6px; }}
    .top3-list {{ display:flex; flex-direction:column; gap:6px; }}
    .top3-item {{ display:flex; justify-content:space-between; align-items:center; font-size:13px; }}
    .medal {{ font-size:14px; margin-right:6px; }}
    .top3-val {{ font-weight:700; color:var(--text); }}
    .top3-date {{ font-size:11px; color:#94a3b8; }}
    </style></head><body><div class="container"><div class="header"><h1>Sport Jorden</h1><button class="lock-btn" onclick="unlock()">❤️ 🔒</button></div>{gold_banner}{stats_box}<div id="hof-container">{global_hof}</div><div class="nav">{nav}</div>{sects}</div><script>
    document.getElementById('hof-container').style.display = 'none';
    function toggleHOF() {{ var x = document.getElementById('hof-container'); x.style.display = (x.style.display === 'none') ? 'grid' : 'none'; }}
    function openTab(e,n){{document.querySelectorAll('.tab-content').forEach(x=>x.style.display='none');document.querySelectorAll('.nav-btn').forEach(x=>x.classList.remove('active'));document.getElementById(n).style.display='block';e.currentTarget.classList.add('active');document.getElementById('hof-container').style.display = 'none';}}
    function filterTable(uid){{var v=document.getElementById('sf-'+uid).value;document.querySelectorAll('#dt-'+uid+' tbody tr').forEach(tr=>tr.style.display=(v==='ALL'||tr.dataset.sport===v)?'':'none')}}function unlock(){{if(prompt("Wachtwoord:")==='Nala'){{document.querySelectorAll('.hr-blur').forEach(e=>{{e.style.filter='none';e.style.color='inherit';e.style.background='transparent'}});document.querySelector('.lock-btn').style.display='none'}}}}</script></body></html>"""
    
    with open('dashboard.html', 'w', encoding='utf-8') as f: f.write(html)
    print("✅ Dashboard (V31.0) gegenereerd: Strict Categorization & Fixed Totals.")

if __name__ == "__main__":
    genereer_dashboard()
