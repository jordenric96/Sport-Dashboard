import requests
import pandas as pd
import os
import time
from datetime import datetime

# --- CONFIGURATIE ---
CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('STRAVA_REFRESH_TOKEN')

AUTH_URL = "https://www.strava.com/oauth/token"
ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
ATHLETE_URL = "https://www.strava.com/api/v3/athlete"
CSV_FILE = 'activities.csv'

def get_access_token():
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type': 'refresh_token',
        'f': 'json'
    }
    try:
        res = requests.post(AUTH_URL, data=payload, verify=False)
        res.raise_for_status()
        return res.json()['access_token']
    except Exception as e:
        print(f"❌ Fout bij token: {e}")
        exit(1)

def get_gear_map(token):
    headers = {'Authorization': f"Bearer {token}"}
    gear_map = {}
    try:
        r = requests.get(ATHLETE_URL, headers=headers)
        data = r.json()
        for bike in data.get('bikes', []): gear_map[bike['id']] = bike['name']
        for shoe in data.get('shoes', []): gear_map[shoe['id']] = shoe['name']
    except: pass
    return gear_map

def translate_type(strava_type):
    mapping = {
        'Run': 'Hardlopen', 'Ride': 'Fietsrit', 'VirtualRide': 'Virtuele fietsrit', 
        'Walk': 'Wandelen', 'Swim': 'Zwemmen', 'WeightTraining': 'Krachttraining', 
        'Workout': 'Training', 'Hike': 'Wandelen', 'GravelRide': 'Fietsrit', 
        'MountainBikeRide': 'Fietsrit', 'E-BikeRide': 'Fietsrit', 'Velomobile': 'Fietsrit'
    }
    return mapping.get(strava_type, strava_type)

def get_last_timestamp():
    """Zoekt de datum van de laatste activiteit in de CSV"""
    if not os.path.exists(CSV_FILE):
        return None
    
    try:
        df = pd.read_csv(CSV_FILE)
        if df.empty or 'Datum van activiteit' not in df.columns: return None
        
        # Probeer de datum te parsen. Het format in CSV is vaak "2025-01-01 12:00:00"
        last_date_str = df['Datum van activiteit'].max()
        dt_obj = pd.to_datetime(last_date_str)
        return int(dt_obj.timestamp())
    except:
        return None

def process_data():
    token = get_access_token()
    headers = {'Authorization': f"Bearer {token}"}
    gear_map = get_gear_map(token)
    
    # Bepaal vanaf wanneer we moeten downloaden
    last_timestamp = get_last_timestamp()
    
    params = {'per_page': 200, 'page': 1}
    if last_timestamp:
        print(f"🔄 Bestaande data gevonden. Ophalen vanaf timestamp: {last_timestamp}")
        params['after'] = last_timestamp
    else:
        print("🆕 Geen data gevonden (of geforceerd). Alles ophalen (max 2000).")
    
    new_activities = []
    
    while True:
        r = requests.get(ACTIVITIES_URL, headers=headers, params=params)
        data = r.json()
        
        if not data: break
        
        new_activities.extend(data)
        print(f"   - {len(data)} nieuwe items opgehaald...")
        
        if len(data) < 200: break # Laatste pagina bereikt
        params['page'] += 1
        
        # Veiligheid: stop na 10 pagina's om loops te voorkomen
        if params['page'] > 10: break

    if not new_activities:
        print("✅ Geen nieuwe activiteiten gevonden. Alles is up-to-date.")
        return

    print(f"📥 Totaal {len(new_activities)} nieuwe activiteiten verwerken...")

    clean_data = []
    for a in new_activities:
        dt = a['start_date_local'].replace('T', ' ').replace('Z', '')
        gear_id = a.get('gear_id')
        gear_name = gear_map.get(gear_id, gear_id) if gear_id else ""
        
        clean_data.append({
            'Datum van activiteit': dt,
            'Naam activiteit': a['name'],
            'Activiteitstype': translate_type(a['type']),
            'Afstand': a['distance'] / 1000,
            'Beweegtijd': a['moving_time'],
            'Gemiddelde snelheid': a['average_speed'] * 3.6,
            'Gemiddelde hartslag': a.get('average_heartrate', ''),
            'Gemiddeld wattage': a.get('average_watts', ''),
            'Uitrusting voor activiteit': gear_name
        })

    df_new = pd.DataFrame(clean_data)
    
    if os.path.exists(CSV_FILE) and last_timestamp:
        # Samenvoegen met bestaande data
        df_old = pd.read_csv(CSV_FILE)
        df_total = pd.concat([df_new, df_old])
        # Dubbele verwijderen op basis van datum en naam (voor zekerheid)
        df_total = df_total.drop_duplicates(subset=['Datum van activiteit', 'Naam activiteit'])
    else:
        df_total = df_new

    # Sorteren aflopend (nieuwste eerst)
    df_total['temp_sort'] = pd.to_datetime(df_total['Datum van activiteit'], errors='coerce')
    df_total = df_total.sort_values(by='temp_sort', ascending=False).drop(columns=['temp_sort'])
    
    df_total.to_csv(CSV_FILE, index=False)
    print(f"💾 Succes! activities.csv bijgewerkt. Totaal nu: {len(df_total)} regels.")

if __name__ == "__main__":
    if not CLIENT_ID: print("❌ Geen API keys.")
    else: process_data()
