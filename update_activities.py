import requests
import pandas as pd
from datetime import datetime
import os
import sys
import time

# --- CONFIGURATIE ---
CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('STRAVA_REFRESH_TOKEN')
CSV_FILE = 'activities.csv'

# Vertalingen
TYPE_MAPPING = {
    'Ride': 'Fietsrit', 'VirtualRide': 'Virtuele fietsrit',
    'Run': 'Hardloopsessie', 'Walk': 'Wandeling', 'Hike': 'Hike',
    'WeightTraining': 'Padel', 'Workout': 'Padel', 'Swim': 'Zwemmen',
    'GravelRide': 'Fietsrit', 'TrailRun': 'Hardloopsessie'
}

def get_access_token():
    if not CLIENT_ID or not CLIENT_SECRET or not REFRESH_TOKEN:
        print("❌ FOUT: Secrets ontbreken.")
        sys.exit(1)
    
    url = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN, 'grant_type': 'refresh_token'
    }
    try:
        r = requests.post(url, data=payload)
        r.raise_for_status()
        return r.json()['access_token']
    except Exception as e:
        print(f"❌ Token error: {e}")
        sys.exit(1)

def get_gear_map(token):
    """Haalt je profiel op om Gear ID's (b1234) om te zetten naar Namen (Canyon)"""
    url = "https://www.strava.com/api/v3/athlete"
    headers = {'Authorization': f"Bearer {token}"}
    gear_map = {}
    
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
        
        # Fietsen mappen
        for bike in data.get('bikes', []):
            gear_map[bike['id']] = bike['name']
        
        # Schoenen mappen
        for shoe in data.get('shoes', []):
            gear_map[shoe['id']] = shoe['name']
            
        print(f"✅ Materiaal opgehaald: {len(gear_map)} items gevonden.")
    except Exception as e:
        print(f"⚠️ Kon materiaal niet ophalen: {e}")
    
    return gear_map

def format_date(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
    maanden = {1:'jan', 2:'feb', 3:'mrt', 4:'apr', 5:'mei', 6:'jun', 
               7:'jul', 8:'aug', 9:'sep', 10:'okt', 11:'nov', 12:'dec'}
    return f"{dt.day} {maanden[dt.month]} {dt.year}, {dt.strftime('%H:%M:%S')}"

def update_csv():
    print("🔄 Start Strava Update (Met Materiaal)...")
    token = get_access_token()
    
    # 1. Haal vertaallijst voor materiaal op
    gear_map = get_gear_map(token)
    
    # 2. Huidige CSV inlezen
    existing_ids = set()
    df_existing = pd.DataFrame()
    
    if os.path.exists(CSV_FILE):
        try:
            df_existing = pd.read_csv(CSV_FILE)
            if 'Activiteits-ID' in df_existing.columns:
                existing_ids = set(df_existing['Activiteits-ID'].astype(str))
        except:
            print("⚠️ Kon CSV niet lezen, start nieuw.")

    # 3. Data ophalen (200 items om zeker te zijn dat we materiaal vullen)
    headers = {'Authorization': f"Bearer {token}"}
    url = "https://www.strava.com/api/v3/athlete/activities?per_page=200"
    
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        activities = r.json()
    except Exception as e:
        print(f"❌ Fout bij activities: {e}")
        sys.exit(1)

    new_rows = []
    
    for act in activities:
        act_id = str(act['id'])
        
        # Check of we deze moeten updaten
        # TIP: Als je oude ritten ook materiaal wilt geven, moet je de CSV verwijderen
        if act_id not in existing_ids:
            # Materiaal naam opzoeken
            gear_id = act.get('gear_id')
            gear_name = gear_map.get(gear_id, "")
            
            # Snelheid conversie (m/s -> km/u)
            avg_speed = act['average_speed'] * 3.6
            max_speed = act['max_speed'] * 3.6
            
            row = {
                'Activiteits-ID': act_id,
                'Datum van activiteit': format_date(act['start_date_local']),
                'Naam activiteit': act['name'],
                'Activiteitstype': TYPE_MAPPING.get(act['type'], act['type']),
                'Beweegtijd': act['moving_time'],
                'Afstand': f"{(act['distance']/1000):.2f}".replace('.', ','),
                'Max. hartslag': act.get('max_heartrate', ''),
                'Gemiddelde snelheid': f"{avg_speed:.1f}".replace('.', ','),
                'Max. snelheid': f"{max_speed:.1f}".replace('.', ','),
                'Totale stijging': act['total_elevation_gain'],
                'Gemiddelde hartslag': act.get('average_heartrate', ''),
                'Calorieën': act.get('kilojoules', 0),
                'Uitrusting voor activiteit': gear_name  # <--- HIER ZIT DE UPDATE
            }
            new_rows.append(row)

    # 4. Opslaan
    if new_rows:
        df_new = pd.DataFrame(new_rows)
        # Zorg dat de kolommen matchen
        if not df_existing.empty:
            # Als de oude CSV de kolom 'Uitrusting...' nog niet had, voeg die toe
            if 'Uitrusting voor activiteit' not in df_existing.columns:
                df_existing['Uitrusting voor activiteit'] = ""
            
            # Voeg samen
            df_final = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_final = df_new
            
        df_final.to_csv(CSV_FILE, index=False)
        print(f"✅ {len(new_rows)} activiteiten toegevoegd (met materiaal!)")
    else:
        print("✅ Geen nieuwe activiteiten.")

if __name__ == "__main__":
    update_csv()
