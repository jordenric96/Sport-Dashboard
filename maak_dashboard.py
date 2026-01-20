import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime

# --- CONFIGURATIE: NEON STYLE (TDT + PINK/BLUE) ---
COLORS = {
    'primary': '#D9F535',       # TDT Volt (Neon Geel) - Padel
    'primary_text': '#000000',  # Zwart op geel
    'neon_blue': '#00F0FF',     # Neon Cyaan/Blauw - Fietsen
    'neon_pink': '#FF00CC',     # Neon Roos - Hardlopen
    'bg': '#121212',            # Donkere achtergrond voor beter contrast met neon
    'card': '#1E1E1E',          # Donkergrijze kaarten
    'text': '#FFFFFF',          # Witte tekst
    'muted': '#AAAAAA',         # Grijs
    'success': '#00E676',       # Fel Groen
    'danger': '#FF1744'         # Fel Rood
}

# Iconen en kleuren per sport (Aangepast met Neon Roos/Blauw)
SPORT_CONFIG = {
    'Fiets': {'icon': '🚴', 'color': COLORS['neon_blue'], 'text': '#000'},
    'Virtuele fietsrit': {'icon': '👾', 'color': '#7B61FF', 'text': '#FFF'}, # Neon Paars
    'Hardloop': {'icon': '🏃', 'color': COLORS['neon_pink'], 'text': '#FFF'},
    'Wandel': {'icon': '🚶', 'color': '#00E676', 'text': '#000'}, # Neon Groen
    'Padel': {'icon': '🎾', 'color': COLORS['primary'], 'text': '#000'}, 
    'Hike': {'icon': '🥾', 'color': '#00E5FF', 'text': '#000'},
    'Zwemmen': {'icon': '🏊', 'color': COLORS['neon_blue'], 'text': '#000'},
    'Default': {'icon': '🏅', 'color': '#888888', 'text': '#FFF'}
}

def get_sport_style(sport_name):
    for key, config in SPORT_CONFIG.items():
        if key.lower() in str(sport_name).lower():
            return config
    return SPORT_CONFIG['Default']

# --- HULPFUNCTIES ---
def format_time(seconds):
    if pd.isna(seconds) or seconds <= 0: return '-'
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f'{hours}u {minutes:02d}m'

def format_diff_html(current, previous, unit="", inverse=False):
    if pd.isna(previous) or previous == 0:
        return '<span class="diff-neutral">Start</span>'
    diff = current - previous
    if diff == 0: return '<span class="diff-neutral">-</span>'
    
    is_good = (diff > 0) if not inverse else (diff < 0)
    color = COLORS['success'] if is_good else COLORS['danger']
    arrow = "▲" if diff > 0 else "▼"
    val_str = f"{abs(diff):.1f}" if isinstance(diff, float) else f"{abs(int(diff))}"
    return f'<span style="color: {color}; font-weight: bold; font-size: 0.85em;">{arrow} {val_str} {unit}</span>'

def robust_date_parser(date_series):
    dutch_month_mapping = {
        'jan': 'Jan', 'feb': 'Feb', 'mrt': 'Mar', 'apr': 'Apr', 
        'mei': 'May', 'jun': 'Jun', 'jul': 'Jul', 'aug': 'Aug', 
        'sep': 'Sep', 'okt': 'Oct', 'nov': 'Nov', 'dec': 'Dec'
    }
    date_series_str = date_series.astype(str).str.lower()
    for dutch, eng in dutch_month_mapping.items():
        date_series_str = date_series_str.str.replace(dutch, eng, regex=False)
    dates = pd.to_datetime(date_series_str, format='%d %b %Y, %H:%M:%S', errors='coerce')
    mask = dates.isna()
    if mask.any():
        dates[mask] = pd.to_datetime(date_series_str[mask], errors='coerce', dayfirst=True)
    return dates

# --- HTML GENERATORS ---

def generate_kpi(title, value, subtext="", icon="", diff=""):
    return f"""
    <div class="kpi-card">
        <div class="kpi-top"><span class="kpi-icon">{icon}</span><span class="kpi-title">{title}</span></div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{diff} <span style="color:{COLORS['muted']}">{subtext}</span></div>
    </div>
    """

