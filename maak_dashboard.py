import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime

# --- CONFIGURATIE & KLEUREN (Modern Palet) ---
# Een modern, sportief palet (Donkerblauw, Levendig Oranje, Fris Groen)
COLORS = {
    'primary': '#007AFF',      # Helder Blauw (Apple style)
    'secondary': '#5856D6',    # Paars/Blauw accent
    'accent_warn': '#FF9500',  # Oranje (Strava-achtig)
    'accent_bad': '#FF3B30',   # Rood
    'accent_good': '#34C759',  # Groen
    'bg': '#F2F2F7',           # Lichte grijze achtergrond
    'card': '#FFFFFF',         # Wit voor kaarten
    'text': '#1C1C1E',         # Bijna zwart
    'text_muted': '#8E8E93'    # Grijs voor subtekst
}

PLOTLY_TEMPLATE = 'plotly_white'
EVEREST_HEIGHT_M = 8848

# Sport Specifieke Iconen & Kleuren voor Grafieken
SPORT_CONFIG = {
    'Fiets': {'icon': '🚴', 'color': '#007AFF'},        # Blauw
    'Virtuele fietsrit': {'icon': '👾', 'color': '#5856D6'}, # Paars
    'Hardloop': {'icon': '🏃', 'color': '#FF9500'},     # Oranje
    'Wandel': {'icon': '🚶', 'color': '#34C759'},       # Groen
    'Hike': {'icon': '🥾', 'color': '#30B0C7'},         # Teal
    'Zwemmen': {'icon': '🏊', 'color': '#5AC8FA'},      # Lichtblauw
    'Training': {'icon': '🏋️', 'color': '#FF2D55'},     # Roze/Rood
    'Workout': {'icon': '💪', 'color': '#FF2D55'},
    'Default': {'icon': '🏅', 'color': '#8E8E93'}
}

def get_sport_color(sport_name):
    for key, config in SPORT_CONFIG.items():
        if key in sport_name:
            return config['color']
    return SPORT_CONFIG['Default']['color']

def get_sport_icon(sport_name):
    for key, config in SPORT_CONFIG.items():
        if key in sport_name:
            return config['icon']
    return SPORT_CONFIG['Default']['icon']

# --- HULPFUNCTIES ---

def format_time(seconds):
    if pd.isna(seconds) or seconds <= 0: return '-'
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f'{hours}u {minutes:02d}m'

def robust_date_parser(date_series):
    # Mapping voor NL maanden
    dutch_month_mapping = {
        'jan': 'Jan', 'feb': 'Feb', 'mrt': 'Mar', 'apr': 'Apr', 
        'mei': 'May', 'jun': 'Jun', 'jul': 'Jul', 'aug': 'Aug', 
        'sep': 'Sep', 'okt': 'Oct', 'nov': 'Nov', 'dec': 'Dec'
    }
    date_series_str = date_series.astype(str).str.lower()
    for dutch, eng in dutch_month_mapping.items():
        date_series_str = date_series_str.str.replace(dutch, eng, regex=False)
        
    dates = pd.to_datetime(date_series_str, format='%d %b %Y, %H:%M:%S', errors='coerce')
    # Fallback
    mask = dates.isna()
    if mask.any():
        dates[mask] = pd.to_datetime(date_series_str[mask], errors='coerce', dayfirst=True)
    return dates

def format_diff(current, previous, unit="", reverse_good=False):
    """Genereert HTML voor het verschil (bijv: +10 km)."""
    if pd.isna(previous) or previous == 0:
        return '<span class="diff-neutral">Nieuw</span>'
    
    diff = current - previous
    if diff == 0:
        return '<span class="diff-neutral">-</span>'
    
    # Bepaal kleur (normaal: meer is groen. reverse_good=True: minder is groen, bijv. tijd)
    is_positive = diff > 0
    if reverse_good:
        is_good = not is_positive
    else:
        is_good = is_positive
        
    color_class = "diff-pos" if is_good else "diff-neg"
    arrow = "▲" if is_positive else "▼"
    
    # Format getal
    if isinstance(diff, float):
        val_str = f"{abs(diff):.1f}"
    else:
        val_str = f"{abs(int(diff))}"
        
    return f'<span class="{color_class}">{arrow} {val_str} {unit}</span>'

