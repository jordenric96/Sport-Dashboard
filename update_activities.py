import requests
import pandas as pd
import os
import time

# --- CONFIGURATIE ---
CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('STRAVA_REFRESH_TOKEN')

AUTH_URL = "https://www.strava.com/oauth/token"
ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
ATHLETE_URL = "https://www.strava.com/api/v3/athlete"

def get_access_token():
    payload = {'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'refresh_token': REFRESH_TOKEN, 'grant_type': 'refresh_token', 'f': 'json'}
    try:
        res = requests.post(AUTH_URL, data=payload, verify=False)
        res.raise_for_status()
        return res.json()['access_token']
    except Exception as e:
        print(f"❌ Fout bij token: {e}")
        exit(1)

def get_gear_map(token):
    """Haalt profiel op om Gear ID (b1234) om te zetten naar Naam (Canyon)"""
    headers = {'Authorization': f"Bearer {token}"}
    gear_map = {}
    try:
        r = requests.get(ATHLETE_URL, headers=headers)
        data = r.json()
        for bike in data.get('bikes', []): gear_map[bike['id']] = bike['name']
        for shoe in data.get('shoes', []): gear_map[shoe['id']] = shoe['name']
        print(f"✅ Materiaal lijst opgehaald: {len(gear_map)} items gevonden.")
    except:
        print("⚠️ Kon materiaal namen niet ophalen, we gebruiken ID's.")
    return gear_map

def translate_type(strava_type):
    mapping = {'Run': 'Hardlopen', 'Ride': 'Fietsrit', 'VirtualRide': 'Virtuele fietsrit', 'Walk': 'Wandelen', 'Swim': 'Zwemmen', 'WeightTraining': 'Krachttraining', 'Workout': 'Training', 'Hike': 'Wandelen', 'GravelRide': 'Fietsrit', 'MountainBikeRide': 'Fietsrit', 'E-BikeRide': 'Fietsrit', 'Velomobile': 'Fietsrit'}
    return mapping.get(strava_type, strava_type)

def process_data():
    token = get_access_token()
    headers = {'Authorization': f"Bearer {token}"}
    
    # 1. Haal gear map op
    gear_map = get_gear_map(token)
    
    # 2. Haal activiteiten
    all_activities = []
    page = 1
    print("📥 Bezig met ophalen historie (limit 1500)...")
    
    while True:
        r = requests.get(f"{ACTIVITIES_URL}?per_page=200&page={page}", headers=headers)
        data = r.json()
        if not data: break
        all_activities.extend(data)
        print(f"   - Pagina {page}.. Totaal: {len(all_activities)}")
        if len(all_activities) >= 1500: break
        page += 1

    clean_data = []
    for a in all_activities:
        dt = a['start_date_local'].replace('T', ' ').replace('Z', '')
        gear_id = a.get('gear_id')
        gear_name = gear_map.get(gear_id, gear_id) if gear_id else "" # Vertaal ID naar Naam
        
        clean_data.append({
            'Datum van activiteit': dt,
            'Naam activiteit': a['name'],
            'Activiteitstype': translate_type(a['type']),
            'Afstand': a['distance'] / 1000,
            'Beweegtijd': a['moving_time'],
            'Gemiddelde snelheid': a['average_speed'] * 3.6,
            'Gemiddelde hartslag': a.get('average_heartrate', ''),
            'Gemiddeld wattage': a.get('average_watts', ''), # WATTAGE TOEGEVOEGD
            'Uitrusting voor activiteit': gear_name
        })

    df = pd.DataFrame(clean_data)
    df.to_csv('activities.csv', index=False)
    print(f"💾 Klaar! {len(df)} activiteiten met namen en wattages opgeslagen.")

if __name__ == "__main__":
    if not CLIENT_ID: print("❌ Geen API keys.")
    else: process_data()
