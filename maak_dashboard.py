import pandas as pd
import numpy as np
import plotly.express as px
import plotly.io as pio
from datetime import datetime

# --- CONFIGURATIE & KLEUREN ---
# Modern kleurenpalet
COLORS = {
    'primary': '#007AFF',      # Apple Blue
    'secondary': '#5856D6',    # Purple
    'success': '#34C759',      # Green
    'warning': '#FF9500',      # Orange
    'danger': '#FF3B30',       # Red
    'bg': '#F2F2F7',           # Light Gray Background
    'card': '#FFFFFF',         # White
    'text': '#1C1C1E',         # Dark Text
    'text_muted': '#8E8E93'    # Grey Text
}

# Iconen en kleuren per sport
SPORT_CONFIG = {
    'Fiets': {'icon': '🚴', 'color': '#007AFF'},
    'Virtuele fietsrit': {'icon': '👾', 'color': '#5856D6'},
    'Hardloop': {'icon': '🏃', 'color': '#FF9500'},
    'Wandel': {'icon': '🚶', 'color': '#34C759'},
    'Hike': {'icon': '🥾', 'color': '#30B0C7'},
    'Zwemmen': {'icon': '🏊', 'color': '#5AC8FA'},
    'Training': {'icon': '🏋️', 'color': '#FF2D55'},
    'Workout': {'icon': '💪', 'color': '#FF2D55'},
    'Default': {'icon': '🏅', 'color': '#8E8E93'}
}

# Hoogte Everest
EVEREST_HEIGHT_M = 8848

# --- HULPFUNCTIES ---

def get_sport_style(sport_name):
    """Haalt kleur en icoon op voor een sport (met partial matching)."""
    for key, config in SPORT_CONFIG.items():
        if key.lower() in str(sport_name).lower():
            return config
    return SPORT_CONFIG['Default']

def format_time(seconds):
    """Van seconden naar 10u 30m formaat"""
    if pd.isna(seconds) or seconds <= 0: return '-'
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f'{hours}u {minutes:02d}m'

