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
    'GravelRide': 'Fietsrit', 'TrailRun': 'Hardloopsessie',
    'Elliptical': 'Training', 'Yoga': 'Training'
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
        try: print(r.text) 
        except: pass
        sys.exit(1)

def get_gear_map(token):
    url = "https://www.strava.com/api/v3/athlete"
    headers = {'Authorization': f"Bearer {token}"}
    gear_map = {}
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
        for bike in data.get('bikes', []): gear_map[bike['id']] = bike['name']
        for shoe in data.get('shoes', []): gear_map[shoe['id']] = shoe['name']
        print(f"✅ Materiaal lijst opgehaald ({len(gear_map)} items).")
    except:
        print("⚠️ Kon materiaal niet ophalen (Token permissie issue?). We gebruiken bestaande CSV data als backup.")
    return gear_map

def format_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        maanden = {1:'jan', 2:'feb', 3:'mrt', 4:'apr', 5:'mei', 6:'jun', 
                   7:'jul', 8:'aug', 9:'sep', 10:'okt', 11:'nov', 12:'dec'}
        return f"{dt.day} {maanden[dt.month]} {dt.year}, {dt.strftime('%H:%M:%S')}"
    except:
        return date_str

def safe_float(value, multiplier=1.0):
    if value is None: return 0.0
    try: return float(value) * multiplier
    except: return 0.0

def update_csv():
    print("🔄 Start Slimme Update (Behoud Data)...")
    token = get_access_token()
    gear_map = get_gear_map(token)
    
    # 1. Lees bestaande CSV in voor backup van materiaal
    old_gear_data = {}
    if os.path.exists(CSV_FILE):
        try:
            df_old = pd.read_csv(CSV_FILE)
            # Maak een dictionary: ID -> MateriaalNaam
            if 'Activiteits-ID' in df_old.columns and 'Uitrusting voor activiteit' in df_old.columns:
                # Zorg dat we strings hebben
                df_old['Activiteits-ID'] = df_old['Activiteits-ID'].astype(str)
                df_old['Uitrusting voor activiteit'] = df_old['Uitrusting voor activiteit'].fillna('').astype(str)
                
                for _, row in df_old.iterrows():
                    gear_val = row['Uitrusting voor activiteit'].strip()
                    if gear_val and gear_val.lower() != 'nan':
                        old_gear_data[row['Activiteits-ID']] = gear_val
            print(f"💾 {len(old_gear_data)} materiaal-items uit oude CSV veiliggesteld.")
        except Exception as e:
            print(f"⚠️ Kon oude CSV niet lezen: {e}")

    # 2. Haal nieuwe data op
    all_activities = []
    page = 1
    headers = {'Authorization': f"Bearer {token}"}
    
    while True:
        print(f"   📄 Ophalen pagina {page}...")
        try:
            r = requests.get(f"https://www.strava.com/api/v3/athlete/activities?per_page=200&page={page}", headers=headers)
            r.raise_for_status()
            data = r.json()
            if not data: break
            all_activities.extend(data)
            page += 1
            time.sleep(1)
        except Exception as e:
            print(f"❌ Fout bij pagina {page}: {e}")
            break

    # 3. Samenvoegen
    new_rows = []
    for act in all_activities:
        try:
            act_id = str(act['id'])
            
            # Slimme Materiaal Selectie
            # Stap A: Kijk of Strava het weet
            gear_id = act.get('gear_id')
            gear_name = gear_map.get(gear_id, "")
            
            # Stap B: Als Strava het niet weet, kijk in de backup
            if not gear_name and act_id in old_gear_data:
                gear_name = old_gear_data[act_id]
            
            avg_speed = safe_float(act.get('average_speed'), 3.6)
            max_speed = safe_float(act.get('max_speed'), 3.6)
            dist_km = safe_float(act.get('distance'), 0.001)
            
            row = {
                'Activiteits-ID': act_id,
                'Datum van activiteit': format_date(act.get('start_date_local', '')),
                'Naam activiteit': act.get('name', 'Naamloos'),
                'Activiteitstype': TYPE_MAPPING.get(act.get('type'), act.get('type', 'Overig')),
                'Beweegtijd': act.get('moving_time', 0),
                'Afstand': f"{dist_km:.2f}".replace('.', ','),
                'Max. hartslag': act.get('max_heartrate', ''),
                'Gemiddelde snelheid': f"{avg_speed:.1f}".replace('.', ','),
                'Max. snelheid': f"{max_speed:.1f}".replace('.', ','),
                'Totale stijging': act.get('total_elevation_gain', 0),
                'Gemiddelde hartslag': act.get('average_heartrate', ''),
                'Calorieën': act.get('kilojoules', 0),
                'Uitrusting voor activiteit': gear_name # Nu met backup!
            }
            new_rows.append(row)
        except: continue

    if new_rows:
        df_new = pd.DataFrame(new_rows)
        df_new.to_csv(CSV_FILE, index=False)
        print("✅ CSV bijgewerkt (Materiaal behouden!).")
    else:
        print("⚠️ Geen data.")

if __name__ == "__main__":
    update_csv()