# --- HTML GENERATORS ---

def generate_kpi_card(title, value, subtext="", icon="", diff_html=""):
    """Genereert een moderne KPI kaart."""
    return f"""
    <div class="kpi-card">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-content">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{diff_html} {subtext}</div>
        </div>
    </div>
    """

def generate_detail_table(df):
    if df.empty: return "<p>Geen data.</p>"
    
    # Sorteer datum aflopend (nieuwste boven)
    df = df.sort_values(by='Datum', ascending=False)
    
    rows = []
    for _, row in df.iterrows():
        icon = get_sport_icon(row['Activiteitstype'])
        date_str = row['Datum'].strftime('%d %b')
        rows.append(f"""
        <tr>
            <td><span class="table-icon">{icon}</span></td>
            <td><strong>{row['Activiteitstype']}</strong><br><span class="table-date">{date_str}</span></td>
            <td>{row['Naam_Activiteit']}</td>
            <td class="num">{row['Afstand_km']:.1f} km</td>
            <td class="num">{format_time(row['Beweegtijd_sec'])}</td>
            <td class="num col-hide">{row['Gemiddelde_Snelheid_km_u']:.1f} km/u</td>
            <td class="num hr-hidden col-hide">{row['Gemiddelde_Hartslag']:.0f}</td>
        </tr>
        """)
        
    return f"""
    <div class="table-wrapper">
        <table class="modern-table">
            <thead>
                <tr>
                    <th style="width: 40px;"></th>
                    <th>Type</th>
                    <th>Naam</th>
                    <th class="num">Afstand</th>
                    <th class="num">Tijd</th>
                    <th class="num col-hide">Snelheid</th>
                    <th class="num col-hide">Hartslag</th>
                </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    </div>
    """