def generate_sport_cards(df_cur, df_prev):
    html = '<div class="sport-grid">'
    sports = sorted(df_cur['Activiteitstype'].unique())
    
    for sport in sports:
        df_s_cur = df_cur[df_cur['Activiteitstype'] == sport]
        if df_prev is not None and not df_prev.empty:
            df_s_prev = df_prev[df_prev['Activiteitstype'] == sport]
            prev_count = len(df_s_prev)
            prev_dist = df_s_prev['Afstand_km'].sum()
        else:
            prev_count = 0
            prev_dist = 0
            
        style = get_sport_style(sport)
        count = len(df_s_cur)
        dist = df_s_cur['Afstand_km'].sum()
        time = df_s_cur['Beweegtijd_sec'].sum()
        avg_hr = df_s_cur['Gemiddelde_Hartslag'].mean()
        
        diff_count = format_diff_html(count, prev_count)
        diff_dist = format_diff_html(dist, prev_dist, "km")
        
        extra_stat = ""
        if 'Fiets' in sport:
            max_spd = df_s_cur['Max_Snelheid_km_u'].max()
            if max_spd > 0: extra_stat = f'<div class="stat-row"><span>Max snelheid</span> <strong>{max_spd:.1f} km/u</strong></div>'
        else:
            max_dst = df_s_cur['Afstand_km'].max()
            if max_dst > 0: extra_stat = f'<div class="stat-row"><span>Langste</span> <strong>{max_dst:.1f} km</strong></div>'
        
        hr_html = ""
        if pd.notna(avg_hr) and avg_hr > 0:
            hr_html = f'<div class="stat-row"><span>Gem. Hartslag</span> <strong class="hr-blur">{avg_hr:.0f} bpm</strong></div>'

        head_col = style.get('text', '#FFF') 

        html += f"""
        <div class="sport-card" style="border-top: 3px solid {style['color']}">
            <div class="sport-header" style="background: {style['color']}; color: {head_col};">
                <span class="sport-icon-small">{style['icon']}</span><h3>{sport}</h3>
            </div>
            <div class="sport-body">
                <div class="stat-main">
                    <div><div class="label">Sessies</div><div class="val">{count}</div><div class="sub">{diff_count}</div></div>
                    <div><div class="label">Afstand</div><div class="val">{dist:,.0f} <span style="font-size:0.7em">km</span></div><div class="sub">{diff_dist}</div></div>
                </div>
                <div class="sport-details">
                    <div class="stat-row"><span>Totaal tijd</span> <strong>{format_time(time)}</strong></div>
                    {extra_stat}
                    {hr_html}
                </div>
            </div>
        </div>
        """
    html += '</div>'
    return html

def generate_hall_of_fame(df):
    html = '<div class="hof-grid">'
    sports = sorted(df['Activiteitstype'].unique())
    
    for sport in sports:
        df_s = df[df['Activiteitstype'] == sport]
        if df_s.empty: continue
        style = get_sport_style(sport)
        records = []
        
        # 1. Langste Afstand
        idx_dist = df_s['Afstand_km'].idxmax()
        if pd.notna(idx_dist):
            row = df_s.loc[idx_dist]
            records.append({'label': 'Langste', 'val': f"{row['Afstand_km']:.1f} km", 'date': row['Datum'], 'icon': '📏'})
            
        # 2. Snelste
        if 'Fiets' in sport:
            idx_spd = df_s['Max_Snelheid_km_u'].idxmax()
            if pd.notna(idx_spd) and df_s.loc[idx_spd, 'Max_Snelheid_km_u'] > 0:
                row = df_s.loc[idx_spd]
                records.append({'label': 'Snelste', 'val': f"{row['Max_Snelheid_km_u']:.1f} km/u", 'date': row['Datum'], 'icon': '🚀'})
        elif 'Hardloop' in sport:
             idx_spd = df_s['Gemiddelde_Snelheid_km_u'].idxmax()
             if pd.notna(idx_spd) and df_s.loc[idx_spd, 'Gemiddelde_Snelheid_km_u'] > 0:
                row = df_s.loc[idx_spd]
                pace_sec = 3600 / row['Gemiddelde_Snelheid_km_u']
                pace = f"{int(pace_sec//60)}:{int(pace_sec%60):02d} /km"
                records.append({'label': 'Snelste Pace', 'val': pace, 'date': row['Datum'], 'icon': '⚡'})

        # 3. Langste Duur
        idx_time = df_s['Beweegtijd_sec'].idxmax()
        if pd.notna(idx_time):
             row = df_s.loc[idx_time]
             records.append({'label': 'Langste Duur', 'val': format_time(row['Beweegtijd_sec']), 'date': row['Datum'], 'icon': '⏱️'})
             
        rec_html = ""
        for r in records:
            date_str = r['date'].strftime('%d %b %Y')
            rec_html += f"""
            <div class="hof-record">
                <div class="hof-icon" style="color:{style['color']}">{r['icon']}</div>
                <div class="hof-data">
                    <div class="hof-label">{r['label']}</div>
                    <div class="hof-val">{r['val']}</div>
                    <div class="hof-date">{date_str}</div>
                </div>
            </div>
            """
            
        html += f"""
        <div class="hof-card">
             <div class="hof-header" style="border-bottom: 2px solid {style['color']}">
                <h3 style="color:{style['color']}">{style['icon']} {sport}</h3>
             </div>
             <div class="hof-body">{rec_html}</div>
        </div>
        """
    html += "</div>"
    return html

