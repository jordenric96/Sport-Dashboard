import pandas as pd
import numpy as np
import plotly.express as px
import plotly.io as pio

# Definieer de kleuren die in de Plotly grafieken gebruikt moeten worden
CUSTOM_COLORS = [
    '#6c9a8b',  # --muted-teal
    '#e8998d',  # --sweet-salmon
    '#a1683a',  # --toffee-brown
    '#eed2cc',  # --almond-silk
]

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
        return '🎾'
    elif 'Wandel' in activity_type or 'Hike' in activity_type:
        return '🚶'
    elif 'Hardloop' in activity_type:
        return '🏃'
    else:
        return '✨'
        
# Helperfunctie om de sport-specifieke statistieken te formatteren
def format_sport_specific_stats(row, activity_type):
    stats_html = ""
    
    # 1. Gemiddelde Hartslag
    hr_avg = row.get('Gemiddelde_Hartslag', np.nan)
    stats_html += f'<p class="summary-line"><span class="summary-icon">❤️</span> <span class="summary-value">{int(hr_avg):d} bpm</span></p>' if pd.notna(hr_avg) and hr_avg > 0 else ''

    # 2. Snelste en Langste Rit/Loopsessie
    is_ride = 'Fiets' in activity_type
    is_run = 'Hardloop' in activity_type
    
    max_dist = row.get('Max_Afstand_km', np.nan)
    max_speed = row.get('Max_Snelheid_km_u', np.nan)

    # Langste Rit/Loopsessie
    if (is_ride or is_run) and pd.notna(max_dist) and max_dist > 0:
        label = 'Langste Rit' if is_ride else 'Langste Loop'
        stats_html += f'<p class="summary-line"><span class="summary-icon">🗺️</span> <span class="summary-label">{label}:</span> <span class="summary-value-small">{max_dist:.1f} km</span></p>'
    
    # Snelste Rit/Loopsessie
    if (is_ride or is_run) and pd.notna(max_speed) and max_speed > 0:
        label = 'Snelste Rit' if is_ride else 'Snelste Loop'
        stats_html += f'<p class="summary-line"><span class="summary-icon">⚡</span> <span class="summary-label">{label}:</span> <span class="summary-value-small">{max_speed:.1f} km/u</span></p>'

    return stats_html

# Functie om de gedetailleerde lijst in HTML te genereren
def genereer_detail_tabel_html(df_data):
    if df_data.empty:
        return '<p class="no-data-msg">Geen activiteiten gevonden voor dit overzicht.</p>'

    # Sorteer op datum, OUDSTE BOVENAAN
    df_data = df_data.sort_values(by='Datum', ascending=True) 
    
    html_rows = []
    
    # OPGELOST: Kolomvolgorde teruggezet naar: Stijging, Gem. Hartslag
    header = """
        <thead>
            <tr>
                <th>Datum</th>
                <th>Activiteitstype</th>
                <th>Naam Activiteit</th>
                <th>Afstand (km)</th>
                <th>Tijd</th>
                <th>Gem. Snelheid (km/u)</th>
                <th>Stijging (m)</th>
                <th>Gem. Hartslag (bpm)</th> 
                <th>Calorieën</th>
            </tr>
        </thead>
    """
    
    # Rijen genereren
    for _, row in df_data.iterrows():
        datum_str = row['Datum'].strftime('%d %b %Y') if pd.notna(row['Datum']) else '-'
        activiteit_type_str = row['Activiteitstype'] 
        activiteit_naam = row['Naam_Activiteit'] if pd.notna(row['Naam_Activiteit']) and row['Naam_Activiteit'].strip() else row['Activiteitstype']
        afstand_str = f"{row['Afstand_km']:.1f}" if pd.notna(row['Afstand_km']) else '-'
        tijd_str = format_time(row['Beweegtijd_sec'])
        snelheid_str = f"{row['Gemiddelde_Snelheid_km_u']:.1f}" if pd.notna(row['Gemiddelde_Snelheid_km_u']) and row['Afstand_km'] > 0 else '-'
        stijging_str = f"{row['Totale_Stijging_m']:.0f}" if pd.notna(row['Totale_Stijging_m']) else '-'
        hartslag_str = f"{row['Gemiddelde_Hartslag']:.0f}" if pd.notna(row['Gemiddelde_Hartslag']) and row['Gemiddelde_Hartslag'] > 0 else '-'
        calorieen_str = f"{row['Calorieen']:.0f}" if pd.notna(row['Calorieen']) and row['Calorieen'] > 0 else '-'
        
        # OPGELOST: Data-rijen aangepast aan de correcte volgorde: Stijging, Gem. Hartslag
        html_row = f"""
            <tr data-activity-type="{activiteit_type_str}"> 
                <td>{datum_str}</td>
                <td>{activiteit_type_str}</td>
                <td>{activiteit_naam}</td>
                <td class="num">{afstand_str}</td>
                <td>{tijd_str}</td>
                <td class="num">{snelheid_str}</td>
                <td class="num">{stijging_str}</td> 
                <td class="num hr-hidden">{hartslag_str}</td> 
                <td class="num">{calorieen_str}</td>
            </tr>
        """
        html_rows.append(html_row)
        
    return f"""
    <div class="detail-table-container">
        <h2 class="detail-title">Gedetailleerd Overzicht</h2>
        <table class="activity-table">
            {header}
            <tbody>
                {''.join(html_rows)}
            </tbody>
        </table>
    </div>
    """

