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
    """Haalt namen van fietsen en schoenen op."""
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
    except Exception as e:
        print(f"⚠️ Kon materiaal niet ophalen: {e}")
    
    return gear_map

def format_date(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
    maanden = {1:'jan', 2:'feb', 3:'mrt', 4:'apr', 5:'mei', 6:'jun', 
               7:'jul', 8:'aug', 9:'sep', 10:'okt', 11:'nov', 12:'dec'}
    return f"{dt.day} {maanden[dt.month]} {dt.year}, {dt.strftime('%H:%M:%S')}"

def update_csv():
    print("🔄 Start Volledige Strava Sync...")
    token = get_access_token()
    gear_map = get_gear_map(token)
    
    # We bouwen de lijst helemaal opnieuw op (veiligste voor gear update)
    all_activities = []
    page = 1
    headers = {'Authorization': f"Bearer {token}"}
    
    while True:
        print(f"   📄 Ophalen pagina {page}...")
        url = f"https://www.strava.com/api/v3/athlete/activities?per_page=200&page={page}"
        
        try:
            r = requests.get(url, headers=headers)
            r.raise_for_status()
            data = r.json()
            
            if not data: # Geen activiteiten meer op deze pagina
                break
                
            all_activities.extend(data)
            page += 1
            
        except Exception as e:
            print(f"❌ Fout bij pagina {page}: {e}")
            break

    print(f"✅ Totaal {len(all_activities)} activiteiten gevonden.")

    new_rows = []
    for act in all_activities:
        act_id = str(act['id'])
        gear_id = act.get('gear_id')
        gear_name = gear_map.get(gear_id, "")
        
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
            'Uitrusting voor activiteit': gear_name
        }
        new_rows.append(row)

    # Opslaan (Overschrijft alles, zodat alles fris is met materiaal)
    if new_rows:
        df_new = pd.DataFrame(new_rows)
        df_new.to_csv(CSV_FILE, index=False)
        print("✅ CSV succesvol herbouwd met alle historie!")
    else:
        print("⚠️ Geen data om op te slaan.")

if __name__ == "__main__":
    update_csv()
