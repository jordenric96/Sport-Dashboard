import pandas as pd
import numpy as np
import plotly.express as px
import plotly.io as pio

# Functie om tijd van seconden naar HH:MM:SS formaat te converteren
def format_time(seconds):
    if pd.isna(seconds) or seconds <= 0:
        return '-'
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours >= 24:
        days = hours // 24
        hours = hours % 24
        return f'{days}d {hours}u {minutes:02d}m'
    elif hours > 0:
        return f'{hours}u {minutes:02d}m {seconds:02d}s'
    else:
        return f'{minutes}m {seconds:02d}s'

# De ultieme FIX voor datumparsing
def robust_date_parser_final(date_series):
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

# Helperfunctie voor activiteitssymbolen
def get_activity_icon(activity_type):
    activity_type = str(activity_type)
    if 'Fiets' in activity_type:
        return '🚴'
    elif 'Training' in activity_type:
        return '🎾'  # Tennisbal gekozen voor 'Training'
    elif 'Wandel' in activity_type or 'Hike' in activity_type:
        return '🚶'
    elif 'Hardloop' in activity_type:
        return '🏃'
    else:
        return '✨'


def genereer_html_dashboard(csv_bestandsnaam='activities.csv', html_output='dashboard.html'):
    """
    Dit is de hoofdfunctie die het definitieve, stabiele dashboard genereert, 
    met consistente stijlen voor alle summary cards.
    """
    print(f"Start analyse van: {csv_bestandsnaam}...")
    try:
        df = pd.read_csv(csv_bestandsnaam)
    except FileNotFoundError:
        print(f"Fout: Bestand '{csv_bestandsnaam}' niet gevonden. Zorg ervoor dat het in dezelfde map staat.")
        return
    except Exception as e:
        print(f"Fout bij het inlezen van de data: {e}")
        return

    # --- Data Voorbereiding en Opschoning (Ongewijzigd) ---
    df.columns = df.columns.str.strip()
    ACTIVITEITS_KOLOMNAAM = df.columns[3] 
    df['Datum van activiteit'] = robust_date_parser_final(df['Datum van activiteit'])
    df['Jaar'] = df['Datum van activiteit'].dt.year

    numeric_cols = ['Afstand', 'Verstreken tijd', 'Max. hartslag', 'Gemiddelde hartslag', 
                    'Maximaal wattage', 'Gemiddeld wattage', 'Max. snelheid', 'Gemiddelde snelheid']

    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(' ', '', regex=False).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    df['Afstand (km)'] = df['Afstand']
    df['Verstreken tijd (sec)'] = df['Verstreken tijd']
    
    df_clean = df.dropna(subset=['Datum van activiteit']).copy()

    df_clean['Gemiddelde km/u'] = df_clean['Gemiddelde snelheid']
    needs_calc = df_clean['Gemiddelde km/u'].isna() & (df_clean['Verstreken tijd (sec)'] > 0) & (df_clean['Afstand (km)'] > 0)
    df_clean.loc[needs_calc, 'Gemiddelde km/u'] = (df_clean.loc[needs_calc, 'Afstand (km)'] / (df_clean.loc[needs_calc, 'Verstreken tijd (sec)'] / 3600))
    df_clean['Gemiddelde km/u'] = df_clean['Gemiddelde km/u'].round(1)

    # FIX: Slimme Categorisatie (Ongewijzigd)
    df_clean['Activiteitstype_Basis'] = df_clean[ACTIVITEITS_KOLOMNAAM].astype(str).str.strip()
    df_clean['Final_Activiteitstype'] = df_clean['Activiteitstype_Basis']
    
    needs_categorization = df_clean['Activiteitstype_Basis'].isna() | (df_clean['Activiteitstype_Basis'] == '') | (df_clean['Activiteitstype_Basis'] == 'nan')
    naam_activiteit_lower = df_clean['Naam activiteit'].astype(str).str.lower()
    
    df_clean.loc[needs_categorization & naam_activiteit_lower.str.contains('loop|hardlopen'), 'Final_Activiteitstype'] = 'Hardloopsessie'
    df_clean.loc[needs_categorization & naam_activiteit_lower.str.contains('fiets|rit'), 'Final_Activiteitstype'] = 'Fietsrit'
    df_clean.loc[needs_categorization & naam_activiteit_lower.str.contains('wandel'), 'Final_Activiteitstype'] = 'Wandeling'
    
    df_clean['Final_Activiteitstype'] = df_clean['Final_Activiteitstype'].fillna('Niet Gecategoriseerd')
    df_clean.loc[df_clean['Final_Activiteitstype'] == 'nan', 'Final_Activiteitstype'] = 'Niet Gecategoriseerd'
    
    # --- Aggregatie en Globale Summary Cards ---
    
    overall_summary = df_clean.groupby('Final_Activiteitstype').agg(
        Totaal_Activiteiten=('Final_Activiteitstype', 'size'),
        Totale_Afstand_km=('Afstand (km)', 'sum'),
        Totale_Tijd_sec=('Verstreken tijd (sec)', 'sum')
    ).reset_index()

    fig_pie = px.pie(
        overall_summary, values='Totaal_Activiteiten', names='Final_Activiteitstype',
        title='Globale Distributie van Activiteiten', template="plotly_white", hole=.3, height=350
    )
    plotly_html_pie = pio.to_html(fig_pie, full_html=False, include_plotlyjs='cdn')
    
    # Globale Summary Cards (gebruikt .card-summary)
    summary_cards_html = ""
    for index, row in overall_summary.iterrows():
        formatted_time = format_time(row['Totale_Tijd_sec'])
        activity_icon = get_activity_icon(row['Final_Activiteitstype']) 
        
        summary_cards_html += f"""
            <div class="card card-summary">
                <h4>{row['Final_Activiteitstype']}</h4>
                <p class="summary-line"><span class="summary-icon">{activity_icon}</span> <span class="summary-value">{row['Totaal_Activiteiten']}</span></p>
                <p class="summary-line"><span class="summary-icon">📏</span> <span class="summary-value">{row['Totale_Afstand_km']:.1f} km</span></p>
                <p class="summary-line"><span class="summary-icon">⏱️</span> <span class="summary-value">{formatted_time}</span></p>
            </div>
        """
        
    global_content = f"""
        <div class="card-grid-2">
            <div class="card chart-container chart-pie">
                {plotly_html_pie}
            </div>
            <div class="card-grid-small">
                {summary_cards_html}
            </div>
        </div>
    """

    # --- Lijn Grafiek en Jaarlijkse Detailsecties ---
    
    df_clean['Jaar_Maand'] = df_clean['Datum van activiteit'].dt.to_period('M').astype(str)
    df_clean['Maand_Jaar'] = df_clean['Datum van activiteit'].dt.year 
    monthly_freq_per_year = df_clean.groupby(['Jaar_Maand', 'Maand_Jaar', 'Final_Activiteitstype']).size().reset_index(name='Aantal')
    monthly_freq_per_year.rename(columns={'Maand_Jaar': 'Jaar'}, inplace=True) 

    jaren_lijst = sorted(df_clean['Jaar'].dropna().unique().astype(int).tolist(), reverse=True)
    knop_html = f'<button class="jaar-knop active" data-view="Globaal" onclick="toonView(\'Globaal\', event)">Totaal Overzicht</button>'
    detail_secties_html = ""
    
    DETAIL_COLS_DISPLAY = {
        'Final_Activiteitstype': 'Sport', 'Naam activiteit': 'Activiteit', 'Afstand (km)': 'Afstand (km)',
        'Verstreken Tijd (Geformatteerd)': 'Verstreken Tijd', 'Gemiddelde km/u': 'Gem. Snelheid (km/u)', 'Gemiddelde hartslag': 'Gem. HR',
        'Gemiddeld wattage': 'Gem. Wattage'
    }

    for jaar in jaren_lijst:
        df_jaar = df_clean[df_clean['Jaar'] == jaar].copy()
        knop_html += f'<button class="jaar-knop" data-view="{jaar}" onclick="toonView(\'{jaar}\', event)">{jaar} ({len(df_jaar)})</button>'

        html_jaar_detail = ""
        for sport_type, df_sport in df_jaar.groupby('Final_Activiteitstype'):
            
            df_sport['Verstreken Tijd (Geformatteerd)'] = df_sport['Verstreken tijd (sec)'].apply(format_time)

            total_activities = df_sport['Final_Activiteitstype'].size
            total_distance = df_sport['Afstand (km)'].sum()
            total_time_sec = df_sport['Verstreken tijd (sec)'].sum()
            formatted_time_sport = format_time(total_time_sec)
            activity_icon = get_activity_icon(sport_type) # Gebruik de nieuwe functie

            df_sport_monthly_year = monthly_freq_per_year[(monthly_freq_per_year['Final_Activiteitstype'] == sport_type) & (monthly_freq_per_year['Jaar'] == jaar)]
            
            fig_line_year_sport = px.line(
                df_sport_monthly_year, x='Jaar_Maand', y='Aantal', title=f'Maandfrequentie {jaar}',
                labels={'Aantal': 'Sessies', 'Jaar_Maand': 'Datum'}, template="plotly_white", height=250
            )
            fig_line_year_sport.update_traces(mode='lines+markers')
            plotly_html_line_year_sport = pio.to_html(fig_line_year_sport, full_html=False, include_plotlyjs='cdn')
            
            df_sport_display = df_sport[list(DETAIL_COLS_DISPLAY.keys())].rename(columns=DETAIL_COLS_DISPLAY).drop(columns=['Sport'])
            numeric_format_map = {'Afstand (km)': '{:.2f}', 'Gem. Snelheid (km/u)': '{:.1f}', 'Gem. HR': '{:.0f}', 'Gem. Wattage': '{:.0f}'}
            for col, fmt in numeric_format_map.items():
                if col in df_sport_display.columns:
                    df_sport_display[col] = df_sport_display[col].apply(
                        lambda x: fmt.format(x) if pd.notna(x) and isinstance(x, (int, float, np.number)) else '-'
                    )

            # Detailweergave (gebruikt .card-stats)
            html_jaar_detail += f"""
                <div class="sport-card">
                    <h4>{sport_type}</h4>
                    <div class="card-grid-2">
                        <div class="card-stats"> 
                            <p class="summary-line"><span class="summary-icon">{activity_icon}</span> <span class="summary-value">{total_activities}</span></p>
                            <p class="summary-line"><span class="summary-icon">📏</span> <span class="summary-value">{total_distance:.1f} km</span></p>
                            <p class="summary-line"><span class="summary-icon">⏱️</span> <span class="summary-value">{formatted_time_sport}</span></p>
                        </div>
                        <div class="chart-container-small">
                            {plotly_html_line_year_sport}
                        </div>
                    </div>
                    
                    <h5>Details ({len(df_sport)} items)</h5>
                    {df_sport_display.to_html(classes='table table-bordered table-striped detail-table', index=False, border=0)}
                </div>
            """
        
        detail_secties_html += f"""
            <div id="view-{jaar}" class="jaar-sectie" style="display:none;">
                {html_jaar_detail}
            </div>
        """


    # --- Finale HTML Assemblage ---
    
    global_section_html = f"""
        <div id="view-Globaal" class="jaar-sectie" style="display: block;">
            <h2>Globale Samenvatting</h2>
            <p>Verdeling van activiteiten over de gehele dataset.</p>
            {global_content}
            
            <h2>Maandelijkse Trends (Alle Jaren)</h2>
            <p>Volg de frequentie van je trainingen door de jaren heen. Klik op de sporten in de legenda om ze aan/uit te zetten.</p>
            <div class="card chart-container chart-container-big">
                {plotly_html_line_all_years}
            </div>
        </div>
    """


    dashboard_html = f"""
    <!DOCTYPE html>
    <html lang="nl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Definitief Activiteitendashboard</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600&display=swap');
            :root {{
                --muted-teal: #6c9a8bff; --sweet-salmon: #e8998dff; --almond-silk: #eed2ccff;
                --parchment: #fbf7f4ff; --toffee-brown: #a1683aff; --text-dark: #333;
                --font-size-small: 13px;
            }}
            body {{ 
                font-family: 'Oswald', sans-serif; margin: 0; padding: 20px 0;
                background-color: var(--parchment); color: var(--text-dark); font-size: var(--font-size-small);
            }}
            .container {{ 
                max-width: 1200px; width: 95%; margin: auto; background: #fff; padding: 30px; 
                border-radius: 12px; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1); 
            }}
            h1 {{ color: var(--toffee-brown); border-bottom: 3px solid var(--almond-silk); padding-bottom: 15px; font-size: 32px; }}
            h2 {{ color: var(--sweet-salmon); margin-top: 30px; border-bottom: 1px solid var(--almond-silk); padding-bottom: 5px; font-size: 20px; }}
            h3 {{ color: var(--muted-teal); margin-top: 25px; font-size: 18px; }}
            h4 {{ color: var(--text-dark); margin-top: 5px; font-size: 16px; font-weight: 600; }}
            h5 {{ color: var(--muted-teal); margin-top: 20px; font-size: 15px; font-weight: 600; }}
            
            /* Layouts */
            .card-grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
            .card-grid-small {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: stretch; }}
            
            /* Cards and Charts */
            .card {{ background: #fff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid var(--almond-silk); }}
            
            /* *** UNIFIED SUMMARY CARD STYLES *** */
            .card-summary, .card-stats {{ 
                flex-basis: calc(50% - 5px); 
                display: flex; 
                flex-direction: column; 
                justify-content: space-between;
                padding: 10px; /* Kleinere padding */
                min-height: 100px;
                background: #fff; /* Override card-stats background to white */
                border-radius: 8px; 
                font-weight: 400; 
                font-size: var(--font-size-small);
                box-shadow: none; /* Remove extra shadow */
            }}
            
            /* Override for card-stats specific container style to make it look like .card-summary */
            .sport-card .card-stats {
                background: var(--almond-silk); /* Geef de stats card een lichte achtergrond */
                font-weight: 600;
            }

            .card-summary h4, .card-stats h4 {{
                margin-bottom: 5px;
                font-size: 15px;
            }}
            
            /* Stijl voor alle samenvattingsparagrafen (in zowel summary als stats cards) */
            .card-summary p, .card-stats p {{
                margin: 3px 0; /* Minder verticale ruimte tussen de lijnen */
                font-size: 14px;
                line-height: 1.2;
                display: flex; 
                align-items: center;
            }}
            .summary-icon {{
                margin-right: 8px;
            }}
            .summary-value {{
                font-size: 1.4em; /* Maak het cijfer groter */
                font-weight: 700; /* Maak het cijfer vetter */
                color: var(--text-dark);
            }}
            
            /* Oude stijlen behouden */
            .chart-container {{ height: 400px; padding: 0 !important; }}
            .chart-pie {{ height: 350px !important; }}
            .chart-container-big {{ height: 550px !important; padding: 0 !important; }}
            
            .chart-container-small {{ height: 300px; padding: 15px !important; }}

            /* Tabellen */
            .table-bordered {{ width: 100%; border-collapse: collapse; margin-top: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); font-size: var(--font-size-small); table-layout: auto; }}
            .table-bordered th, .table-bordered td {{ padding: 8px 12px; border: 1px solid var(--almond-silk); text-align: right; }}
            .table-bordered th {{ background-color: var(--muted-teal); color: white; text-align: center; font-weight: 600; }}
            .table-bordered tbody tr:nth-child(even) {{ background-color: #f6f6f9; }}
            .table-bordered tbody tr:hover {{ background-color: var(--almond-silk); }}
            .table-bordered tbody tr:last-child {{ font-weight: bold; background-color: var(--sweet-salmon); color: white; }}
            .detail-table th:nth-child(-n+2), .detail-table td:nth-child(-n+2) {{ text-align: left; }}
            .sport-card {{ border: 1px solid var(--almond-silk); border-radius: 8px; padding: 15px; margin-bottom: 20px; background-color: #fff; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05); }}
            
            /* Knoppen */
            .knop-container {{ margin-bottom: 20px; border-bottom: 1px solid var(--almond-silk); padding-bottom: 5px; }}
            .jaar-knop {{ background-color: #fff; color: var(--muted-teal); border: 2px solid var(--muted-teal); padding: 10px 15px; margin: 5px 5px 5px 0; cursor: pointer; border-radius: 5px; transition: all 0.3s; font-weight: 600; }}
            .jaar-knop:hover {{ background-color: var(--muted-teal); color: white; }}
            .jaar-knop.active {{ background-color: var(--sweet-salmon); color: white; border-color: var(--sweet-salmon); box-shadow: 0 4px 8px rgba(232, 153, 141, 0.4); }}
            .jaar-sectie {{ margin-top: 25px; padding: 20px; border-radius: 8px; background: #fff; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05); }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Definitief Activiteitendashboard</h1>
            <p>Geüpdatet op: <strong>{pd.Timestamp('now').strftime('%d-%m-%Y om %H:%M')}</strong></p>

            <div class="knop-container">
                {knop_html}
            </div>

            <div id="detail-container">
                
                {global_section_html}
                
                {detail_secties_html}
            </div>

        </div>

        <script>
            // Functie voor het schakelen tussen JAAR en GLOBAAL
            function toonView(view_id, event) {{
                const secties = document.querySelectorAll('.jaar-sectie');
                const knoppen = document.querySelectorAll('.jaar-knop');
                
                // Verberg alle secties
                secties.forEach(sectie => {{ sectie.style.display = 'none'; }});
                
                // Deactiveer alle knoppen
                knoppen.forEach(knop => {{ knop.classList.remove('active'); }});

                // Toon de gevraagde sectie
                const actieveSectie = document.getElementById('view-' + view_id);
                if (actieveSectie) {{ actieveSectie.style.display = 'block'; }}
                
                // Activeer de aangeklikte knop
                if (event && event.currentTarget) {{ event.currentTarget.classList.add('active'); }}
            }}
            
            // Activeer de 'Totaal Overzicht' knop en de bijbehorende weergave bij het laden
            document.addEventListener('DOMContentLoaded', () => {{
                // Zorg ervoor dat de 'Globaal' sectie wordt getoond
                const globaleSectie = document.getElementById('view-Globaal');
                if (globaleSectie) {{ globaleSectie.style.display = 'block'; }}
                
                // Activeer de 'Totaal Overzicht' knop
                const globaleKnop = document.querySelector('[data-view="Globaal"]');
                if (globaleKnop) {{ globaleKnop.classList.add('active'); }}
            }});
        </script>
    </body>
    </html>
    """
    
    with open('dashboard.html', 'w', encoding='utf-8') as f:
        f.write(dashboard_html)

    print(f"\n✅ Het finale dashboard is succesvol gegenereerd in 'dashboard.html' met universele kaartstijlen!")


# Directe aanroep van de functie om de uitvoering te garanderen
genereer_html_dashboard('activities.csv')