import pandas as pd
import numpy as np
import plotly.express as px
import plotly.io as pio

# Definieer de kleuren die in de Plotly grafieken gebruikt moeten worden
# NIEUW PALET
CUSTOM_COLORS = [
    '#ed254e',  # --watermelon (Rood/Roze)
    '#f38155',  # --coral-glow (Oranje/Zalm)
    '#f9dc5c',  # --royal-gold (Geel/Goud)
    '#c2eabd',  # --tea-green (Licht Groen)
    '#011936',  # --prussian-blue (Donker Blauw)
]
COLOR_CUMULATIVE = '#ed254e' # Gebruik Watermelon voor de highlight

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

# Helperfunctie voor activiteitssymbolen (AANGEPAST)
def get_activity_icon(activity_type):
    activity_type = str(activity_type)
    if 'Zwemmen' in activity_type:
        return '🏊' # Zwembad/Zwemmen symbool
    elif 'Virtuele Fietsrit' in activity_type:
        return '⛰️' # Berglandschap voor virtuele rit
    elif 'Fiets' in activity_type:
        return '🚴'
    elif 'Training' in activity_type:
        return '🎾'
    elif 'Wandel' in activity_type or 'Hike' in activity_type:
        return '🚶'
    elif 'Hardloop' in activity_type:
        return '🏃'
    else:
        return '✨'
        
