import requests
import pandas as pd
import os
import time
import re

# --- CONFIGURATIE ---
# Haalt secrets uit GitHub Actions omgeving
CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('STRAVA_REFRESH_TOKEN')

# Auth URL
AUTH_URL = "https://www.strava.com/oauth/token"
ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"

def get_access_token():
    """Wisselt refresh token in voor vers access token"""
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type': 'refresh_token',
        'f': 'json'
    }
    print("🔄 Token verversen...")
    try:
        res = requests.post(AUTH_URL, data=payload, verify=False)
        res.raise_for_status()
        return res.json()['access_token']
    except Exception as e:
        print(f"❌ Fout bij token: {e}")
        exit(1)

def get_activities(limit=1500):  # <--- HIER STAAT NU 1500
    """Haalt de laatste 'limit' activiteiten op"""
    token = get_access_token()
    headers = {'Authorization': f"Bearer {token}"}
    all_activities = []
    page = 1
    per_page = 200 # Maximaal toegestaan door Strava per call
    
    print(f"📥 Bezig met ophalen van de laatste {limit} activiteiten...")
    
    while True:
        try:
            r = requests.get(f"{ACTIVITIES_URL}?per_page={per_page}&page={page}", headers=headers)
            r.raise_for_status()
            
            data = r.json()
            if not data:
                break
                
            all_activities.extend(data)
            print(f"   - Pagina {page} binnen ({len(data)} items)... Totaal nu: {len(all_activities)}")
            
            if len(all_activities) >= limit:
                break
            page += 1
            
        except Exception as e:
            print(f"❌ Fout bij ophalen data op pagina {page}: {e}")
            break
            
    print(f"✅ Klaar! {len(all_activities)} activiteiten opgehaald.")
    return all_activities[:limit]

def translate_type(strava_type):
    """Vertaalt Engelse Strava types naar jouw Dashboard types"""
    mapping = {
        'Run': 'Hardlopen',
        'Ride': 'Fietsrit',
        'VirtualRide': 'Virtuele fietsrit',
        'Walk': 'Wandelen',
        'Swim': 'Zwemmen',
        'WeightTraining': 'Krachttraining',
        'Workout': 'Training',
        'Hike': 'Wandelen',
        'GravelRide': 'Fietsrit',
        'MountainBikeRide': 'Fietsrit',
        'E-BikeRide': 'Fietsrit',
        'Velomobile': 'Fietsrit'
    }
    return mapping.get(strava_type, strava_type)

def process_data():
    # VRAAG OM 1500 ACTIVITEITEN
    activities = get_activities(1500)
    
    if not activities:
        print("⚠️ Geen activiteiten gevonden.")
        return

    # Omzetten naar lijst voor DataFrame
    clean_data = []
    for a in activities:
        # Datum formateren naar ISO (veilig voor parser V42.0)
        # Voorbeeld Strava: "2025-01-18T09:00:00Z" -> "2025-01-18 09:00:00"
        dt = a['start_date_local'].replace('T', ' ').replace('Z', '')
        
        # Uitrusting naam ophalen (als beschikbaar in samenvatting) of ID gebruiken
        gear = a.get('gear_id', '')
        
        clean_data.append({
            'Datum van activiteit': dt,
            'Naam activiteit': a['name'],
            'Activiteitstype': translate_type(a['type']), # Vertaal naar NL
            'Afstand': a['distance'] / 1000, # Meters naar KM
            'Beweegtijd': a['moving_time'], # Seconden
            'Gemiddelde snelheid': a['average_speed'] * 3.6, # m/s naar km/u
            'Gemiddelde hartslag': a.get('average_heartrate', ''),
            'Uitrusting voor activiteit': gear 
        })

    df = pd.DataFrame(clean_data)
    
    # Opslaan als CSV
    df.to_csv('activities.csv', index=False)
    print(f"💾 activities.csv succesvol bijgewerkt met {len(df)} regels!")

if __name__ == "__main__":
    if not CLIENT_ID:
        print("❌ Geen API keys gevonden. Draai dit lokaal of check GitHub Secrets.")
    else:
        process_data()
