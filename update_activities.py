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
ACTIVITY_DETAIL_URL = "https://www.strava.com/api/v3/activities"

# --- ZELF GEDEFINIEERDE UITRUSTING (SCHOENEN) ---
# OPMERKING: Fietsen worden automatisch via datum bepaald. Vul hier je schoenennamen in:
MANUAL_GEAR_MAP = {
    'g20191215': 'Adidas Adistar',       
    'g28340688': 'Schoenen 2 (vul naam in)',       
    'g20403195': 'Schoenen 3 (vul naam in)',       
    'g13828248': 'Schoenen 4 (vul naam in)'        
}

def get_access_token():
    payload = {'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'refresh_token': REFRESH_TOKEN, 'grant_type': 'refresh_token', 'f': 'json'}
    try:
        res = requests.post(AUTH_URL, data=payload, verify=False)
        res.raise_for_status()
        return res.json()['access_token']
    except Exception as e:
        print(f"❌ Fout bij token: {e}")
        exit(1)

def translate_type(strava_type):
    mapping = {'Run': 'Hardlopen', 'Ride': 'Fietsrit', 'VirtualRide': 'Virtuele fietsrit', 'Walk': 'Wandelen', 'Swim': 'Zwemmen', 'WeightTraining': 'Krachttraining', 'Workout': 'Training', 'Hike': 'Wandelen', 'GravelRide': 'Fietsrit', 'MountainBikeRide': 'Fietsrit', 'E-BikeRide': 'Fietsrit', 'Velomobile': 'Fietsrit'}
    return mapping.get(strava_type, strava_type)

def process_data():
    token = get_access_token()
    headers = {'Authorization': f"Bearer {token}"}
    
    # 1. Lees de oude CSV in om API requests voor calorieën te besparen
    existing_cals = {}
    if os.path.exists('activities.csv'):
        try:
            df_old = pd.read_csv('activities.csv')
            if 'Calorieën' in df_old.columns and 'Datum van activiteit' in df_old.columns:
                for _, row in df_old.iterrows():
                    if pd.notna(row['Calorieën']) and float(row['Calorieën']) > 0:
                        existing_cals[str(row['Datum van activiteit'])] = float(row['Calorieën'])
        except:
            print("Geen oude cache kunnen laden.")

    all_activities = []
    page = 1
    print("📥 Bezig met ophalen historie (limit 1500)...")
    
    while True:
        r = requests.get(f"{ACTIVITIES_URL}?per_page=200&page={page}", headers=headers)
        data = r.json()
        if not data: break
        all_activities.extend(data)
        if len(all_activities) >= 1500: break
        page += 1

    clean_data = []
    api_calls = 0
    
    for a in all_activities:
        dt = a['start_date_local'].replace('T', ' ').replace('Z', '')
        sport_type = translate_type(a['type'])
        
        # --- GEAR VERTALING (Basis voor schoenen) ---
        gear_id = a.get('gear_id')
        gear_name = MANUAL_GEAR_MAP.get(gear_id, gear_id) if gear_id else ""
        
        # --- SLIMME DATUM-FIETS OVERRIDE (Buiten + Zwift) ---
        if sport_type in ['Fietsrit', 'Virtuele fietsrit']:
            if dt < "2025-05-09":
                gear_name = "Proracer"
            else:
                gear_name = "Merida Scultura 5000"
                
        # --- CALORIEËN OPHALEN VIA STRAVA ---
        cal = existing_cals.get(dt, 0)
        
        if cal == 0:
            cal = a.get('calories', a.get('kilojoules', 0))
            
        if cal == 0 and api_calls < 80: 
            act_id = a['id']
            try:
                res = requests.get(f"{ACTIVITY_DETAIL_URL}/{act_id}", headers=headers)
                if res.status_code == 200:
                    detail = res.json()
                    cal = detail.get('calories', 0)
                    api_calls += 1
                    time.sleep(0.5)
                    print(f"   🔍 Detail opgehaald voor {sport_type} op {dt} ({cal} kcal)")
            except:
                pass

        clean_data.append({
            'Datum van activiteit': dt,
            'Naam activiteit': a['name'],
            'Activiteitstype': sport_type,
            'Afstand': a['distance'] / 1000,
            'Beweegtijd': a['moving_time'],
            'Gemiddelde snelheid': a['average_speed'] * 3.6,
            'Gemiddelde hartslag': a.get('average_heartrate', ''),
            'Gemiddeld wattage': a.get('average_watts', ''),
            'Uitrusting voor activiteit': gear_name,
            'Calorieën': cal
        })

    df = pd.DataFrame(clean_data)
    df.to_csv('activities.csv', index=False)
    print(f"💾 Klaar! {len(df)} activiteiten opgeslagen. {api_calls} detail-opvragingen gedaan.")

if __name__ == "__main__":
    if not CLIENT_ID: print("❌ Geen API keys.")
    else: process_data()