# Functie om de gedetailleerde lijst in HTML te genereren
def genereer_detail_tabel_html(df_data):
    if df_data.empty:
        return '<p class="no-data-msg">Geen activiteiten gevonden voor dit overzicht.</p>'

    # Sorteer op datum, OUDSTE BOVENAAN
    df_data = df_data.sort_values(by='Datum', ascending=True) 
    
    html_rows = []
    
    # Aangepaste classes voor responsiviteit
    header = """
        <thead>
            <tr>
                <th>Datum</th>
                <th>Activiteitstype</th>
                <th class="col-hide-900">Naam Activiteit</th> 
                <th>Afstand (km)</th>
                <th class="col-hide-600">Tijd</th>
                <th class="col-hide-600">Gem. Snelheid (km/u)</th>
                <th class="col-hide-750">Stijging (m)</th>
                <th class="col-hide-800">Gem. Hartslag (bpm)</th> 
                <th class="col-hide-800">Calorieën</th>
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
        
        # Data-rijen met responsieve classes
        html_row = f"""
            <tr data-activity-type="{activiteit_type_str}"> 
                <td>{datum_str}</td>
                <td>{activiteit_type_str}</td>
                <td class="col-hide-900">{activiteit_naam}</td>
                <td class="num">{afstand_str}</td>
                <td class="col-hide-600">{tijd_str}</td>
                <td class="num col-hide-600">{snelheid_str}</td>
                <td class="num col-hide-750">{stijging_str}</td> 
                <td class="num hr-hidden col-hide-800">{hartslag_str}</td> 
                <td class="num col-hide-800">{calorieen_str}</td>
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
    <div class="filter-container" id="filter-container-{sectie_id}">
        <label for="filter-{sectie_id}">Filter op Sport:</label>
        <select id="filter-{sectie_id}" onchange="filterDetailTabel('{sectie_id}')">
            {''.join(options)}
        </select>
    </div>
    """

# Nieuwe functie om de GRAND TOTAL kaart voor een jaar of Totaal te genereren (AANGEPAST)
def genereer_totaal_jaar_card_html(row, titel="Jaar Totaal Overzicht"):
    afstand_totaal = f"{row['Totaal_Afstand_km']:.1f} km"
    tijd_totaal = format_time(row['Totaal_Tijd_sec'])
    stijging_totaal = f"{row['Totaal_Stijging_m']:.0f} m"
    # FIX: Cast naar int() om ValueError te voorkomen
    aantal = f"{int(row['Aantal_Activiteiten']):d} sessies" 
    
    avg_hr = row.get('Gemiddelde_Hartslag', np.nan)
    avg_hr_html = f'<p class="stat-main-large"><span>Gem. Hartslag:</span> <span class="hr-hidden">{avg_hr:.0f} bpm</span></p>' if pd.notna(avg_hr) and avg_hr > 0 else ''

    html = f"""
    <div class="summary-card-total">
        <h3 class="activity-title-total">{titel}</h3>
        <div class="stats-group-large">
            <p class="stat-main-large"><span>Sessies:</span> {aantal}</p>
            <p class="stat-main-large"><span>Afstand:</span> {afstand_totaal}</p>
            <p class="stat-main-large"><span>Tijd:</span> {tijd_totaal}</p>
            <p class="stat-main-large"><span>Stijging:</span> {stijging_totaal}</p>
            {avg_hr_html}
        </div>
    </div>
    """
    return html

# Functie om de HTML-statistiekenkaartjes voor individuele sporten te genereren (AANGEPAST)
def genereer_summary_card_html(row, df_clean, is_totaal=False):
    activiteit = row['Activiteitstype']
    icon = get_activity_icon(activiteit)
    
    # Gebruik Totaal_Stijging_m (de geaggregeerde kolomnaam)
    afstand_totaal = f"{row['Totaal_Afstand_km']:.1f} km"
    tijd_totaal = format_time(row['Totaal_Tijd_sec'])
    # FIX: Gebruik de geaggregeerde kolomnaam 'Totaal_Stijging_m' i.p.v. 'Totale_Stijging_m'
    stijging_totaal = f"{row['Totaal_Stijging_m']:.0f} m"
    # FIX: Cast naar int() om ValueError te voorkomen
    aantal = f"{int(row['Aantal_Activiteiten']):d}" 
    
    max_dist_row = row.get('Max_Afstand_km', np.nan)
    max_avg_speed_row = row.get('Max_Gemiddelde_Snelheid_km_u', np.nan) 
    avg_speed = row.get('Gemiddelde_Snelheid_km_u', np.nan)
    
    stats_html = ""
    
    # NEW: Prominent average HR display in details
    avg_hr = row.get('Gemiddelde_Hartslag', np.nan)
    avg_hr_html = f'<p class="summary-line primary-detail"><span class="summary-icon">❤️</span> <span class="summary-label">Gem. Hartslag:</span> <span class="summary-value-small hr-hidden">{avg_hr:.0f} bpm</span></p>' if pd.notna(avg_hr) and avg_hr > 0 else ''
    
    # Voeg HR toe aan de details
    stats_html += avg_hr_html
            
    if pd.notna(avg_speed) and avg_speed > 0:
        stats_html += f'<p class="summary-line"><span class="summary-icon">⏱️</span> <span class="summary-label">Gem. Snelheid:</span> <span class="summary-value-small">{avg_speed:.1f} km/u</span></p>'
            
    # Labels voor langste/snelste rit/loop/wandeling
    is_ride = 'Fiets' in activiteit or 'Virtuele Fietsrit' in activiteit
    is_run = 'Hardloop' in activiteit
    is_walk = 'Wandel' in activiteit or 'Hike' in activiteit
    
    if pd.notna(max_dist_row) and max_dist_row > 0:
        if is_ride:
            label = 'Langste Rit'
        elif is_run:
            label = 'Langste Loop'
        elif is_walk:
            label = 'Langste Wandeling' # AANGEPAST
        else:
            label = 'Max. Afstand'
        stats_html += f'<p class="summary-line"><span class="summary-icon">🗺️</span> <span class="summary-label">{label}:</span> <span class="summary-value-small">{max_dist_row:.1f} km</span></p>'
        
    if pd.notna(max_avg_speed_row) and max_avg_speed_row > 0:
        if is_ride:
            label = 'Snelste Gem. Rit' # AANGEPAST
        elif is_run:
            label = 'Snelste Gem. Loop'
        elif is_walk:
            label = 'Snelste Gem. Wandeling' # AANGEPAST
        else:
            label = 'Max. Gem. Snelheid'
        stats_html += f'<p class="summary-line"><span class="summary-icon">⚡</span> <span class="summary-label">{label}:</span> <span class="summary-value-small">{max_avg_speed_row:.1f} km/u</span></p>'
            
    # Deze logica had df_clean nodig, wat is opgelost door het door te geven.
    if is_totaal and 'Training' in activiteit:
        max_gewicht = df_clean[df_clean['Activiteitstype'].str.contains('Training', na=False)]['Totaal_Geheven_Gewicht_kg'].max()
        if pd.notna(max_gewicht) and max_gewicht > 0:
            stats_html += f'<p class="summary-line"><span class="summary-icon">🏋️</span> <span class="summary-label">Max. Gewicht:</span> <span class="summary-value-small">{max_gewicht:,.0f} kg</span></p>'

    # Voorwaardelijke weergave van de hoofdstatistieken (AANGEPAST)
    main_stats_html = f"""
        <p class="stat-main"><span>Tijd:</span> {tijd_totaal}</p>
    """
    
    # Alleen afstand tonen als het geen Training is
    if 'Training' not in activiteit:
        main_stats_html += f'<p class="stat-main"><span>Afstand:</span> {afstand_totaal}</p>'
    
    # Alleen stijging tonen als het geen Training EN geen Zwemmen is
    if 'Training' not in activiteit and 'Zwemmen' not in activiteit:
        # FIX: Gebruik de geaggregeerde kolomnaam
        main_stats_html += f'<p class="stat-main"><span>Stijging:</span> {stijging_totaal}</p>'
    
    # De layout voor zwemmen/training wordt nu flexibel. We laten de lege kolommen weg.
    
    html = f"""
    <div class="summary-card" data-type="{activiteit}">
        <div class="card-header">
            <span class="activity-icon">{icon}</span>
            <h3 class="activity-title">{activiteit} ({aantal}x)</h3>
        </div>
        <div class="stats-group">
            {main_stats_html}
        </div>
        <div class="stats-details">
            {stats_html}
        </div>
    </div>
    """
    return html


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
    
    # --- Filter om alle sessies mee te tellen ---
    df_clean = df_clean[df_clean['Activiteitstype'].notna()].copy() 

    # LET OP: df_clean bevat nu ALLE sporten voor kaarten en tabellen.
    print("✅ Data opgeschoond en voorbewerkt.")
    
    # NIEUWE STAP: Maak een gefilterde set voor de globale grafieken (Fietsen, Lopen, Wandelen)
    ACTIVITEITEN_KEUZE = ['Fiets', 'Hardloop', 'Wandel', 'Hike']
    filter_patroon = '|'.join(ACTIVITEITEN_KEUZE)
    
    df_charts = df_clean[
        df_clean['Activiteitstype'].str.contains(filter_patroon, case=False, na=False)
    ].copy()
    
    print("✅ Afzonderlijke dataset (df_charts) aangemaakt voor de twee globale grafieken (Fietsen/Lopen/Wandelen).")


    # --- Gegevensaggregatie ---

    df_clean['Jaar_Maand_Period'] = df_clean['Datum'].dt.to_period('M')

    # Bepaal de periode range voor de zero-filling
    min_date = df_clean['Datum'].min().to_period('M')
    max_date = df_clean['Datum'].max().to_period('M')
    
    # Full periods are needed for the per-year views (even if they now only contain the filtered subset)
    full_periods = pd.period_range(start=min_date, end=max_date, freq='M')
    unieke_activiteiten_na_filter = df_clean['Activiteitstype'].unique()
    full_index_sports = pd.MultiIndex.from_product([full_periods, unieke_activiteiten_na_filter], names=['Jaar_Maand_Period', 'Activiteitstype'])


    # 1. Aggregatie Sessions (voor sessions graph) - MET ZERO FILLING (Nodig voor jaarsecties)
    sessions_raw = df_clean.groupby(['Jaar_Maand_Period', 'Activiteitstype']).size().rename('Aantal_Activiteiten')
    agg_sessies_maand = sessions_raw.reindex(full_index_sports, fill_value=0).reset_index()
    agg_sessies_maand['Jaar'] = agg_sessies_maand['Jaar_Maand_Period'].dt.year
    agg_sessies_maand['Maand'] = agg_sessies_maand['Jaar_Maand_Period'].dt.month
    agg_sessies_maand['Jaar_Maand'] = agg_sessies_maand['Jaar'].astype(str) + '-' + agg_sessies_maand['Maand'].astype(str).str.zfill(2)
    
    # 2. Aggregatie Afstand (for distance graph) - MET ZERO FILLING (Nodig voor jaarsecties)
    distance_raw = df_clean.groupby(['Jaar_Maand_Period', 'Activiteitstype'])['Afstand_km'].sum().rename('Afstand_km')
    agg_maand_base = distance_raw.reindex(full_index_sports, fill_value=0).reset_index()
    
    # OPGELOST: Voeg 'Jaar', 'Maand', en 'Jaar_Maand' kolommen toe aan agg_maand_base
    agg_maand_base['Jaar'] = agg_maand_base['Jaar_Maand_Period'].dt.year
    agg_maand_base['Maand'] = agg_maand_base['Jaar_Maand_Period'].dt.month
    agg_maand_base['Jaar_Maand'] = agg_maand_base['Jaar'].astype(str) + '-' + agg_maand_base['Maand'].astype(str).str.zfill(2)
    
    # Sum over all sports for total distance per month (NOT USED ANYMORE FOR GLOBAL, but kept for consistency)
    agg_maand = agg_maand_base.groupby('Jaar_Maand_Period')['Afstand_km'].sum().rename('Afstand_km').reset_index()
    agg_maand['Jaar'] = agg_maand['Jaar_Maand_Period'].dt.year
    agg_maand['Maand'] = agg_maand['Jaar_Maand_Period'].dt.month
    agg_maand['Jaar_Maand'] = agg_maand['Jaar'].astype(str) + '-' + agg_maand['Maand'].astype(str).str.zfill(2)
    
    # Merge de maandnamen voor uniformiteit in plotten van het totaal overzicht
    agg_maand['MaandNaam_Jaar'] = agg_maand['Maand'].apply(lambda x: pd.to_datetime(str(x), format='%m').strftime('%b')) + ' ' + agg_maand['Jaar'].astype(str)
    agg_sessies_maand['MaandNaam_Jaar'] = agg_sessies_maand['Maand'].apply(lambda x: pd.to_datetime(str(x), format='%m').strftime('%b')) + ' ' + agg_sessies_maand['Jaar'].astype(str)

    # NIEUWE AGGREGATIES VOOR DE GLOBALE JAARGRAFIEKEN (Gebruiken df_charts)
    
    # 3. Jaarlijkse aggregatie van sessies (voor globale staafgrafiek)
    agg_sessies_jaar = df_charts.groupby(['Jaar', 'Activiteitstype']).size().rename('Aantal_Activiteiten').reset_index()
    
    # 4. Jaarlijkse Afstand aggregatie (voor globale staafgrafiek, opgesplitst per sport)
    agg_afstand_jaar_stacked = df_charts.groupby(['Jaar', 'Activiteitstype'])['Afstand_km'].sum().rename('Afstand_km').reset_index()

    # Aggregeren per jaar en activiteitstype (voor summary cards per jaar) (Gebruikt df_clean)
    agg_jaar = df_clean.groupby(['Jaar', 'Activiteitstype']).agg(
        Totaal_Afstand_km=('Afstand_km', 'sum'),
        Totaal_Tijd_sec=('Beweegtijd_sec', 'sum'),
        Totaal_Stijging_m=('Totale_Stijging_m', 'sum'),
        Totaal_Calorieen=('Calorieen', 'sum'),
        Aantal_Activiteiten=('Activiteitstype', 'size'),
        Gemiddelde_Snelheid_km_u=('Gemiddelde_Snelheid_km_u', lambda x: x[df_clean.loc[x.index, 'Afstand_km'] > 0].mean()),
        Gemiddelde_Hartslag=('Gemiddelde_Hartslag', 'mean'), # Toegevoegd voor kaartjes
    ).reset_index()
    
    agg_jaar['Gemiddelde_Tijd_sec'] = agg_jaar['Totaal_Tijd_sec'] / agg_jaar['Aantal_Activiteiten']
    
    # Bepaal de max stats per jaar
    max_stats = df_clean.groupby(['Jaar', 'Activiteitstype']).agg(
        Max_Afstand_km=('Afstand_km', 'max'),
        # Max. gemiddelde snelheid van een sessie
        Max_Gemiddelde_Snelheid_km_u=('Gemiddelde_Snelheid_km_u', 'max'),
    ).reset_index()
    
    agg_jaar = agg_jaar.merge(max_stats, on=['Jaar', 'Activiteitstype'], how='left')

    # Aggregatie voor TOTAAL OVERZICHT KAART PER JAAR
    agg_jaar_totaal = df_clean.groupby(['Jaar']).agg(
        Totaal_Afstand_km=('Afstand_km', 'sum'),
        Totaal_Tijd_sec=('Beweegtijd_sec', 'sum'),
        Totaal_Stijging_m=('Totale_Stijging_m', 'sum'),
        Totaal_Calorieen=('Calorieen', 'sum'),
        Aantal_Activiteiten=('Activiteitstype', 'size'),
        Gemiddelde_Hartslag=('Gemiddelde_Hartslag', 'mean'),
    ).reset_index()
    
    # OPGELOST: Berekenen van de zwaarste workout voor Totaal Geheven Gewicht (Moet hier bovenaan staan)
    agg_jaar_gewicht = df_clean[df_clean['Totaal_Geheven_Gewicht_kg'].notna() & (df_clean['Totaal_Geheven_Gewicht_kg'] > 0)].groupby('Jaar')['Totaal_Geheven_Gewicht_kg'].max().reset_index().rename(columns={'Totaal_Geheven_Gewicht_kg': 'Max_Gewicht'})
    
    # Aggregeren van alle data over de tijd (globaal overzicht) (Gebruikt df_clean)
    agg_totaal = df_clean.groupby('Activiteitstype').agg(
        Totaal_Afstand_km=('Afstand_km', 'sum'), 
        Totaal_Tijd_sec=('Beweegtijd_sec', 'sum'),
        Totaal_Stijging_m=('Totale_Stijging_m', 'sum'),
        Totaal_Calorieen=('Calorieen', 'sum'),
        Aantal_Activiteiten=('Activiteitstype', 'size'),
        Gemiddelde_Snelheid_km_u=('Gemiddelde_Snelheid_km_u', lambda x: x[df_clean.loc[x.index, 'Afstand_km'] > 0].mean()),
        Gemiddelde_Hartslag=('Gemiddelde_Hartslag', 'mean'), # Toegevoegd voor kaartjes
    ).reset_index()
    
    agg_totaal['Gemiddelde_Tijd_sec'] = agg_totaal['Totaal_Tijd_sec'] / agg_totaal['Aantal_Activiteiten']

    # Bepaal de max stats in het totale overzicht
    max_stats_totaal = df_clean.groupby('Activiteitstype').agg(
        Max_Afstand_km=('Afstand_km', 'max'),
        Max_Gemiddelde_Snelheid_km_u=('Gemiddelde_Snelheid_km_u', 'max')
    ).reset_index()
    
    agg_totaal = agg_totaal.merge(max_stats_totaal, on='Activiteitstype', how='left')
    
    # NIEUWE aggregatie voor de GRAND TOTAL CARD over alle jaren (Robuuste methode) (Gebruikt df_clean)
    agg_alle_jaren = pd.DataFrame({
        'Totaal_Afstand_km': [df_clean['Afstand_km'].sum()],
        'Totaal_Tijd_sec': [df_clean['Beweegtijd_sec'].sum()],
        'Totaal_Stijging_m': [df_clean['Totale_Stijging_m'].sum()],
        'Aantal_Activiteiten': [df_clean.shape[0]], 
        'Gemiddelde_Hartslag': [df_clean['Gemiddelde_Hartslag'].mean()],
    })
    
    unieke_activiteiten = sorted(df_clean['Activiteitstype'].unique())
    
    print("✅ Gegevens succesvol geaggregeerd.")

    # --- Plotly Grafieken Genereren (Globaal) ---

    # 1. Sessions per Year per Sport (NIEUW: Gebruikt df_charts)
    fig_sessies_per_jaar = px.bar(agg_sessies_jaar, 
                       x='Jaar', 
                       y='Aantal_Activiteiten', 
                       color='Activiteitstype', 
                       title='Totaal Aantal Sessies per Jaar (Fietsen, Lopen, Wandelen)',
                       color_discrete_sequence=CUSTOM_COLORS,
                       text='Aantal_Activiteiten')
    fig_sessies_per_jaar.update_layout(
        xaxis_title="Jaar", 
        yaxis_title="Totaal Aantal Sessies", 
        # FIX: Forceer de volgorde van de categorische as naar oplopend (2024 vóór 2025)
        xaxis={'type': 'category', 'categoryorder': 'category ascending'}, 
        # AANGEPAST: Vergrote bovenmarge om ruimte te maken voor de horizontale legende
        margin=dict(t=90, b=20, l=20, r=20),
        legend_title_text='Sport',
        # Legende horizontaal bovenaan
        legend_orientation="h",
        legend_yanchor="bottom",
        legend_y=1.02,
        legend_xanchor="left",
        legend_x=0
    )
    fig_sessies_per_jaar.update_traces(textposition='inside', marker_line_width=0)


    # 2. Distance per Year per Sport (NIEUW: Gebruikt df_charts)
    fig_afstand_per_jaar = px.bar(agg_afstand_jaar_stacked, 
                       x='Jaar', 
                       y='Afstand_km', 
                       color='Activiteitstype', 
                       title='Totale Afstand per Jaar (Fietsen, Lopen, Wandelen)',
                       color_discrete_sequence=CUSTOM_COLORS,
                       text=agg_afstand_jaar_stacked['Afstand_km'].apply(lambda x: f'{x:.0f}')) # Afstand afgerond
    fig_afstand_per_jaar.update_layout(
        xaxis_title="Jaar", 
        yaxis_title="Totale Afstand (km)", 
        # FIX: Forceer de volgorde van de categorische as naar oplopend (2024 vóór 2025)
        xaxis={'type': 'category', 'categoryorder': 'category ascending'}, 
        # AANGEPAST: Vergrote bovenmarge om ruimte te maken voor de horizontale legende
        margin=dict(t=90, b=20, l=20, r=20),
        legend_title_text='Sport',
        # Legende horizontaal bovenaan
        legend_orientation="h",
        legend_yanchor="bottom",
        legend_y=1.02,
        legend_xanchor="left",
        legend_x=0
    )
    fig_afstand_per_jaar.update_traces(textposition='inside', marker_line_width=0)
    
    print("✅ Grafieken gegenereerd.")
    
    # --- HTML Genereren ---

    # Genereer kaarten voor het totale overzicht
    totaal_kaarten_html = "".join(agg_totaal.apply(lambda row: genereer_summary_card_html(row, df_clean, is_totaal=True), axis=1).tolist())
    
    # NIEUW: Genereer de Grand Total kaart voor ALLE jaren
    totaal_alle_jaren_kaart_html = genereer_totaal_jaar_card_html(agg_alle_jaren.iloc[0], titel="Globaal Totaal Overzicht")

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
        # Data voor samenvattingskaartjes per sport
        df_jaar = agg_jaar[agg_jaar['Jaar'] == jaar].copy()
        # df_clean wordt nu meegegeven
        jaar_kaarten_html = "".join(df_jaar.apply(lambda row: genereer_summary_card_html(row, df_clean), axis=1).tolist())
        
        # Data voor Totaal Jaar Kaart
        df_total_year = agg_jaar_totaal[agg_jaar_totaal['Jaar'] == jaar].iloc[0]
        # De titel voor de jaarkaart specificeren
        totaal_jaar_kaart_html = genereer_totaal_jaar_card_html(df_total_year, titel=f"Totaal Overzicht {jaar}")
        
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
            # AANGEPAST: Vergrote bovenmarge om ruimte te maken voor de horizontale legende
            margin=dict(t=90, b=20, l=20, r=20),
            legend_title_text='Sport',
            # Legende horizontaal bovenaan
            legend_orientation="h",
            legend_yanchor="bottom",
            legend_y=1.02,
            legend_xanchor="left",
            legend_x=0
        )

        # Nieuwe Logica: Afstand per Maand OPGESPLITST per Activiteit
        df_distance_jaar = agg_maand_base[agg_maand_base['Jaar'] == jaar].copy()

        fig_jaar_afstand_per_maand = px.bar(df_distance_jaar, 
                           x='Jaar_Maand', 
                           y='Afstand_km', 
                           color='Activiteitstype', # VERANDERD: Kleur op Activiteitstype
                           title=f'Afstand per Maand en Activiteit in {jaar}',
                           color_discrete_sequence=CUSTOM_COLORS)
        fig_jaar_afstand_per_maand.update_layout(
            xaxis_title="Maand", 
            yaxis_title="Afstand (km)", 
            xaxis={'tickmode': 'array', 'tickvals': df_distance_jaar['Jaar_Maand'], 'ticktext': df_distance_jaar['Maand'].apply(lambda x: pd.to_datetime(str(x), format='%m').strftime('%b'))}, 
            # AANGEPAST: Vergrote bovenmarge om ruimte te maken voor de horizontale legende
            margin=dict(t=90, b=20, l=20, r=20),
            legend_title_text='Sport',
            # Legende horizontaal bovenaan
            legend_orientation="h",
            legend_yanchor="bottom",
            legend_y=1.02,
            legend_xanchor="left",
            legend_x=0
        )
        
        # Max. Gewicht voor dit jaar (Robuuste logica)
        df_gewicht_jaar = agg_jaar_gewicht[agg_jaar_gewicht['Jaar'] == jaar]
        if not df_gewicht_jaar.empty:
            max_gewicht_jaar = df_gewicht_jaar['Max_Gewicht'].iloc[0]
        else:
            max_gewicht_jaar = np.nan
            
        gewicht_html = f'<p><strong>Zwaarste workout (max. getild gewicht):</strong> {max_gewicht_jaar:,.0f} kg</p>' if pd.notna(max_gewicht_jaar) else ''
        
        # Genereer de detailtabel voor dit jaar
        df_detail_jaar = df_clean[df_clean['Jaar'] == jaar]
        filter_jaar_html = genereer_filter_html(unieke_activiteiten, str(jaar))
        jaar_detail_tabel = genereer_detail_tabel_html(df_detail_jaar)


        # FIX: Alle grafieken in jaar-secties gebruiken nu chart-full-width
        # POSITIE FIX: Filter verplaatst naar direct na H2
        jaar_secties_html += f"""
        <div id="view-{jaar}" class="jaar-sectie" style="display: none;">
            <h2>Overzicht {jaar}</h2>
            
            {filter_jaar_html}
            
            <div class="summary-container-total"> 
                {totaal_jaar_kaart_html}
            </div>
            
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
            
            <a href="#" onclick="revealHeartRate(event)" class="hr-reveal-button">❤️🔒</a>
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
                /* NIEUWE KLEUREN PALET */
                --watermelon: #ed254eff; 
                --coral-glow: #f38155ff; 
                --royal-gold: #f9dc5cff; 
                --tea-green: #c2eabdff;
                --prussian-blue: #011936ff;
                
                /* Mapping van oude variabelen naar nieuwe */
                --muted-teal: var(--prussian-blue);   /* Donker accent (H2, headers, Total Card BG) */
                --sweet-salmon: var(--watermelon);    /* Highlights (HR button, Total Card Text) */
                --toffee-brown: var(--coral-glow);    /* Primaaire accent (H1, knoppen) */
                --almond-silk: var(--royal-gold);     /* Subtiele lijnen/achtergrond accent */
                --parchment: #fbf7f4;                 /* Achtergrond (licht) */
                --text-dark: var(--prussian-blue);    /* Tekstkleur */
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
            
            /* CSS voor de nieuwe grote TOTAAL kaart */
            .summary-container-total {{ margin-bottom: 30px; }}
            .summary-card-total {{
                background-color: var(--muted-teal); color: #fff; border-radius: 8px; padding: 20px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            .activity-title-total {{ margin: 0; font-size: 1.5em; border-bottom: 1px solid #fff3; padding-bottom: 10px; margin-bottom: 15px; }}
            .stats-group-large {{
                display: flex; flex-wrap: wrap; gap: 20px;
            }}
            .stat-main-large {{ 
                font-size: 0.9em; line-height: 1.3; flex: 1 1 180px;
            }}
            .stat-main-large span {{ 
                display: block; font-size: 1.6em; font-weight: 600; color: var(--sweet-salmon); 
                margin-top: 5px; 
            }}
            
            /* Standaard Sport Kaart */
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
            /* AANGEPAST FONT SIZE */
            .stat-main {{ 
                font-size: 1em; line-height: 1.3; /* AANGEPAST van 0.9em */
            }}
            .stat-main span {{ 
                display: block; font-size: 1.5em; font-weight: 600; color: var(--toffee-brown); /* AANGEPAST van 1.4em */
                margin-top: 5px; 
            }}
            
            .stats-details {{ 
                padding-top: 10px; border-top: 1px dashed var(--almond-silk);
            }}
            .summary-line {{ 
                display: flex; justify-content: space-between; align-items: center;
                margin: 5px 0; font-size: 0.9em; /* AANGEPAST van 0.85em */
            }}
            /* Geef HR op de sportkaarten een extra prominentie */
            .stats-details .primary-detail {{
                font-size: 1em; font-weight: 600; border-bottom: 1px solid var(--almond-silk); margin-bottom: 8px;
            }}
            .stats-details .primary-detail .summary-value-small {{
                color: var(--sweet-salmon);
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
                font-size: 1.2em; /* Groter voor icoon */
                color: var(--sweet-salmon);
                cursor: pointer;
                text-decoration: none; /* Geen onderstreping voor icoon */
                font-weight: 600;
            }}
            .hr-reveal-button:hover {{ color: var(--toffee-brown); }}

            /* Detail Tabel STYLING */
            /* NIEUW: Horizontaal scrollen voor mobiel */
            .detail-table-container {{ 
                margin-top: 20px; 
                overflow-x: auto; /* Belangrijk voor scrollen op smallere schermen */
            }}
            .detail-title {{ 
                color: var(--toffee-brown); font-size: 1.5em; margin-bottom: 15px; 
                border-bottom: 1px solid var(--almond-silk); padding-bottom: 5px;
            }}
            .activity-table {{
                width: 100%; 
                min-width: 700px; /* Forceer een minimale breedte voor scrollen op mobiel */
                border-collapse: collapse; margin-top: 15px; font-size: 0.85em;
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

            /* Responsieve aanpassingen - Progressieve kolomverbergen */
            /* Belangrijk: De onderstaande media queries werken nog steeds, maar de overflow-x: auto zorgt ervoor dat de scrollbar verschijnt als ze niet allemaal verborgen zijn. */
            
            /* Prioriteit 1: Verberg Naam Activiteit op kleinere schermen dan 900px */
            .activity-table .col-hide-900 {{
                display: table-cell; 
            }}
            @media (max-width: 900px) {{
                .activity-table .col-hide-900 {{ 
                    display: none; 
                }}
            }}
            /* Prioriteit 2: Verberg Tijd, Gem. Snelheid op kleinere schermen dan 600px */
            .activity-table .col-hide-600 {{
                display: table-cell; 
            }}
            @media (max-width: 600px) {{
                .activity-table .col-hide-600 {{ 
                    display: none; 
                }}
                /* Pas de Totaal Kaart aan op kleine schermen */
                .stats-group-large {{ gap: 10px; }}
                .stat-main-large {{ flex: 1 1 100%; }}

            }}
            /* Prioriteit 3: Verberg Stijging op kleinere schermen dan 750px */
            .activity-table .col-hide-750 {{
                display: table-cell; 
            }}
            @media (max-width: 750px) {{
                .activity-table .col-hide-750 {{ 
                    display: none; 
                }}
            }}
            /* Prioriteit 4: Verberg Gem. Hartslag, Calorieën op kleinere schermen dan 800px */
            .activity-table .col-hide-800 {{
                display: table-cell; 
            }}
            @media (max-width: 800px) {{
                .activity-table .col-hide-800 {{ 
                    display: none; 
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
                
                {filter_globaal_html}
                
                <div class="summary-container-total"> 
                    {totaal_alle_jaren_kaart_html}
                </div>
                
                <div class="summary-container">
                    {totaal_kaarten_html}
                </div>
                
                <div class="chart-full-width">
                    {fig_sessies_per_jaar.to_html(full_html=False, include_plotlyjs='cdn')}
                </div>
                <div class="chart-full-width">
                    {fig_afstand_per_jaar.to_html(full_html=False, include_plotlyjs='cdn')}
                </div>
                
                <a href="#" onclick="revealHeartRate(event)" class="hr-reveal-button">❤️🔒</a>
                {totaal_detail_tabel}
            </div>
            
            {jaar_secties_html}

        </div>

        <script>
            // Wachtwoord blijft behouden zoals gevraagd
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

    print(f"\n✅ Het finale, geoptimaliseerde dashboard is succesvol gegenereerd in '{html_output}'.")


# Directe aanroep van de functie om de uitvoering te garanderen
genereer_html_dashboard()