# Functie om de HTML voor het filter te genereren
def genereer_filter_html(unieke_activiteiten, sectie_id):
    options = ['<option value="ALL">Alle Activiteiten</option>']
    for activity in unieke_activiteiten:
        options.append(f'<option value="{activity}">{activity}</option>')
        
    return f"""
    <div class="filter-container">
        <label for="filter-{sectie_id}">Filter op Sport:</label>
        <select id="filter-{sectie_id}" onchange="filterDetailTabel('{sectie_id}')">
            {''.join(options)}
        </select>
    </div>
    """


def genereer_html_dashboard(csv_bestandsnaam='activities.csv', html_output='dashboard.html'):
    """
    Dit is de hoofdfunctie die het definitieve, stabiele dashboard genereert.
    """
    print(f"Start analyse van: {csv_bestandsnaam}...")
    try:
        df = pd.read_csv(csv_bestandsnaam)
    except FileNotFoundError:
        print(f"Fout: Bestand '{csv_bestandsnaam}' niet gevonden. Zorg ervoor dat het in dezelfde map staat.")
        return
        
    # --- FIX 1: Omzetten van m/s naar km/u ---
    if 'Gemiddelde snelheid' in df.columns:
        df['Gemiddelde snelheid'] = df['Gemiddelde snelheid'] * 3.6
    if 'Max. snelheid' in df.columns:
        df['Max. snelheid'] = df['Max. snelheid'] * 3.6
    print('✅ Snelheid (m/s) succesvol geconverteerd naar km/u.')
    
    # Herbenoemen en opschonen van kolommen
    df = df.rename(columns={
        'Datum van activiteit': 'Datum',
        'Naam activiteit': 'Naam_Activiteit', 
        'Activiteitstype': 'Activiteitstype',
        'Verstreken tijd': 'Verstreken_Tijd_sec',
        'Beweegtijd': 'Beweegtijd_sec',
        'Afstand': 'Afstand_km', 
        'Max. snelheid': 'Max_Snelheid_km_u',
        'Gemiddelde snelheid': 'Gemiddelde_Snelheid_km_u',
        'Totale stijging': 'Totale_Stijging_m',
        'Max. hartslag': 'Max_Hartslag',
        'Gemiddelde hartslag': 'Gemiddelde_Hartslag',
        'Max. cadans': 'Max_Cadans',
        'Gemiddelde cadans': 'Gemiddelde_Cadans',
        'Calorieën': 'Calorieen',
        'Gemiddeld wattage': 'Gemiddeld_Wattage',
        'Totaal geheven gewicht': 'Totaal_Geheven_Gewicht_kg',
    })

    # --- FIX 2: Conversie van komma naar punt voor numerieke kolommen ---
    kolommen_met_komma_als_decimaal = ['Afstand_km', 'Totale_Stijging_m', 'Gemiddelde_Snelheid_km_u', 'Max_Snelheid_km_u', 'Calorieen', 'Gemiddeld_Wattage', 'Totaal_Geheven_Gewicht_kg', 'Gemiddelde_Hartslag']
    
    for col in kolommen_met_komma_als_decimaal:
        if col in df.columns and df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce') 
    
    print('✅ Decimale komma\'s succesvol geconverteerd naar punten.')
    
    # Datum parsing
    df['Datum'] = robust_date_parser_final(df['Datum'])
    df['Jaar'] = df['Datum'].dt.year
    df['Maand'] = df['Datum'].dt.month
    df['Week'] = df['Datum'].dt.isocalendar().week.astype(pd.Int64Dtype()) 
    df['Week'] = df['Week'].fillna(0).astype(int) 
    
    # Selecteer alleen de relevante kolommen voor de analyse
    relevante_kolommen = [
        'Datum', 'Naam_Activiteit', 'Jaar', 'Maand', 'Week', 'Activiteitstype', 
        'Afstand_km', 'Verstreken_Tijd_sec', 'Beweegtijd_sec', 'Totale_Stijging_m',
        'Gemiddelde_Snelheid_km_u', 'Max_Snelheid_km_u', 'Gemiddelde_Hartslag', 
        'Calorieen', 'Gemiddeld_Wattage', 'Totaal_Geheven_Gewicht_kg'
    ]
    df_clean = df[relevante_kolommen].copy()
    
    # Opschonen van NaN's 
    df_clean.loc[:, 'Totale_Stijging_m'] = df_clean['Totale_Stijging_m'].fillna(0)
    df_clean.loc[:, 'Calorieen'] = df_clean['Calorieen'].fillna(0)
    
    # --- FIX 3: Verwijder de filter op Afstand_km > 0.1 om alle sessies mee te tellen ---
    df_clean = df_clean[df_clean['Activiteitstype'].notna()].copy() 

    print("✅ Data opgeschoond en voorbewerkt (filter > 0.1 km verwijderd).")
    
    # --- Gegevensaggregatie ---

    df_clean['Jaar_Maand_Period'] = df_clean['Datum'].dt.to_period('M')

    # Bepaal de periode range voor de zero-filling
    min_date = df_clean['Datum'].min().to_period('M')
    max_date = df_clean['Datum'].max().to_period('M')
    full_periods = pd.period_range(start=min_date, end=max_date, freq='M')
    
    # Index voor zero-filling (alle combinaties van periode x activiteitstype)
    full_index_sports = pd.MultiIndex.from_product([full_periods, df_clean['Activiteitstype'].unique()], names=['Jaar_Maand_Period', 'Activiteitstype'])


    # 1. Aggregatie Sessions (voor sessions graph) - MET ZERO FILLING
    sessions_raw = df_clean.groupby(['Jaar_Maand_Period', 'Activiteitstype']).size().rename('Aantal_Activiteiten')
    agg_sessies_maand = sessions_raw.reindex(full_index_sports, fill_value=0).reset_index()
    agg_sessies_maand['Jaar'] = agg_sessies_maand['Jaar_Maand_Period'].dt.year
    agg_sessies_maand['Maand'] = agg_sessies_maand['Jaar_Maand_Period'].dt.month
    agg_sessies_maand['Jaar_Maand'] = agg_sessies_maand['Jaar'].astype(str) + '-' + agg_sessies_maand['Maand'].astype(str).str.zfill(2)
    
    # 2. Aggregatie Afstand (for distance graph) - MET ZERO FILLING
    distance_raw = df_clean.groupby(['Jaar_Maand_Period', 'Activiteitstype'])['Afstand_km'].sum().rename('Afstand_km')
    agg_maand_base = distance_raw.reindex(full_index_sports, fill_value=0).reset_index()
    
    # Sum over all sports for total distance per month
    agg_maand = agg_maand_base.groupby('Jaar_Maand_Period')['Afstand_km'].sum().rename('Afstand_km').reset_index()
    agg_maand['Jaar'] = agg_maand['Jaar_Maand_Period'].dt.year
    agg_maand['Maand'] = agg_maand['Jaar_Maand_Period'].dt.month
    agg_maand['Jaar_Maand'] = agg_maand['Jaar'].astype(str) + '-' + agg_maand['Maand'].astype(str).str.zfill(2)


    # Aggregeren per jaar en activiteitstype (voor summary cards)
    agg_jaar = df_clean.groupby(['Jaar', 'Activiteitstype']).agg(
        Totaal_Afstand_km=('Afstand_km', 'sum'),
        Totaal_Tijd_sec=('Beweegtijd_sec', 'sum'),
        Totaal_Stijging_m=('Totale_Stijging_m', 'sum'),
        Totaal_Calorieen=('Calorieen', 'sum'),
        Aantal_Activiteiten=('Activiteitstype', 'size'),
        Gemiddelde_Snelheid_km_u=('Gemiddelde_Snelheid_km_u', lambda x: x[df_clean.loc[x.index, 'Afstand_km'] > 0].mean())
    ).reset_index()
    
    agg_jaar['Gemiddelde_Tijd_sec'] = agg_jaar['Totaal_Tijd_sec'] / agg_jaar['Aantal_Activiteiten']
    
    # Bepaal de max stats per jaar
    max_stats = df_clean.groupby(['Jaar', 'Activiteitstype']).agg(
        Max_Afstand_km=('Afstand_km', 'max'),
        # Max. gemiddelde snelheid van een sessie
        Max_Gemiddelde_Snelheid_km_u=('Gemiddelde_Snelheid_km_u', 'max'),
    ).reset_index()
    
    agg_jaar = agg_jaar.merge(max_stats, on=['Jaar', 'Activiteitstype'], how='left')

    # Berekenen van de zwaarste workout voor Totaal Geheven Gewicht 
    agg_jaar_gewicht = df_clean[df_clean['Totaal_Geheven_Gewicht_kg'].notna() & (df_clean['Totaal_Geheven_Gewicht_kg'] > 0)].groupby('Jaar')['Totaal_Geheven_Gewicht_kg'].max().reset_index().rename(columns={'Totaal_Geheven_Gewicht_kg': 'Max_Gewicht'})
    
    # Aggregeren van alle data over de tijd (globaal overzicht)
    agg_totaal = df_clean.groupby('Activiteitstype').agg(
        Totaal_Afstand_km=('Afstand_km', 'sum'),
        Totaal_Tijd_sec=('Beweegtijd_sec', 'sum'),
        Totaal_Stijging_m=('Totale_Stijging_m', 'sum'),
        Totaal_Calorieen=('Calorieen', 'sum'),
        Aantal_Activiteiten=('Activiteitstype', 'size'),
        Gemiddelde_Snelheid_km_u=('Gemiddelde_Snelheid_km_u', lambda x: x[df_clean.loc[x.index, 'Afstand_km'] > 0].mean())
    ).reset_index()
    
    agg_totaal['Gemiddelde_Tijd_sec'] = agg_totaal['Totaal_Tijd_sec'] / agg_totaal['Aantal_Activiteiten']

    # Bepaal de max stats in het totale overzicht
    max_stats_totaal = df_clean.groupby('Activiteitstype').agg(
        Max_Afstand_km=('Afstand_km', 'max'),
        Max_Gemiddelde_Snelheid_km_u=('Gemiddelde_Snelheid_km_u', 'max')
    ).reset_index()
    
    agg_totaal = agg_totaal.merge(max_stats_totaal, on='Activiteitstype', how='left')
    
    unieke_activiteiten = sorted(df_clean['Activiteitstype'].unique())
    
    print("✅ Gegevens succesvol geaggregeerd.")

    # --- Plotly Grafieken Genereren ---

    # 1. Sessions per Month per Sport (Nieuwe Grafiek)
    
    fig_sessies_per_maand = px.bar(agg_sessies_maand, 
                       x='Jaar_Maand', 
                       y='Aantal_Activiteiten', 
                       color='Activiteitstype', 
                       title='Aantal Sessies per Maand (per Sport)',
                       color_discrete_sequence=CUSTOM_COLORS)
    fig_sessies_per_maand.update_layout(
        xaxis_title="Jaar en Maand", 
        yaxis_title="Aantal Sessies", 
        xaxis={'tickmode': 'array', 'tickvals': agg_sessies_maand['Jaar_Maand'][::2], 'ticktext': agg_sessies_maand['Jaar_Maand'][::2]}, # Toon niet alle ticks
        margin=dict(t=50, b=20, l=20, r=20),
        legend_title_text='Sport'
    )

    # 2. Afstand per Maand (Balkgrafiek - Blijft ter referentie)
    fig_maand = px.bar(agg_maand, 
                       x='Jaar_Maand', 
                       y='Afstand_km', 
                       color='Jaar', 
                       title='Totale Afstand per Maand',
                       color_discrete_sequence=CUSTOM_COLORS)
    fig_maand.update_layout(
        xaxis_title="Jaar en Maand", 
        yaxis_title="Afstand (km)", 
        xaxis={'tickmode': 'array', 'tickvals': agg_maand['Jaar_Maand'][::2], 'ticktext': agg_maand['Jaar_Maand'][::2]}, 
        margin=dict(t=50, b=20, l=20, r=20),
        legend_title_text='Jaar'
    )
    
    print("✅ Grafieken gegenereerd.")
    
    # --- HTML Genereren ---

    # Functie om de HTML-statistiekenkaartjes te genereren
    def genereer_summary_card_html(row, is_totaal=False):
        activiteit = row['Activiteitstype']
        icon = get_activity_icon(activiteit)
        
        # FIX: Gebruik Totaal_Stijging_m (de geaggregeerde kolomnaam)
        afstand_totaal = f"{row['Totaal_Afstand_km']:.1f} km"
        tijd_totaal = format_time(row['Totaal_Tijd_sec'])
        stijging_totaal = f"{row['Totaal_Stijging_m']:.0f} m"
        aantal = f"{row['Aantal_Activiteiten']:d}"
        
        max_dist_row = row.get('Max_Afstand_km', np.nan)
        max_avg_speed_row = row.get('Max_Gemiddelde_Snelheid_km_u', np.nan) # Gebruikt Max Gem. Snelheid
        avg_speed = row.get('Gemiddelde_Snelheid_km_u', np.nan)
        
        stats_html = ""
        
        if pd.notna(avg_speed) and avg_speed > 0:
            stats_html += f'<p class="summary-line"><span class="summary-icon">⏱️</span> <span class="summary-label">Gem. Snelheid:</span> <span class="summary-value-small">{avg_speed:.1f} km/u</span></p>'
            
        if pd.notna(max_dist_row) and max_dist_row > 0:
            label = 'Langste Rit' if 'Fiets' in activiteit else ('Langste Loop' if 'Hardloop' in activiteit else 'Max. Afstand')
            stats_html += f'<p class="summary-line"><span class="summary-icon">🗺️</span> <span class="summary-label">{label}:</span> <span class="summary-value-small">{max_dist_row:.1f} km</span></p>'
        
        if pd.notna(max_avg_speed_row) and max_avg_speed_row > 0:
            label = 'Snelste Gem. Rit' if 'Fiets' in activiteit else 'Snelste Gem. Loop' # Aangepast label
            stats_html += f'<p class="summary-line"><span class="summary-icon">⚡</span> <span class="summary-label">{label}:</span> <span class="summary-value-small">{max_avg_speed_row:.1f} km/u</span></p>'
            
        if is_totaal and 'Training' in activiteit:
            max_gewicht = df_clean[df_clean['Activiteitstype'].str.contains('Training', na=False)]['Totaal_Geheven_Gewicht_kg'].max()
            if pd.notna(max_gewicht) and max_gewicht > 0:
                stats_html += f'<p class="summary-line"><span class="summary-icon">🏋️</span> <span class="summary-label">Max. Gewicht:</span> <span class="summary-value-small">{max_gewicht:,.0f} kg</span></p>'


        html = f"""
        <div class="summary-card" data-type="{activiteit}">
            <div class="card-header">
                <span class="activity-icon">{icon}</span>
                <h3 class="activity-title">{activiteit} ({aantal}x)</h3>
            </div>
            <div class="stats-group">
                <p class="stat-main"><span>Tijd:</span> {tijd_totaal}</p>
                <p class="stat-main"><span>Afstand:</span> {afstand_totaal}</p>
                <p class="stat-main"><span>Stijging:</span> {stijging_totaal}</p>
            </div>
            <div class="stats-details">
                {stats_html}
            </div>
        </div>
        """
        return html

    # Genereer kaarten voor het totale overzicht
    totaal_kaarten_html = "".join(agg_totaal.apply(lambda row: genereer_summary_card_html(row, is_totaal=True), axis=1).tolist())
    
    # Genereer de detailtabel voor het globale overzicht
    filter_globaal_html = genereer_filter_html(unieke_activiteiten, 'Globaal')
    totaal_detail_tabel = genereer_detail_tabel_html(df_clean)

    # Genereer secties per jaar
    jaar_secties_html = ""
    beschikbare_jaren = sorted(agg_jaar['Jaar'].unique(), reverse=True)
    
    # Maak de knoppen voor jaarselectie
    jaar_knoppen_html = '<button class="jaar-knop active" onclick="showView(\'Globaal\', event)" data-view="Globaal">Totaal Overzicht</button>'
    for jaar in beschikbare_jaren:
        jaar_knoppen_html += f'<button class="jaar-knop" onclick="showView(\'{jaar}\', event)" data-view="{jaar}">{jaar}</button>'

    for jaar in beschikbare_jaren:
        df_jaar = agg_jaar[agg_jaar['Jaar'] == jaar].copy()
        jaar_kaarten_html = "".join(df_jaar.apply(genereer_summary_card_html, axis=1).tolist())
        
        # Gegevens voor maandelijkse sessies per sport voor dit jaar
        df_sessies_jaar = agg_sessies_maand[agg_sessies_maand['Jaar'] == jaar].copy()
        
        fig_jaar_sessies_per_maand = px.bar(df_sessies_jaar, 
                           x='Jaar_Maand', 
                           y='Aantal_Activiteiten', 
                           color='Activiteitstype', 
                           title=f'Aantal Sessies per Maand in {jaar} (per Sport)',
                           color_discrete_sequence=CUSTOM_COLORS)
        fig_jaar_sessies_per_maand.update_layout(
            xaxis_title="Maand", 
            yaxis_title="Aantal Sessies", 
            xaxis={'tickmode': 'array', 'tickvals': df_sessies_jaar['Jaar_Maand'], 'ticktext': df_sessies_jaar['Maand'].apply(lambda x: pd.to_datetime(str(x), format='%m').strftime('%b'))}, # Toon maandaanduiding
            margin=dict(t=50, b=20, l=20, r=20),
            legend_title_text='Sport'
        )

        # Gegevens voor maandelijkse afstand voor dit jaar
        df_maand_jaar = agg_maand[agg_maand['Jaar'] == jaar].copy()

        fig_jaar_afstand_per_maand = px.bar(df_maand_jaar, 
                           x='Jaar_Maand', 
                           y='Afstand_km', 
                           color='Jaar', 
                           title=f'Totale Afstand per Maand in {jaar}',
                           color_discrete_sequence=CUSTOM_COLORS[:1])
        fig_jaar_afstand_per_maand.update_layout(
            xaxis_title="Maand", 
            yaxis_title="Afstand (km)", 
            xaxis={'tickmode': 'array', 'tickvals': df_maand_jaar['Jaar_Maand'], 'ticktext': df_maand_jaar['Maand'].apply(lambda x: pd.to_datetime(str(x), format='%m').strftime('%b'))}, # Toon maandaanduiding
            margin=dict(t=50, b=20, l=20, r=20),
            legend_title_text='Jaar',
            showlegend=False
        )
        
        # Max. Gewicht voor dit jaar
        max_gewicht_jaar = agg_jaar_gewicht[agg_jaar_gewicht['Jaar'] == jaar]['Max_Gewicht'].iloc[0] if jaar in agg_jaar_gewicht['Jaar'].values else np.nan
        gewicht_html = f'<p><strong>Zwaarste workout (max. getild gewicht):</strong> {max_gewicht_jaar:,.0f} kg</p>' if pd.notna(max_gewicht_jaar) else ''
        
        # Genereer de detailtabel voor dit jaar
        df_detail_jaar = df_clean[df_clean['Jaar'] == jaar]
        filter_jaar_html = genereer_filter_html(unieke_activiteiten, str(jaar))
        jaar_detail_tabel = genereer_detail_tabel_html(df_detail_jaar)


        # FIX: Zorg ervoor dat de grafieken in de jaar-secties ook chart-full-width gebruiken
        jaar_secties_html += f"""
        <div id="view-{jaar}" class="jaar-sectie" style="display: none;">
            <h2>Overzicht {jaar}</h2>
            <div class="summary-container">
                {jaar_kaarten_html}
            </div>
            
            <div class="chart-full-width">
                {fig_jaar_sessies_per_maand.to_html(full_html=False, include_plotlyjs='cdn')}
            </div>
            <div class="chart-full-width">
                {fig_jaar_afstand_per_maand.to_html(full_html=False, include_plotlyjs='cdn')}
            </div>
            
            <div class="footer-note">{gewicht_html}</div>
            
            <a href="#" onclick="revealHeartRate(event)" class="hr-reveal-button">Toon Gemiddelde Hartslag</a>
            {filter_jaar_html}
            {jaar_detail_tabel}
            
        </div>
        """

    # --- Finale HTML-structuur ---

    dashboard_html = f"""
    <!DOCTYPE html>
    <html lang="nl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sport overzicht Jorden Ricour</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600&display=swap');
            :root {{
                --muted-teal: #6c9a8b; --sweet-salmon: #e8998d; --almond-silk: #eed2cc;
                --parchment: #fbf7f4; --toffee-brown: #a1683a; --text-dark: #333;
                --font-size-small: 13px;
            }}
            body {{ 
                font-family: 'Oswald', sans-serif; margin: 0; padding: 20px 0;
                background-color: var(--parchment); color: var(--text-dark); font-size: var(--font-size-small);
            }}
            .container {{ 
                max-width: 1200px; width: 95%; margin: auto; background: #fff; padding: 30px; 
                border-radius: 12px; box-shadow: 0 8px 8px rgba(0, 0, 0, 0.05); 
            }}
            h1 {{ color: var(--toffee-brown); border-bottom: 3px solid var(--almond-silk); padding-bottom: 10px; }}
            h2 {{ color: var(--muted-teal); font-size: 1.5em; margin-bottom: 20px; }}
            
            /* Knoppen Navigatie */
            .nav-buttons {{ margin-bottom: 25px; display: flex; flex-wrap: wrap; gap: 10px; }}
            .jaar-knop {{
                background-color: #fff; color: var(--toffee-brown); border: 1px solid var(--toffee-brown);
                padding: 10px 15px; cursor: pointer; border-radius: 5px; font-weight: 600;
                transition: all 0.2s; font-family: 'Oswald', sans-serif; text-transform: uppercase;
                font-size: var(--font-size-small);
            }}
            .jaar-knop:hover {{ background-color: var(--almond-silk); }}
            .jaar-knop.active {{ background-color: var(--toffee-brown); color: #fff; }}
            
            /* Samenvattingskaarten */
            .summary-container {{ 
                display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 30px; 
            }}
            .summary-card {{
                flex: 1 1 300px; 
                background-color: var(--parchment); border-radius: 8px; padding: 20px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            }}
            .card-header {{ 
                display: flex; align-items: center; border-bottom: 1px solid var(--almond-silk);
                padding-bottom: 10px; margin-bottom: 15px; 
            }}
            .activity-icon {{ font-size: 24px; margin-right: 15px; }}
            .activity-title {{ margin: 0; font-size: 1.2em; color: var(--muted-teal); font-weight: 600; }}
            
            /* Statistieken binnen de kaart */
            .stats-group {{ 
                display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 15px;
                text-align: center;
            }}
            .stat-main {{ 
                font-size: 0.9em; line-height: 1.3;
            }}
            .stat-main span {{ 
                display: block; font-size: 1.4em; font-weight: 600; color: var(--toffee-brown); 
                margin-top: 5px; 
            }}
            
            .stats-details {{ 
                padding-top: 10px; border-top: 1px dashed var(--almond-silk);
            }}
            .summary-line {{ 
                display: flex; justify-content: space-between; align-items: center;
                margin: 5px 0; font-size: 0.85em;
            }}
            .summary-icon {{ font-size: 14px; margin-right: 8px; }}
            .summary-label {{ font-weight: 400; color: var(--text-dark); }}
            .summary-value-small {{ font-weight: 600; color: var(--muted-teal); }}
            
            /* GRAFIEKEN AANPASSINGEN: Volle breedte, onder elkaar */
            .chart-full-width {{ 
                width: 100%; margin-bottom: 20px; 
                background: var(--parchment); padding: 10px; border-radius: 8px;
            }}
            /* FIX voor Plotly om 100% breedte te garanderen */
            .chart-full-width .js-plotly-plot,
            .chart-full-width .plotly-graph-div,
            .chart-full-width .svg-container {{ 
                width: 100% !important; 
            }}

            .footer-note {{
                margin-top: 20px; padding: 10px; border-top: 1px solid var(--almond-silk);
                font-size: 0.85em; color: var(--text-dark);
            }}
            
            /* Filter Styling */
            .filter-container {{
                margin: 20px 0 10px 0; display: flex; align-items: center; gap: 10px;
                font-weight: 600;
            }}
            .filter-container select {{
                padding: 8px 12px; border: 1px solid var(--muted-teal); border-radius: 5px;
                font-family: 'Oswald', sans-serif; font-size: var(--font-size-small);
                background-color: #fff;
            }}

            /* HR Privacy Styling */
            .hr-hidden {{
                filter: blur(4px);
                user-select: none;
                transition: filter 0.5s;
            }}
            .hr-reveal-button {{
                display: inline-block;
                margin-top: 10px;
                font-size: 0.8em;
                color: var(--sweet-salmon);
                cursor: pointer;
                text-decoration: underline;
            }}
            .hr-reveal-button:hover {{ color: var(--toffee-brown); }}

            /* Detail Tabel STYLING */
            .detail-table-container {{ 
                margin-top: 20px; 
            }}
            .detail-title {{ 
                color: var(--toffee-brown); font-size: 1.5em; margin-bottom: 15px; 
                border-bottom: 1px solid var(--almond-silk); padding-bottom: 5px;
            }}
            .activity-table {{
                width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.85em;
            }}
            .activity-table th {{
                background-color: var(--muted-teal); color: #fff; padding: 10px; text-align: left;
                position: sticky; top: 0; z-index: 10;
            }}
            .activity-table td {{
                padding: 10px; border-bottom: 1px solid var(--almond-silk);
            }}
            .activity-table tr:nth-child(even) {{
                background-color: var(--parchment);
            }}
            .activity-table tr:hover {{
                background-color: var(--almond-silk); cursor: default;
            }}
            .activity-table .num {{
                text-align: right; font-weight: 600;
            }}
            .no-data-msg {{
                color: var(--text-dark); font-style: italic; padding: 20px; text-align: center;
            }}


            /* Responsieve aanpassingen */
            @media (max-width: 900px) {{
                .activity-table th:nth-child(3), .activity-table td:nth-child(3) {{ 
                    display: none; /* Verberg 'Naam Activiteit' op kleine schermen */
                }}
            }}
            @media (max-width: 600px) {{
                .summary-card {{ flex: 1 1 100%; }}
                .stats-group {{ grid-template-columns: repeat(2, 1fr); }}
                /* Verberg meer kolommen om de tabel leesbaar te houden op kleine schermen */
                .activity-table th:nth-child(5), .activity-table td:nth-child(5),
                .activity-table th:nth-child(6), .activity-table td:nth-child(6),
                .activity-table th:nth-child(7), .activity-table td:nth-child(7),
                .activity-table th:nth-child(8), .activity-table td:nth-child(8),
                .activity-table th:nth-child(9), .activity-table td:nth-child(9) {{
                    display: none; 
                }}
                .activity-table th:nth-child(2), .activity-table td:nth-child(2), /* Toon de sport */
                .activity-table th:nth-child(4), .activity-table td:nth-child(4) {{
                    display: table-cell; /* Toon minstens Afstand en Sport */
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Sport Overzicht</h1>
            
            <div class="nav-buttons">
                {jaar_knoppen_html}
            </div>

            <div id="view-Globaal" class="jaar-sectie">
                <h2>Totaal Overzicht</h2>
                <div class="summary-container">
                    {totaal_kaarten_html}
                </div>
                
                <div class="chart-full-width">
                    {fig_sessies_per_maand.to_html(full_html=False, include_plotlyjs='cdn')}
                </div>
                <div class="chart-full-width">
                    {fig_maand.to_html(full_html=False, include_plotlyjs='cdn')}
                </div>
                
                <a href="#" onclick="revealHeartRate(event)" class="hr-reveal-button">Toon Gemiddelde Hartslag</a>
                {filter_globaal_html}
                {totaal_detail_tabel}
            </div>
            
            {jaar_secties_html}

        </div>

        <script>
            // Wachtwoord is hardcoded in de client-side code.
            const CORRECT_PASSWORD = 'jordenlore'; 

            function showView(view_id, event) {{
                const secties = document.querySelectorAll('.jaar-sectie');
                const knoppen = document.querySelectorAll('.jaar-knop');
                
                secties.forEach(sectie => {{ sectie.style.display = 'none'; }});
                knoppen.forEach(knop => {{ knop.classList.remove('active'); }});

                const actieveSectie = document.getElementById('view-' + view_id);
                if (actieveSectie) {{ actieveSectie.style.display = 'block'; }};
                
                if (event && event.currentTarget) {{ event.currentTarget.classList.add('active'); }};
                
                // Reset de filter wanneer van jaar wordt gewisseld
                const filter = document.getElementById('filter-' + view_id);
                if (filter) {{
                    filter.value = 'ALL';
                    filterDetailTabel(view_id);
                }}
            }}
            
            function filterDetailTabel(sectie_id) {{
                const filter = document.getElementById('filter-' + sectie_id);
                const selected_activity = filter.value;
                
                const sectie = document.getElementById('view-' + sectie_id);
                if (!sectie) return;

                const table = sectie.querySelector('.activity-table');
                if (!table) return;

                const rows = table.querySelectorAll('tbody tr');

                rows.forEach(row => {{
                    const row_activity = row.getAttribute('data-activity-type');
                    
                    if (selected_activity === 'ALL' || row_activity === selected_activity) {{
                        row.style.display = ''; 
                    }} else {{
                        row.style.display = 'none'; 
                    }}
                }});
            }}

            function revealHeartRate(event) {{
                if (event) {{
                    event.preventDefault(); // Voorkom dat de link naar de top van de pagina springt
                }}

                // Check of de hartslag al getoond wordt
                const hiddenElements = document.querySelectorAll('.hr-hidden');
                if (hiddenElements.length === 0) {{
                    alert("Hartslag is al zichtbaar.");
                    return;
                }}

                const password = prompt("Voer het wachtwoord in om de hartslaggegevens te tonen:");

                if (password === CORRECT_PASSWORD) {{
                    // Verwijder de blur class van alle verborgen elementen in het hele dashboard
                    hiddenElements.forEach(el => {{
                        el.classList.remove('hr-hidden');
                    }});
                    // Verberg de knop nu de data getoond is
                    document.querySelectorAll('.hr-reveal-button').forEach(btn => {{
                        btn.style.display = 'none';
                    }});
                }} else if (password !== null) {{
                    alert("Onjuist wachtwoord.");
                }}
            }}


            // Activeer de 'Totaal Overzicht' knop en de bijbehorende weergave bij het laden
            document.addEventListener('DOMContentLoaded', () => {{
                const globaleSectie = document.getElementById('view-Globaal');
                if (globaleSectie) {{ globaleSectie.style.display = 'block'; }};
                
                const globaleKnop = document.querySelector('[data-view="Globaal"]');
                if (globaleKnop) {{ globaleKnop.classList.add('active'); }};
            }});
        </script>
    </body>
    </html>
    """
    
    with open(html_output, 'w', encoding='utf-8') as f:
        f.write(dashboard_html)

    print(f"\n✅ Het finale dashboard is succesvol gegenereerd in '{html_output}' met alle gevraagde verbeteringen!")


# Directe aanroep van de functie om de uitvoering te garanderen
genereer_html_dashboard()