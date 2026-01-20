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
    'Elliptical': 'Training', 'Yoga': 'Training' # Extra veiligheid
}

def get_access_token():
    if not CLIENT_ID or not CLIENT_SECRET or not REFRESH_TOKEN:
        print("❌ FOUT: Secrets ontbreken. Check je GitHub Secrets.")
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
        # Print response voor debuggen (maar pas op met secrets in logs)
        try: print(r.text) 
        except: pass
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
        print(f"⚠️ Kon materiaal niet ophalen (geen ramp): {e}")
    
    return gear_map

def format_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        maanden = {1:'jan', 2:'feb', 3:'mrt', 4:'apr', 5:'mei', 6:'jun', 
                   7:'jul', 8:'aug', 9:'sep', 10:'okt', 11:'nov', 12:'dec'}
        return f"{dt.day} {maanden[dt.month]} {dt.year}, {dt.strftime('%H:%M:%S')}"
    except:
        return date_str # Fallback

def safe_float(value, multiplier=1.0):
    """Veilige conversie naar getal, voorkomt crashes bij None"""
    if value is None: return 0.0
    try:
        return float(value) * multiplier
    except:
        return 0.0

def update_csv():
    print("🔄 Start Volledige Strava Sync (Veilige Modus)...")
    token = get_access_token()
    gear_map = get_gear_map(token)
    
    all_activities = []
    page = 1
    headers = {'Authorization': f"Bearer {token}"}
    
    # Loop door alle pagina's
    while True:
        print(f"   📄 Ophalen pagina {page}...")
        url = f"https://www.strava.com/api/v3/athlete/activities?per_page=200&page={page}"
        
        try:
            r = requests.get(url, headers=headers)
            r.raise_for_status()
            data = r.json()
            
            if not data: 
                break # Klaar!
                
            all_activities.extend(data)
            page += 1
            time.sleep(1) # Pauze om API limieten te respecteren
            
        except Exception as e:
            print(f"❌ Fout bij pagina {page}: {e}")
            break

    print(f"✅ Totaal {len(all_activities)} activiteiten binnengehaald.")

    new_rows = []
    for act in all_activities:
        try:
            act_id = str(act['id'])
            
            # Materiaal veilig ophalen
            gear_id = act.get('gear_id')
            gear_name = gear_map.get(gear_id, "")
            
            # Snelheid veilig berekenen (voorkomt crash bij manual entry)
            avg_speed = safe_float(act.get('average_speed'), 3.6)
            max_speed = safe_float(act.get('max_speed'), 3.6)
            dist_km = safe_float(act.get('distance'), 0.001)
            
            # Data samenstellen
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
                'Uitrusting voor activiteit': gear_name
            }
            new_rows.append(row)
        except Exception as e:
            print(f"⚠️ Rij overgeslagen wegens fout: {e}")
            continue

    if new_rows:
        df_new = pd.DataFrame(new_rows)
        # Sla op (overschrijf alles)
        df_new.to_csv(CSV_FILE, index=False)
        print("✅ CSV succesvol herbouwd met alle historie!")
    else:
        print("⚠️ Geen data gevonden om op te slaan.")

if __name__ == "__main__":
    update_csv()