def genereer_dashboard(csv_input='activities.csv', html_output='dashboard.html'):
    print("🚀 Start Generatie Neon Editie...")
    try:
        df = pd.read_csv(csv_input)
    except:
        print("❌ CSV niet gevonden.")
        return

    # Renames & Cleaning
    df = df.rename(columns={
        'Datum van activiteit': 'Datum', 'Naam activiteit': 'Naam', 
        'Activiteitstype': 'Activiteitstype', 'Beweegtijd': 'Beweegtijd_sec',
        'Afstand': 'Afstand_km', 'Totale stijging': 'Hoogte_m',
        'Gemiddelde hartslag': 'Gemiddelde_Hartslag',
        'Gemiddelde snelheid': 'Gemiddelde_Snelheid_km_u',
        'Max. snelheid': 'Max_Snelheid_km_u'
    })
    
    cols = ['Afstand_km', 'Hoogte_m', 'Gemiddelde_Snelheid_km_u', 'Gemiddelde_Hartslag', 'Max_Snelheid_km_u']
    for c in cols:
        if c in df.columns and df[c].dtype == object:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce')

    # PADEL LOGICA
    padel_types = ['Training', 'Workout', 'WeightTraining', 'Krachttraining', 'Fitness']
    mask_padel = df['Activiteitstype'].isin(padel_types) | df['Activiteitstype'].str.contains('Training', case=False)
    df.loc[mask_padel, 'Activiteitstype'] = 'Padel'

    mask_swim = df['Activiteitstype'].str.contains('Zwemmen', case=False)
    df.loc[mask_swim, 'Afstand_km'] /= 1000
    
    df['Datum'] = robust_date_parser(df['Datum'])
    df['Jaar'] = df['Datum'].dt.year
    df['DagVanJaar'] = df['Datum'].dt.dayofyear
    
    now = datetime.now()
    huidig_jaar = now.year
    max_datum = df['Datum'].max()
    ytd_day = max_datum.dayofyear if max_datum.year == huidig_jaar else 366

    # --- HTML ---
    nav_html = ""
    sections_html = ""
    jaren = sorted(df['Jaar'].unique(), reverse=True)
    
    # 1. JAAR TABS
    for jaar in jaren:
        is_current = (jaar == max_datum.year)
        df_jaar = df[df['Jaar'] == jaar]
        
        # YTD
        prev_jaar = jaar - 1
        df_prev_full = df[df['Jaar'] == prev_jaar]
        if is_current:
            df_prev_comp = df_prev_full[df_prev_full['DagVanJaar'] <= ytd_day]
        else:
            df_prev_comp = df_prev_full

        s_cur = {'n': len(df_jaar), 'km': df_jaar['Afstand_km'].sum(), 'h': df_jaar['Hoogte_m'].sum()}
        s_prev = {'n': len(df_prev_comp), 'km': df_prev_comp['Afstand_km'].sum(), 'h': df_prev_comp['Hoogte_m'].sum()}
        
        label = "t.o.v. YTD vorig jaar" if is_current else "t.o.v. vorig jaar"
        
        kpis = f"""<div class="kpi-grid">
            {generate_kpi("Sessies", s_cur['n'], label, "🔥", format_diff_html(s_cur['n'], s_prev['n']))}
            {generate_kpi("Afstand", f"{s_cur['km']:,.0f} km", label, "📏", format_diff_html(s_cur['km'], s_prev['km'], "km"))}
            {generate_kpi("Hoogtemeters", f"{s_cur['h']:,.0f} m", label, "⛰️", format_diff_html(s_cur['h'], s_prev['h'], "m"))}
        </div>"""
        
        # Koersverloop Grafiek
        df_cum = df_jaar.sort_values('DagVanJaar')[['DagVanJaar', 'Afstand_km']].copy()
        df_cum['Cum'] = df_cum['Afstand_km'].cumsum()
        df_cum_prev = df_prev_full.sort_values('DagVanJaar')[['DagVanJaar', 'Afstand_km']].copy()
        df_cum_prev['Cum'] = df_cum_prev['Afstand_km'].cumsum()
        
        fig_line = px.line(title=f"Koersverloop: {jaar} vs {prev_jaar}")
        fig_line.add_scatter(x=df_cum['DagVanJaar'], y=df_cum['Cum'], name=f"{jaar}", line_color=COLORS['neon_blue'], line_width=4)
        if not df_cum_prev.empty:
            fig_line.add_scatter(x=df_cum_prev['DagVanJaar'], y=df_cum_prev['Cum'], name=f"{prev_jaar}", line_color=COLORS['muted'], line_dash='dot')
        
        fig_line.update_layout(
            template='plotly_dark', 
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': COLORS['text']},
            margin=dict(t=40,b=20,l=20,r=20), 
            height=350
        )

        # Pie Chart
        sessies_per_sport = df_jaar['Activiteitstype'].value_counts().reset_index()
        sessies_per_sport.columns = ['Sport', 'Aantal']
        pie_colors = {row['Sport']: get_sport_style(row['Sport'])['color'] for _, row in sessies_per_sport.iterrows()}
        
        fig_pie = px.pie(sessies_per_sport, values='Aantal', names='Sport', title=f"Verdeling {jaar}", color='Sport', color_discrete_map=pie_colors, hole=0.5)
        fig_pie.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', font={'color': COLORS['text']}, height=350, showlegend=True)

        active = "active" if is_current else ""
        nav_html += f'<button class="nav-btn {active}" onclick="openTab(event, \'view-{jaar}\')">{jaar}</button>'
        disp = 'block' if is_current else 'none'
        
        sections_html += f"""
        <div id="view-{jaar}" class="tab-content" style="display: {disp};">
            <h2 class="section-title">Overzicht {jaar}</h2>
            {kpis}
            <h3 class="section-subtitle">Details per Sport</h3>
            {generate_sport_cards(df_jaar, df_prev_comp)}
            <h3 class="section-subtitle">Grafieken</h3>
            <div class="chart-grid">
                <div class="chart-box full-width">{fig_line.to_html(full_html=False, include_plotlyjs='cdn')}</div>
                <div class="chart-box">{fig_pie.to_html(full_html=False, include_plotlyjs='cdn')}</div>
            </div>
        </div>
        """

    # 2. TOTAAL TAB
    nav_html += '<button class="nav-btn" onclick="openTab(event, \'view-Total\')">Totaal</button>'
    tk_n = len(df); tk_km = df['Afstand_km'].sum(); tk_h = df['Hoogte_m'].sum()
    kpis_tot = f"""<div class="kpi-grid">
        {generate_kpi("Totaal Sessies", tk_n, "Carrière", "🏆")}
        {generate_kpi("Totaal Afstand", f"{tk_km:,.0f} km", "Carrière", "🌍")}
        {generate_kpi("Hoogtemeters", f"{tk_h:,.0f} m", f"{(tk_h/8848):.1f}x Everest", "⛰️")}
    </div>"""
    
    sections_html += f"""
    <div id="view-Total" class="tab-content" style="display: none;">
        <h2 class="section-title">Carrière Overzicht</h2>
        {kpis_tot}
        <h3 class="section-subtitle">Per Sport</h3>
        {generate_sport_cards(df, None)}
    </div>
    """

    # 3. HALL OF FAME TAB
    nav_html += '<button class="nav-btn" onclick="openTab(event, \'view-HOF\')">Hall of Fame</button>'
    sections_html += f"""
    <div id="view-HOF" class="tab-content" style="display: none;">
        <h2 class="section-title">🏆 Hall of Fame</h2>
        {generate_hall_of_fame(df)}
    </div>
    """

    # 4. DETAIL TABEL
    df_sorted = df.sort_values('Datum', ascending=False)
    sports_list = sorted(df['Activiteitstype'].unique())
    opt_html = "".join([f'<option value="{s}">{s}</option>' for s in sports_list])
    rows = ""
    for _, row in df_sorted.iterrows():
        st = get_sport_style(row['Activiteitstype'])
        hr = f"{row['Gemiddelde_Hartslag']:.0f}" if pd.notna(row['Gemiddelde_Hartslag']) else "-"
        rows += f"""<tr data-sport="{row['Activiteitstype']}">
            <td><span style="color:{st['color']}">{st['icon']}</span></td>
            <td>{row['Datum'].strftime('%d-%m-%Y')}</td>
            <td><strong style="color:{st['color']}">{row['Activiteitstype']}</strong></td>
            <td>{row['Naam']}</td>
            <td class="num">{row['Afstand_km']:.1f}</td>
            <td class="num">{format_time(row['Beweegtijd_sec'])}</td>
            <td class="num hr-blur">{hr}</td>
        </tr>"""

    detail_table = f"""
    <div class="detail-section">
        <div class="detail-header">
            <h3>📃 Sessie Logboek</h3>
            <select id="sportFilter" onchange="filterTable()">
                <option value="ALL">Alles tonen</option>
                {opt_html}
            </select>
        </div>
        <div class="table-responsive">
            <table id="detailTable">
                <thead><tr><th width="30"></th><th>Datum</th><th>Sport</th><th>Naam</th><th class="num">Km</th><th class="num">Tijd</th><th class="num">❤️</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </div>
    """

    html = f"""
    <!DOCTYPE html>
    <html lang="nl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Neon Sport Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg: {COLORS['bg']}; --card: {COLORS['card']}; 
                --text: {COLORS['text']}; --muted: {COLORS['muted']};
                --neon-blue: {COLORS['neon_blue']}; --neon-pink: {COLORS['neon_pink']};
                --primary: {COLORS['primary']};
            }}
            body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            
            /* Header */
            .top-bar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #333; padding-bottom: 20px; }}
            h1 {{ margin: 0; font-weight: 900; font-style: italic; text-transform: uppercase; font-size: 28px; letter-spacing: 1px; }}
            h1 span {{ color: var(--neon-blue); text-shadow: 0 0 10px var(--neon-blue); }}
            
            .lock-btn {{ background: transparent; border: 2px solid var(--neon-pink); color: var(--neon-pink); border-radius: 30px; padding: 8px 16px; cursor: pointer; font-weight: 600; transition: 0.3s; box-shadow: 0 0 5px var(--neon-pink); }}
            .lock-btn:hover {{ background: var(--neon-pink); color: #fff; box-shadow: 0 0 15px var(--neon-pink); }}

            /* Nav */
            .nav-bar {{ display: flex; gap: 10px; margin-bottom: 25px; overflow-x: auto; padding-bottom: 5px; }}
            .nav-btn {{ background: var(--card); border: 1px solid #333; padding: 12px 24px; border-radius: 30px; cursor: pointer; font-weight: 700; color: var(--muted); text-transform: uppercase; transition: 0.2s; white-space: nowrap; }}
            .nav-btn.active {{ background: var(--primary); color: #000; border-color: var(--primary); box-shadow: 0 0 10px var(--primary); }}
            
            /* Grids */
            .kpi-grid, .sport-grid, .chart-grid, .hof-grid {{ display: grid; gap: 20px; margin-bottom: 30px; }}
            .kpi-grid {{ grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }}
            .sport-grid {{ grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }}
            .chart-grid {{ grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); }}
            .hof-grid {{ grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}

            /* Cards */
            .kpi-card, .sport-card, .hof-card, .chart-box, .detail-section {{ background: var(--card); border-radius: 12px; padding: 20px; border: 1px solid #333; }}
            .full-width {{ grid-column: 1 / -1; }}
            
            /* Text & Icons */
            .kpi-title, .label, .hof-label {{ font-size: 11px; text-transform: uppercase; color: var(--muted); letter-spacing: 1px; }}
            .kpi-value {{ font-size: 28px; font-weight: 800; color: #fff; }}
            .val {{ font-size: 20px; font-weight: 700; color: #fff; }}
            .kpi-icon {{ font-size: 24px; margin-right: 10px; }}
            
            /* Sport Header */
            .sport-header {{ padding: 10px; margin: -20px -20px 15px -20px; border-radius: 11px 11px 0 0; display: flex; align-items: center; gap: 10px; font-weight: bold; }}
            
            /* Stats */
            .stat-main {{ display: flex; justify-content: space-between; border-bottom: 1px solid #333; padding-bottom: 15px; margin-bottom: 15px; }}
            .stat-row {{ display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px; }}
            
            /* Table */
            .detail-header {{ display: flex; justify-content: space-between; margin-bottom: 15px; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 13px; color: #eee; }}
            th {{ text-align: left; padding: 10px; background: #252525; color: var(--muted); text-transform: uppercase; font-size: 11px; }}
            td {{ padding: 10px; border-bottom: 1px solid #333; }}
            .num {{ text-align: right; font-family: 'Inter', monospace; }}
            select {{ background: #000; color: #fff; border: 1px solid #444; padding: 5px; border-radius: 4px; }}
            
            .hr-blur {{ filter: blur(6px); transition: 0.3s; }}
            .section-title {{ font-size: 18px; font-weight: 800; margin: 30px 0 15px 0; border-left: 4px solid var(--neon-blue); padding-left: 10px; color: #fff; }}
            .section-subtitle {{ font-size: 14px; color: var(--muted); margin: 20px 0 10px 0; text-transform: uppercase; letter-spacing: 1px; }}

            @media (max-width: 768px) {{ .chart-grid {{ grid-template-columns: 1fr; }} }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="top-bar">
                <h1>NEON <span>DASHBOARD</span></h1>
                <button class="lock-btn" onclick="unlockHR()">🔒 Hartslag</button>
            </div>
            <div class="nav-bar">{nav_html}</div>
            {sections_html}
            {detail_table}
        </div>
        
        <script>
            function openTab(evt, tabName) {{
                var i, tabcontent, tablinks;
                tabcontent = document.getElementsByClassName("tab-content");
                for (i = 0; i < tabcontent.length; i++) {{ tabcontent[i].style.display = "none"; }}
                tablinks = document.getElementsByClassName("nav-btn");
                for (i = 0; i < tablinks.length; i++) {{ tablinks[i].className = tablinks[i].className.replace(" active", ""); }}
                document.getElementById(tabName).style.display = "block";
                evt.currentTarget.className += " active";
            }}
            function filterTable() {{
                var input = document.getElementById("sportFilter").value;
                var tr = document.getElementById("detailTable").getElementsByTagName("tr");
                for (i = 1; i < tr.length; i++) {{
                    var sport = tr[i].getAttribute('data-sport');
                    if (input === "ALL" || sport === input) {{ tr[i].style.display = ""; }} 
                    else {{ tr[i].style.display = "none"; }}
                }}
            }}
            function unlockHR() {{
                var pass = prompt("Wachtwoord (Tip: Niet Gust):");
                if(pass === "Nala") {{
                    document.querySelectorAll('.hr-blur').forEach(e => e.style.filter = 'none');
                    document.querySelector('.lock-btn').style.display = 'none';
                    alert("🔓 Hartslag ontgrendeld!");
                }} else if(pass !== null) {{ alert("❌ Fout!"); }}
            }}
        </script>
    </body>
    </html>
    """
    
    with open(html_output, 'w', encoding='utf-8') as f:
        f.write(html)
    print("✅ Neon Dashboard gereed!")

if __name__ == "__main__":
    genereer_dashboard()