def format_pace(speed_kmh):
    """Zet km/u om naar min/km (voor hardlopen)"""
    if pd.isna(speed_kmh) or speed_kmh <= 0: return '-'
    seconds_per_km = 3600 / speed_kmh
    minutes = int(seconds_per_km // 60)
    seconds = int(seconds_per_km % 60)
    return f"{minutes}:{seconds:02d} /km"

def robust_date_parser(date_series):
    """Parses NL datums zoals '4 jan 2026'."""
    dutch_month_mapping = {
        'jan': 'Jan', 'feb': 'Feb', 'mrt': 'Mar', 'apr': 'Apr', 
        'mei': 'May', 'jun': 'Jun', 'jul': 'Jul', 'aug': 'Aug', 
        'sep': 'Sep', 'okt': 'Oct', 'nov': 'Nov', 'dec': 'Dec'
    }
    date_series_str = date_series.astype(str).str.lower()
    for dutch, eng in dutch_month_mapping.items():
        date_series_str = date_series_str.str.replace(dutch, eng, regex=False)
        
    dates = pd.to_datetime(date_series_str, format='%d %b %Y, %H:%M:%S', errors='coerce')
    # Fallback voor andere formaten
    mask = dates.isna()
    if mask.any():
        dates[mask] = pd.to_datetime(date_series_str[mask], errors='coerce', dayfirst=True)
    return dates

def format_diff_html(current, previous, unit="", inverse=False):
    """
    Maakt HTML voor verschil (bijv. +10 km). 
    Houdt rekening met 'Point-in-Time' logica.
    """
    if pd.isna(previous) or previous == 0:
        return '<span class="diff-neutral">Start</span>'
    
    diff = current - previous
    if diff == 0: return '<span class="diff-neutral">-</span>'
    
    # Kleur bepalen (Meer is goed, tenzij 'inverse' waar is (bijv tijd per km))
    is_good = (diff > 0) if not inverse else (diff < 0)
    color_class = "diff-pos" if is_good else "diff-neg"
    arrow = "▲" if diff > 0 else "▼"
    
    val_str = f"{abs(diff):.1f}" if isinstance(diff, float) else f"{abs(int(diff))}"
    
    return f'<span class="{color_class}">{arrow} {val_str} {unit}</span>'

# --- HTML GENERATORS ---

def generate_kpi_card(title, value, subtext="", icon="", diff_html=""):
    return f"""
    <div class="kpi-card">
        <div class="kpi-icon-box">{icon}</div>
        <div class="kpi-content">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{diff_html} {subtext}</div>
        </div>
    </div>
    """

def generate_sport_details(df_year):
    """Genereert gedetailleerde kaarten per sport."""
    html = '<div class="sport-grid">'
    
    # Groepeer per sport
    sports = df_year['Activiteitstype'].unique()
    
    for sport in sorted(sports):
        df_sport = df_year[df_year['Activiteitstype'] == sport]
        style = get_sport_style(sport)
        
        # Stats berekenen
        count = len(df_sport)
        dist = df_sport['Afstand_km'].sum()
        time = df_sport['Beweegtijd_sec'].sum()
        avg_hr = df_sport['Gemiddelde_Hartslag'].mean()
        
        # Max stats
        max_dist = df_sport['Afstand_km'].max()
        max_speed = df_sport['Max_Snelheid_km_u'].max()
        fastest_pace = df_sport['Gemiddelde_Snelheid_km_u'].max()
        
        # Formatteren
        dist_str = f"{dist:,.1f} km"
        time_str = format_time(time)
        hr_str = f"{avg_hr:.0f} bpm" if pd.notna(avg_hr) else "-"
        
        # Specifieke regels per type
        details_html = ""
        
        # Regel 1: Langste sessie
        if max_dist > 0:
            details_html += f'<div class="stat-row"><span>Langste:</span> <strong>{max_dist:.1f} km</strong></div>'
            
        # Regel 2: Snelheid (Loop vs Fiets)
        if 'Hardloop' in sport:
             if fastest_pace > 0:
                details_html += f'<div class="stat-row"><span>Snelste tempo:</span> <strong>{format_pace(fastest_pace)}</strong></div>'
        elif 'Fiets' in sport:
             if max_speed > 0:
                details_html += f'<div class="stat-row"><span>Max snelheid:</span> <strong>{max_speed:.1f} km/u</strong></div>'
        
        # Regel 3: Hartslag
        if pd.notna(avg_hr) and avg_hr > 0:
             details_html += f'<div class="stat-row"><span>Gem. Hartslag:</span> <strong class="hr-blur">{hr_str}</strong></div>'
             
        html += f"""
        <div class="sport-card" style="border-top: 4px solid {style['color']}">
            <div class="sport-header">
                <span class="sport-icon">{style['icon']}</span>
                <h3>{sport}</h3>
            </div>
            <div class="sport-main-stats">
                <div class="main-stat">
                    <div class="label">Sessies</div>
                    <div class="value">{count}</div>
                </div>
                <div class="main-stat">
                    <div class="label">Afstand</div>
                    <div class="value">{dist_str}</div>
                </div>
                <div class="main-stat">
                    <div class="label">Tijd</div>
                    <div class="value">{time_str}</div>
                </div>
            </div>
            <div class="sport-details">
                {details_html}
            </div>
        </div>
        """
        
    html += '</div>'
    return html

def genereer_dashboard(csv_input='activities.csv', html_output='dashboard.html'):
    print("🚀 Start generatie met Point-in-Time logica...")
    
    # 1. Data Laden
    try:
        df = pd.read_csv(csv_input)
    except:
        print("❌ Geen CSV gevonden!")
        return

    # Data Cleaning
    cols_rename = {
        'Datum van activiteit': 'Datum', 'Naam activiteit': 'Naam', 
        'Activiteitstype': 'Activiteitstype', 'Beweegtijd': 'Beweegtijd_sec',
        'Afstand': 'Afstand_km', 'Totale stijging': 'Hoogte_m',
        'Gemiddelde hartslag': 'Gemiddelde_Hartslag',
        'Gemiddelde snelheid': 'Gemiddelde_Snelheid_km_u',
        'Max. snelheid': 'Max_Snelheid_km_u'
    }
    df = df.rename(columns=cols_rename)
    
    # Numeriek maken
    numeric_cols = ['Afstand_km', 'Hoogte_m', 'Gemiddelde_Snelheid_km_u', 'Max_Snelheid_km_u', 'Gemiddelde_Hartslag']
    for c in numeric_cols:
        if c in df.columns and df[c].dtype == object:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce')

    # Zwemmen correctie (meters naar km)
    mask_swim = df['Activiteitstype'].str.contains('Zwemmen', na=False, case=False)
    df.loc[mask_swim, 'Afstand_km'] = df.loc[mask_swim, 'Afstand_km'] / 1000
    
    # Snelheid correctie (m/s naar km/u) - Strava export is soms m/s
    # We checken even of de gemiddelde snelheid verdacht laag is (< 10 voor fietsen bijv)
    if df['Gemiddelde_Snelheid_km_u'].mean() < 7: # Ruwe gok: m/s values zijn klein
         df['Gemiddelde_Snelheid_km_u'] *= 3.6
         if 'Max_Snelheid_km_u' in df.columns: df['Max_Snelheid_km_u'] *= 3.6

    # Datum parsing
    df['Datum'] = robust_date_parser(df['Datum'])
    df['Jaar'] = df['Datum'].dt.year
    df['Maand'] = df['Datum'].dt.month
    df['DagVanJaar'] = df['Datum'].dt.dayofyear
    
    # Huidige status bepalen
    nu = datetime.now()
    huidig_jaar = nu.year
    # Als er nog geen data is van 2026 in de CSV, pakken we de laatste datum in de CSV als 'nu'
    max_datum_csv = df['Datum'].max()
    
    if max_datum_csv.year == huidig_jaar:
        huidige_dag_van_jaar = max_datum_csv.dayofyear
    else:
        # Als we in 2026 leven maar de data stopt in 2025, is de vergelijking irrelevant
        huidige_dag_van_jaar = 366 

    # 2. HTML Opbouw
    nav_html = ""
    sections_html = ""
    
    jaren = sorted(df['Jaar'].unique(), reverse=True)
    
    for jaar in jaren:
        df_jaar = df[df['Jaar'] == jaar]
        prev_jaar = jaar - 1
        
        # --- LOGICA VOOR VERGELIJKING ---
        # Als dit het huidige jaar is, vergelijk YTD (Year To Date)
        # Anders vergelijk je het volledige jaar met het volledige vorige jaar
        
        is_current_year = (jaar == max_datum_csv.year)
        vergelijk_label = "t.o.v. zelfde moment vorig jaar" if is_current_year else "t.o.v. vorig jaar"
        
        # Stats Huidig
        stats_cur = {
            'sessies': len(df_jaar),
            'afstand': df_jaar['Afstand_km'].sum(),
            'tijd': df_jaar['Beweegtijd_sec'].sum(),
            'hoogte': df_jaar['Hoogte_m'].sum()
        }
        
        # Stats Vorig Jaar (De "Ghost" data)
        df_prev = df[df['Jaar'] == prev_jaar]
        
        if is_current_year:
            # FILTER: Pak alleen data van vorig jaar tot dezelfde dagnummer
            df_prev_comp = df_prev[df_prev['DagVanJaar'] <= huidige_dag_van_jaar]
        else:
            df_prev_comp = df_prev # Volledig jaar
            
        stats_prev = {
            'sessies': len(df_prev_comp),
            'afstand': df_prev_comp['Afstand_km'].sum(),
            'tijd': df_prev_comp['Beweegtijd_sec'].sum(),
            'hoogte': df_prev_comp['Hoogte_m'].sum()
        }
        
        # Diff Strings maken
        diff_sessies = format_diff_html(stats_cur['sessies'], stats_prev['sessies'])
        diff_afstand = format_diff_html(stats_cur['afstand'], stats_prev['afstand'], "km")
        diff_hoogte = format_diff_html(stats_cur['hoogte'], stats_prev['hoogte'], "m")

        # KPI Kaarten
        kpis = f"""
        <div class="kpi-grid">
            {generate_kpi_card("Sessies", stats_cur['sessies'], vergelijk_label, "🔥", diff_sessies)}
            {generate_kpi_card("Afstand", f"{stats_cur['afstand']:,.1f} km", vergelijk_label, "📏", diff_afstand)}
            {generate_kpi_card("Tijd", format_time(stats_cur['tijd']), "in beweging", "⏱️")}
            {generate_kpi_card("Hoogtemeters", f"{stats_cur['hoogte']:,.0f} m", vergelijk_label, "⛰️", diff_hoogte)}
        </div>
        """
        
        # Gedetailleerde Sport Kaarten
        sport_cards = generate_sport_details(df_jaar)
        
        # Grafieken
        # 1. Cumulatieve Afstand (Comparison Line)
        # We maken een dataset met cumulatieve som per dag van het jaar
        df_cum = df_jaar.sort_values('DagVanJaar')[['DagVanJaar', 'Afstand_km']].copy()
        df_cum['Cum_Afstand'] = df_cum['Afstand_km'].cumsum()
        
        # Vorig jaar ook cumulatief
        df_cum_prev = df_prev.sort_values('DagVanJaar')[['DagVanJaar', 'Afstand_km']].copy()
        df_cum_prev['Cum_Afstand'] = df_cum_prev['Afstand_km'].cumsum()
        
        fig = px.line(title=f"Koersverloop: {jaar} vs {prev_jaar}")
        fig.add_scatter(x=df_cum['DagVanJaar'], y=df_cum['Cum_Afstand'], name=f"{jaar}", line_color=COLORS['primary'], line_width=3)
        if not df_cum_prev.empty:
            fig.add_scatter(x=df_cum_prev['DagVanJaar'], y=df_cum_prev['Cum_Afstand'], name=f"{prev_jaar}", line_color=COLORS['text_muted'], line_dash='dot')
            
        fig.update_layout(template='plotly_white', xaxis_title="Dag van het Jaar", yaxis_title="Totaal km", margin=dict(t=50,b=20,l=20,r=20))
        
        # Navigatie Button
        active_cls = "active" if is_current_year else ""
        nav_html += f'<button class="nav-btn {active_cls}" onclick="openTab(event, \'view-{jaar}\')">{jaar}</button>'
        
        # Sectie samenstellen
        display_style = 'block' if is_current_year else 'none'
        
        sections_html += f"""
        <div id="view-{jaar}" class="tab-content" style="display: {display_style};">
            <h2 class="section-title">Overzicht {jaar}</h2>
            {kpis}
            
            <h3 class="section-subtitle">Details per Sport</h3>
            {sport_cards}
            
            <h3 class="section-subtitle">Grafieken</h3>
            <div class="chart-container">{fig.to_html(full_html=False, include_plotlyjs='cdn')}</div>
        </div>
        """

    # 3. HTML Template
    html = f"""
    <!DOCTYPE html>
    <html lang="nl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sport Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            :root {{
                --primary: {COLORS['primary']};
                --bg: {COLORS['bg']};
                --card: {COLORS['card']};
                --text: {COLORS['text']};
                --muted: {COLORS['text_muted']};
            }}
            body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }}
            .container {{ max-width: 1100px; margin: 0 auto; }}
            
            /* Navigatie */
            .nav-bar {{ display: flex; gap: 10px; margin-bottom: 20px; overflow-x: auto; padding-bottom: 5px; }}
            .nav-btn {{ background: var(--card); border: none; padding: 10px 20px; border-radius: 20px; cursor: pointer; font-weight: 600; color: var(--muted); transition: 0.2s; }}
            .nav-btn.active {{ background: var(--primary); color: white; box-shadow: 0 4px 10px rgba(0,122,255,0.3); }}
            
            /* KPI Grid */
            .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 30px; }}
            .kpi-card {{ background: var(--card); padding: 20px; border-radius: 16px; display: flex; align-items: center; gap: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }}
            .kpi-icon-box {{ font-size: 28px; width: 50px; height: 50px; background: #F2F8FF; display: flex; align-items: center; justify-content: center; border-radius: 12px; }}
            .kpi-title {{ font-size: 13px; color: var(--muted); text-transform: uppercase; font-weight: 600; }}
            .kpi-value {{ font-size: 24px; font-weight: 800; margin: 2px 0; }}
            .kpi-sub {{ font-size: 12px; color: var(--muted); display: flex; align-items: center; gap: 6px; }}
            
            /* Diff Styles */
            .diff-pos {{ color: #34C759; background: rgba(52, 199, 89, 0.1); padding: 2px 6px; border-radius: 4px; font-weight: 600; }}
            .diff-neg {{ color: #FF3B30; background: rgba(255, 59, 48, 0.1); padding: 2px 6px; border-radius: 4px; font-weight: 600; }}
            .diff-neutral {{ color: var(--muted); }}
            
            /* Sport Grid */
            .sport-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }}
            .sport-card {{ background: var(--card); border-radius: 16px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }}
            .sport-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 15px; }}
            .sport-icon {{ font-size: 24px; }}
            .sport-header h3 {{ margin: 0; font-size: 18px; }}
            
            .sport-main-stats {{ display: flex; justify-content: space-between; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #eee; }}
            .main-stat .label {{ font-size: 11px; color: var(--muted); text-transform: uppercase; }}
            .main-stat .value {{ font-size: 16px; font-weight: 700; }}
            
            .stat-row {{ display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 8px; color: var(--text); }}
            .hr-blur {{ filter: blur(4px); transition: 0.3s; cursor: pointer; }}
            .hr-blur:hover {{ filter: none; }}
            
            .chart-container {{ background: var(--card); padding: 15px; border-radius: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }}
            
            h2, h3 {{ color: var(--text); }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Sport Dashboard</h1>
            
            <div class="nav-bar">
                {nav_html}
            </div>
            
            {sections_html}
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
        </script>
    </body>
    </html>
    """
    
    with open(html_output, 'w', encoding='utf-8') as f:
        f.write(html)
    print("✅ Dashboard gereed!")

if __name__ == "__main__":
    genereer_dashboard()
