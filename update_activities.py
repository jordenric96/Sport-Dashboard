import requests
import pandas as pd
from datetime import datetime
import os
import sys

# --- CONFIGURATIE ---
# Haal geheimen op uit de omgeving (GitHub Secrets)
CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('STRAVA_REFRESH_TOKEN')

CSV_FILE = 'activities.csv'

# Vertalingen naar jouw CSV-indeling
TYPE_MAPPING = {
    'Ride': 'Fietsrit', 
    'VirtualRide': 'Virtuele fietsrit',
    'Run': 'Hardloopsessie', 
    'Walk': 'Wandeling', 
    'Hike': 'Wandeling',
    'WeightTraining': 'Training', 
    'Workout': 'Training', 
    'Swim': 'Zwemmen',
    'GravelRide': 'Fietsrit'
}

def get_access_token():
    """Wisselt de Refresh Token in voor een tijdelijke Access Token."""
    if not CLIENT_ID or not CLIENT_SECRET or not REFRESH_TOKEN:
        print("❌ FOUT: Strava secrets ontbreken in environment variables.")
        sys.exit(1)

    url = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type': 'refresh_token'
    }
    
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        return response.json()['access_token']
    except Exception as e:
        print(f"❌ Fout bij ophalen access token: {e}")
        # Print response text voor debugging (zonder secrets te lekken)
        try: print(response.text)
        except: pass
        sys.exit(1)

def format_strava_date(date_str):
    """Zet Strava tijd om naar jouw NL formaat: '4 jan 2026, 09:28:00'"""
    dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
    maanden = {1:'jan', 2:'feb', 3:'mrt', 4:'apr', 5:'mei', 6:'jun', 
               7:'jul', 8:'aug', 9:'sep', 10:'okt', 11:'nov', 12:'dec'}
    return f"{dt.day} {maanden[dt.month]} {dt.year}, {dt.strftime('%H:%M:%S')}"

def update_csv():
    print("🔄 Start Strava Update...")
    
    # 1. Token regelen
    token = get_access_token()
    
    # 2. Huidige CSV inlezen (om dubbelen te voorkomen)
    existing_ids = set()
    if os.path.exists(CSV_FILE):
        try:
            df_existing = pd.read_csv(CSV_FILE)
            # Zorg dat IDs als strings worden behandeld
            if 'Activiteits-ID' in df_existing.columns:
                existing_ids = set(df_existing['Activiteits-ID'].astype(str))
            print(f"📂 Huidige CSV bevat {len(existing_ids)} activiteiten.")
        except Exception as e:
            print(f"⚠️ Kon CSV niet lezen: {e}. We beginnen met een lege set.")
            df_existing = pd.DataFrame()
    else:
        print("⚠️ Geen activities.csv gevonden. Er wordt een nieuwe aangemaakt.")
        df_existing = pd.DataFrame()

    # 3. Nieuwe data ophalen (laatste 30 activiteiten)
    headers = {'Authorization': f"Bearer {token}"}
    url = "https://www.strava.com/api/v3/athlete/activities?per_page=30"
    
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        activities = r.json()
    except Exception as e:
        print(f"❌ Fout bij ophalen activiteiten: {e}")
        sys.exit(1)

    new_rows = []
    
    for act in activities:
        act_id = str(act['id'])
        
        # Alleen toevoegen als hij nog niet bestaat
        if act_id not in existing_ids:
            # Data formatteren zoals in jouw originele CSV
            # Afstand: km met komma (bijv "37,97")
            afstand_km = act['distance'] / 1000
            afstand_str = f"{afstand_km:.2f}".replace('.', ',')
            
            row = {
                'Activiteits-ID': act_id,
                'Datum van activiteit': format_strava_date(act['start_date_local']),
                'Naam activiteit': act['name'],
                'Activiteitstype': TYPE_MAPPING.get(act['type'], act['type']),
                'Beschrijving van activiteit': '',
                'Verstreken tijd': act['elapsed_time'],
                'Afstand': afstand_str,
                'Max. hartslag': act.get('max_heartrate', ''),
                'Gemiddelde snelheid': act['average_speed'], # Dashboard script converteert dit later x3.6
                'Totale stijging': act['total_elevation_gain'],
                'Gemiddelde hartslag': act.get('average_heartrate', ''),
                'Calorieën': act.get('kilojoules', 0),
                'Beweegtijd': act['moving_time']
            }
            new_rows.append(row)
            print(f"   ➕ Nieuw: {act['name']} ({row['Datum van activiteit']})")

    # 4. Opslaan
    if new_rows:
        df_new = pd.DataFrame(new_rows)
        
        # Als er al een CSV is, aligneer de kolommen
        if not df_existing.empty:
            # Zorg dat nieuwe data dezelfde kolommen heeft
            for col in df_existing.columns:
                if col not in df_new.columns:
                    df_new[col] = "" 
            # Volgorde herstellen
            df_new = df_new[df_existing.columns]
            
            # Toevoegen (append) zonder header
            df_new.to_csv(CSV_FILE, mode='a', header=False, index=False)
        else:
            # Nieuw bestand: wel header
            df_new.to_csv(CSV_FILE, index=False)
            
        print(f"✅ {len(new_rows)} activiteiten toegevoegd!")
    else:
        print("✅ Geen nieuwe activiteiten gevonden.")

if __name__ == "__main__":
    update_csv()