def genereer_html_dashboard(csv_input='activities.csv', html_output='dashboard.html'):
    print("🚀 Start dashboard generatie...")
    
    # 1. DATA LADEN & CLEANEN
    try:
        df = pd.read_csv(csv_input)
    except FileNotFoundError:
        print("❌ CSV niet gevonden.")
        return

    # Basis cleaning
    if 'Gemiddelde snelheid' in df.columns: df['Gemiddelde snelheid'] *= 3.6
    
    # Kolom mapping
    df = df.rename(columns={
        'Datum van activiteit': 'Datum',
        'Naam activiteit': 'Naam_Activiteit',
        'Activiteitstype': 'Activiteitstype',
        'Beweegtijd': 'Beweegtijd_sec',
        'Afstand': 'Afstand_km',
        'Totale stijging': 'Totale_Stijging_m',
        'Gemiddelde hartslag': 'Gemiddelde_Hartslag',
        'Gemiddelde snelheid': 'Gemiddelde_Snelheid_km_u',
        'Calorieën': 'Calorieen'
    })

    # Numerieke conversie
    cols_to_numeric = ['Afstand_km', 'Totale_Stijging_m', 'Gemiddelde_Snelheid_km_u', 'Gemiddelde_Hartslag', 'Calorieen']
    for col in cols_to_numeric:
        if col in df.columns and df[col].dtype == object:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    # Datum parsing
    df['Datum'] = robust_date_parser(df['Datum'])
    df['Jaar'] = df['Datum'].dt.year
    df['Maand'] = df['Datum'].dt.month
    df['Maand_Naam'] = df['Datum'].dt.strftime('%b') # Jan, Feb etc.
    
    # Alleen relevante rows
    df = df.dropna(subset=['Datum'])
    df['Totale_Stijging_m'] = df['Totale_Stijging_m'].fillna(0)
    
    # Zwemmen fix (m naar km)
    mask_swim = df['Activiteitstype'].str.contains('Zwemmen', na=False, case=False)
    df.loc[mask_swim, 'Afstand_km'] = df.loc[mask_swim, 'Afstand_km'] / 1000

    # 2. ANALYSE PER JAAR VOOR YoY
    jaren = sorted(df['Jaar'].unique(), reverse=True)
    jaar_stats = {}
    
    for jaar in jaren:
        d_jaar = df[df['Jaar'] == jaar]
        jaar_stats[jaar] = {
            'sessies': len(d_jaar),
            'afstand': d_jaar['Afstand_km'].sum(),
            'tijd': d_jaar['Beweegtijd_sec'].sum(),
            'stijging': d_jaar['Totale_Stijging_m'].sum(),
            'data': d_jaar
        }

    # 3. HTML OPBOUW
    
    # Huidig jaar bepalen voor auto-open
    current_year_sys = datetime.now().year
    # Als huidig jaar nog geen data heeft, pak het laatste jaar met data
    if current_year_sys not in jaren:
        current_year_sys = jaren[0]

    # Navigatie Knoppen
    nav_html = ""
    for jaar in jaren:
        active_class = "active" if jaar == current_year_sys else ""
        nav_html += f'<button class="nav-btn {active_class}" onclick="openTab(event, \'view-{jaar}\')">{jaar}</button>'
    nav_html += '<button class="nav-btn" onclick="openTab(event, \'view-Globaal\')">Totaal</button>'

    # Content Secties
    sections_html = ""
    
    # --- JAAR SECTIES ---
    for jaar in jaren:
        stats = jaar_stats[jaar]
        prev_year = jaar - 1
        
        # YoY Berekeningen
        diff_sessies = ""
        diff_afstand = ""
        
        if prev_year in jaar_stats:
            prev_stats = jaar_stats[prev_year]
            diff_sessies = format_diff(stats['sessies'], prev_stats['sessies'], "")
            diff_afstand = format_diff(stats['afstand'], prev_stats['afstand'], "km")
        else:
            diff_sessies = "<span class='diff-neutral'>Start</span>"
            diff_afstand = "<span class='diff-neutral'>-</span>"

        # KPI Kaarten
        kpis = f"""
        <div class="kpi-grid">
            {generate_kpi_card("Sessies", stats['sessies'], "t.o.v. vorig jaar", "🔥", diff_sessies)}
            {generate_kpi_card("Afstand", f"{stats['afstand']:,.1f} km", "t.o.v. vorig jaar", "📏", diff_afstand)}
            {generate_kpi_card("Tijd", format_time(stats['tijd']), "in beweging", "⏱️")}
            {generate_kpi_card("Hoogtemeters", f"{stats['stijging']:,.0f} m", f"{(stats['stijging']/EVEREST_HEIGHT_M):.1f}x Everest", "⛰️")}
        </div>
        """
        
        # GRAFIEKEN (Plotly)
        df_jaar = stats['data'].copy()
        
        # 1. Afstand per Maand (Stacked Bar)
        df_maand = df_jaar.groupby(['Maand', 'Maand_Naam', 'Activiteitstype'])['Afstand_km'].sum().reset_index()
        
        # Zorg voor juiste maandvolgorde
        df_maand = df_maand.sort_values('Maand')
        
        # Kleuren toewijzen
        color_map = {sport: get_sport_color(sport) for sport in df_maand['Activiteitstype'].unique()}
        
        fig_bar = px.bar(df_maand, x='Maand_Naam', y='Afstand_km', color='Activiteitstype',
                         title=f"Afstand per Maand ({jaar})",
                         color_discrete_map=color_map,
                         template=PLOTLY_TEMPLATE)
        fig_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font={'family': 'Inter, sans-serif', 'color': '#1C1C1E'},
            legend=dict(orientation="h", y=1.1, x=0),
            margin=dict(l=20, r=20, t=60, b=20)
        )
        
        # 2. Cumulatieve Lijn (Huidig vs Vorig jaar) - OPTIONEEL MAAR GAAF
        # We maken een simpele scatterplot van sessies over tijd
        fig_scatter = px.scatter(df_jaar, x='Datum', y='Afstand_km', color='Activiteitstype',
                                size='Afstand_km', hover_data=['Naam_Activiteit'],
                                title=f"Alle Activiteiten Tijdlijn ({jaar})",
                                color_discrete_map=color_map,
                                template=PLOTLY_TEMPLATE)
        fig_scatter.update_layout(
             paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
             font={'family': 'Inter, sans-serif', 'color': '#1C1C1E'},
             legend=dict(orientation="h", y=1.1, x=0),
             margin=dict(l=20, r=20, t=60, b=20)
        )

        # HTML Tabel
        tabel_html = generate_detail_table(df_jaar)

        display_style = 'block' if jaar == current_year_sys else 'none'
        
        sections_html += f"""
        <div id="view-{jaar}" class="tab-content" style="display: {display_style};">
            <h2 class="section-title">Overzicht {jaar}</h2>
            {kpis}
            
            <div class="charts-grid">
                <div class="chart-card">{fig_bar.to_html(full_html=False, include_plotlyjs='cdn')}</div>
                <div class="chart-card">{fig_scatter.to_html(full_html=False, include_plotlyjs='cdn')}</div>
            </div>
            
            <h3 class="section-subtitle">Activiteiten Logboek</h3>
            {tabel_html}
        </div>
        """

    # --- TOTAAL SECTIE (GLOBAAL) ---
    # Totaal grafieken
    agg_jaar = df.groupby(['Jaar', 'Activiteitstype'])['Afstand_km'].sum().reset_index()
    color_map_global = {sport: get_sport_color(sport) for sport in agg_jaar['Activiteitstype'].unique()}
    
    fig_global = px.bar(agg_jaar, x='Jaar', y='Afstand_km', color='Activiteitstype',
                        title="Totale Afstand per Jaar",
                        color_discrete_map=color_map_global,
                        template=PLOTLY_TEMPLATE)
    fig_global.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", y=1.1),
        xaxis={'type': 'category'} # Zorgt dat jaren heel blijven
    )

    sections_html += f"""
    <div id="view-Globaal" class="tab-content" style="display: none;">
        <h2 class="section-title">Carrière Totaal</h2>
        <div class="kpi-grid">
            {generate_kpi_card("Totaal Sessies", len(df), "", "🏆")}
            {generate_kpi_card("Totaal Afstand", f"{df['Afstand_km'].sum():,.0f} km", "", "🌍")}
        </div>
        <div class="chart-card full-width">
            {fig_global.to_html(full_html=False, include_plotlyjs='cdn')}
        </div>
        {generate_detail_table(df)}
    </div>
    """

    # 4. FINAL HTML ASSEMBLAGE
    html_content = f"""
    <!DOCTYPE html>
    <html lang="nl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sport Dashboard {current_year_sys}</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-color: #F2F2F7;
                --card-bg: #FFFFFF;
                --text-main: #1C1C1E;
                --text-muted: #8E8E93;
                --accent: #007AFF;
                --success: #34C759;
                --danger: #FF3B30;
                --shadow: 0 4px 12px rgba(0,0,0,0.08);
            }}
            
            body {{
                font-family: 'Inter', -apple-system, sans-serif;
                background-color: var(--bg-color);
                color: var(--text-main);
                margin: 0;
                padding: 20px;
                -webkit-font-smoothing: antialiased;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            
            header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
            }}
            
            h1 {{ margin: 0; font-weight: 800; font-size: 28px; }}
            
            /* Navigatie */
            .nav-container {{
                display: flex;
                gap: 10px;
                overflow-x: auto;
                padding-bottom: 10px;
            }}
            
            .nav-btn {{
                background: var(--card-bg);
                border: none;
                padding: 10px 20px;
                border-radius: 20px;
                font-weight: 600;
                color: var(--text-muted);
                cursor: pointer;
                transition: all 0.2s;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }}
            
            .nav-btn.active {{
                background: var(--accent);
                color: white;
                box-shadow: 0 4px 10px rgba(0,122,255,0.3);
            }}
            
            /* KPI Kaarten */
            .kpi-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .kpi-card {{
                background: var(--card-bg);
                padding: 20px;
                border-radius: 16px;
                box-shadow: var(--shadow);
                display: flex;
                align-items: center;
                gap: 15px;
            }}
            
            .kpi-icon {{ font-size: 32px; }}
            .kpi-title {{ font-size: 14px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }}
            .kpi-value {{ font-size: 28px; font-weight: 800; margin: 5px 0; }}
            .kpi-sub {{ font-size: 13px; color: var(--text-muted); display: flex; align-items: center; gap: 5px; }}
            
            .diff-pos {{ color: var(--success); font-weight: 600; background: rgba(52, 199, 89, 0.1); padding: 2px 6px; border-radius: 6px; }}
            .diff-neg {{ color: var(--danger); font-weight: 600; background: rgba(255, 59, 48, 0.1); padding: 2px 6px; border-radius: 6px; }}
            
            /* Grafieken */
            .charts-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .chart-card {{
                background: var(--card-bg);
                padding: 20px;
                border-radius: 16px;
                box-shadow: var(--shadow);
                min-height: 400px;
            }}
            
            .full-width {{ grid-column: 1 / -1; }}
            
            /* Tabel */
            .table-wrapper {{
                background: var(--card-bg);
                border-radius: 16px;
                box-shadow: var(--shadow);
                overflow: hidden;
                overflow-x: auto;
            }}
            
            .modern-table {{
                width: 100%;
                border-collapse: collapse;
                min-width: 600px;
            }}
            
            .modern-table th {{
                text-align: left;
                padding: 15px 20px;
                background: #F9F9F9;
                color: var(--text-muted);
                font-weight: 600;
                font-size: 13px;
                text-transform: uppercase;
            }}
            
            .modern-table td {{
                padding: 15px 20px;
                border-bottom: 1px solid #EEE;
                font-size: 14px;
            }}
            
            .modern-table tr:last-child td {{ border-bottom: none; }}
            
            .table-icon {{ font-size: 20px; }}
            .table-date {{ font-size: 12px; color: var(--text-muted); }}
            
            .num {{ text-align: right; font-family: 'Inter', monospace; }}
            
            /* Utilities */
            .hr-hidden {{ filter: blur(5px); transition: 0.3s; cursor: pointer; }}
            .hr-hidden:hover {{ filter: none; }}
            
            @media (max-width: 768px) {{
                .charts-grid {{ grid-template-columns: 1fr; }}
                .col-hide {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Sport Dashboard</h1>
                <div style="font-size: 24px;">🏃🚴💨</div>
            </header>
            
            <nav class="nav-container">
                {nav_html}
            </nav>
            
            <main>
                {sections_html}
            </main>
            
            <footer style="text-align: center; margin-top: 40px; color: var(--text-muted); font-size: 12px;">
                Generated on {datetime.now().strftime('%d %b %Y %H:%M')}
            </footer>
        </div>

        <script>
            function openTab(evt, tabName) {{
                var i, tabcontent, tablinks;
                
                // Verberg alle content
                tabcontent = document.getElementsByClassName("tab-content");
                for (i = 0; i < tabcontent.length; i++) {{
                    tabcontent[i].style.display = "none";
                }}
                
                // Verwijder active class van knoppen
                tablinks = document.getElementsByClassName("nav-btn");
                for (i = 0; i < tablinks.length; i++) {{
                    tablinks[i].className = tablinks[i].className.replace(" active", "");
                }}
                
                // Toon geselecteerde
                document.getElementById(tabName).style.display = "block";
                evt.currentTarget.className += " active";
            }}
            
            // Hartslag unlock (simpel click-to-reveal)
            document.querySelectorAll('.hr-hidden').forEach(item => {{
                item.addEventListener('click', event => {{
                    item.classList.remove('hr-hidden');
                }})
            }});
        </script>
    </body>
    </html>
    """
    
    with open(html_output, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Dashboard klaar! ({html_output})")

if __name__ == "__main__":
    genereer_html_dashboard()
