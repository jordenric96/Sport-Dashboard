import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import warnings
import re

warnings.filterwarnings("ignore", category=UserWarning)

# --- CONFIGURATIE ---
GOALS = {'bike_out': 3000, 'zwift': 3000, 'run': 350}

COLORS = {
    'primary': '#0f172a', 'gold': '#d4af37', 'bg': '#f8fafc',
    'card': '#ffffff', 'text': '#1e293b', 'text_light': '#64748b',
    'zwift': '#ff6600', 'bike_out': '#0099ff', 'run': '#fbbf24', 
    'swim': '#3b82f6', 'padel': '#84cc16', 'walk': '#10b981', 
    'default': '#64748b', 'ref_gray': '#cbd5e1'
}

# --- 1. HARDE DATUM FIX (CRUCIAAL VOOR JE SESSIE AANTALLEN) ---
def parse_dutch_date(date_str):
    """
    Zet '20 jun 2017, 15:10:32' om naar een datum.
    Negeert komma's en vertaalt NL maanden handmatig.
    """
    if pd.isna(date_str) or str(date_str).strip() == "": 
        return pd.NaT
        
    # Mapping voor NL maanden (inclusief puntjes voor de zekerheid)
    d_map = {
        'jan': 1, 'feb': 2, 'mrt': 3, 'mar': 3, 'apr': 4, 'mei': 5, 'may': 5,
        'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    try:
        # Maak schoon: alleen letters, cijfers, dubbele punt en spaties
        s = re.sub(r'[^a-zA-Z0-9: ]', '', str(date_str).lower())
        parts = s.split()
        
        # Verwacht: [20, jun, 2017, 15:10:32]
        if len(parts) >= 3:
            day = int(parts[0])
            month_str = parts[1][:3] # Pak eerste 3 letters
            month = d_map.get(month_str, 1)
            year = int(parts[2])
            return pd.Timestamp(year=year, month=month, day=day)
    except:
        pass
        
    # Fallback
    return pd.to_datetime(date_str, errors='coerce')

# --- 2. CATEGORISERING (GEBASEERD OP KOLOM ACTIVITEITSTYPE) ---
def determine_category(row):
    # We gebruiken de exacte kolom 'Activiteitstype'
    atype = str(row['Activiteitstype']).lower().strip()
    anaam = str(row['Naam']).lower().strip()
    
    # Virtueel (Zwift)
    if 'virtu' in atype or 'zwift' in atype or 'zwift' in anaam:
        return 'Virtueel'
    
    # Fietsen (Buiten)
    if any(x in atype for x in ['fiets', 'ride', 'gravel', 'mtb', 'cycle', 'wieler']):
        return 'Fiets'
        
    # Hardlopen
    if any(x in atype for x in ['hardloop', 'run', 'jog']):
        return 'Hardlopen'
        
    # Padel / Training
    if any(x in atype for x in ['training', 'workout', 'kracht', 'padel', 'fitness', 'gym']):
        return 'Padel'
        
    # Zwemmen
    if 'zwem' in atype or 'swim' in atype:
        return 'Zwemmen'
        
    # Wandelen
    if any(x in atype for x in ['wandel', 'hike', 'walk']):
        return 'Wandelen'
        
    return 'Overig'

def get_sport_style(cat):
    styles = {
        'Fiets': {'icon': '🚴', 'color': COLORS['bike_out']},
        'Virtueel': {'icon': '👾', 'color': COLORS['zwift']},
        'Hardlopen': {'icon': '🏃', 'color': COLORS['run']},
        'Wandelen': {'icon': '🚶', 'color': COLORS['walk']},
        'Padel': {'icon': '🎾', 'color': COLORS['padel']},
        'Zwemmen': {'icon': '🏊', 'color': COLORS['swim']},
        'Overig': {'icon': '🏅', 'color': COLORS['default']}
    }
    return styles.get(cat, styles['Overig'])

# --- 3. HELPER FUNCTIES ---
def format_time(seconds):
    if pd.isna(seconds) or seconds <= 0: return '-'
    h, r = divmod(int(seconds), 3600)
    m, _ = divmod(r, 60)
    return f'{h}u {m:02d}m'

def format_diff_html(cur, prev, unit=""):
    if pd.isna(prev) or prev == 0: return '<span style="color:#ccc">-</span>'
    diff = cur - prev
    color = '#10b981' if diff >= 0 else '#ef4444'
    arrow = "▲" if diff >= 0 else "▼"
    return f'<span style="color:{color}; font-weight:700; font-size:0.9em;">{arrow} {abs(diff):.1f} {unit}</span>'

# --- 4. STREAK BEREKENING (STRAVA STIJL) ---
def calculate_streaks(df):
    """Berekent streak over de hele geschiedenis, niet per jaar."""
    if df.empty: return {}
    valid = df.dropna(subset=['Datum']).sort_values('Datum')
    if valid.empty: return {}
    
    # Zet alles om naar de MAANDAG van die week
    valid['WeekStart'] = valid['Datum'].dt.to_period('W-MON').dt.start_time
    unique_weeks = sorted(valid['WeekStart'].unique())
    
    if not unique_weeks: return {}
    
    # Huidige Streak
    cur_wk = 0
    now_wk = pd.Timestamp.now().to_period('W-MON').start_time
    last_act_wk = unique_weeks[-1]
    
    # Als de laatste activiteit deze week OF vorige week was, loopt de streak
    if (now_wk - last_act_wk).days <= 7:
        cur_wk = 1
        # Tel terug
        for i in range(len(unique_weeks)-2, -1, -1):
            if (unique_weeks[i+1] - unique_weeks[i]).days == 7:
                cur_wk += 1
            else:
                break
    
    # Langste Streak Ooit
    max_wk = 0
    temp = 1
    if len(unique_weeks) > 0:
        max_wk = 1
        for i in range(1, len(unique_weeks)):
            if (unique_weeks[i] - unique_weeks[i-1]).days == 7:
                temp += 1
            else:
                max_wk = max(max_wk, temp)
                temp = 1
        max_wk = max(max_wk, temp)
        
    return {'cur_week': cur_wk, 'max_week': max_wk}

# --- 5. UI GENERATOREN ---
def generate_stats_box(df, current_year):
    df_cur = df[df['Jaar'] == current_year]
    
    # Doelen berekenen
    b_km = df_cur[df_cur['Categorie'] == 'Fiets']['Afstand_km'].sum()
    z_km = df_cur[df_cur['Categorie'] == 'Virtueel']['Afstand_km'].sum()
    r_km = df_cur[df_cur['Categorie'] == 'Hardlopen']['Afstand_km'].sum()
    
    b_pct = min(100, (b_km / GOALS['bike_out']) * 100)
    z_pct = min(100, (z_km / GOALS['zwift']) * 100)
    r_pct = min(100, (r_km / GOALS['run']) * 100)
    
    s = calculate_streaks(df)
    
    return f"""
    <div class="stats-box-container">
        <div class="goals-section">
            <h3 class="box-title">🎯 DOELEN {current_year}</h3>
            <div class="goal-item">
                <div class="goal-label"><span>🚴 Buiten: {b_km:.0f} / {GOALS['bike_out']} km</span><span>{b_pct:.1f}%</span></div>
                <div class="goal-bar"><div style="width:{b_pct}%; background:{COLORS['bike_out']};"></div></div>
            </div>
            <div class="goal-item">
                <div class="goal-label"><span>👾 Zwift: {z_km:.0f} / {GOALS['zwift']} km</span><span>{z_pct:.1f}%</span></div>
                <div class="goal-bar"><div style="width:{z_pct}%; background:{COLORS['zwift']};"></div></div>
            </div>
            <div class="goal-item">
                <div class="goal-label"><span>🏃 Lopen: {r_km:.0f} / {GOALS['run']} km</span><span>{r_pct:.1f}%</span></div>
                <div class="goal-bar"><div style="width:{r_pct}%; background:{COLORS['run']};"></div></div>
            </div>
        </div>
        <div class="streaks-section">
            <h3 class="box-title">🔥 REEKSEN (STREAKS)</h3>
            <div class="streak-row"><span class="label">Huidige Reeks:</span><span class="val">{s.get('cur_week', 0)} weken</span></div>
            <div class="streak-row"><span class="label">Langste Reeks:</span><span class="val">{s.get('max_week', 0)} weken</span></div>
            <p style="font-size:10px; color:#94a3b8; margin-top:5px;">*Gebaseerd op weekactiviteit (ma-zo)</p>
        </div>
    </div>"""

def generate_sport_cards(df_yr, df_prev_comp):
    html = '<div class="sport-grid">'
    # We tonen expliciet de belangrijke categorieën + overig
    categories = sorted(df_yr['Categorie'].unique())
    
    for cat in categories:
        df_s = df_yr[df_yr['Categorie'] == cat]
        df_p = df_prev_comp[df_prev_comp['Categorie'] == cat] if df_prev_comp is not None else pd.DataFrame()
        
        if df_s.empty: continue
        
        style = get_sport_style(cat)
        
        # Stats berekenen
        n_sessies = len(df_s)
        n_prev = len(df_p)
        dist = df_s['Afstand_km'].sum()
        dist_p = df_p['Afstand_km'].sum() if not df_p.empty else 0
        tijd = df_s['Beweegtijd_sec'].sum()
        hr = df_s['Hartslag'].mean()
        
        # Snelheid
        spd_val = "-"
        if cat == 'Hardlopen' and dist > 0:
            pace = tijd / dist
            spd_val = f"{int(pace//60)}:{int(pace%60):02d} /km"
        elif tijd > 0:
            spd_val = f"{(dist/(tijd/3600)):.1f} km/u"

        # Afstand regel (verberg voor Padel/Fitness)
        dist_row = ""
        if cat not in ['Padel', 'Overig'] and dist > 0:
            dist_row = f'<div class="stat-row"><span>Afstand</span> <div class="val-group"><strong>{dist:,.0f} km</strong> {format_diff_html(dist, dist_p)}</div></div>'

        html += f"""<div class="sport-card">
            <div class="sport-header" style="color:{style['color']}">
                <div class="icon-circle" style="background:{style['color']}15">{style['icon']}</div>
                <h3>{cat}</h3>
            </div>
            <div class="sport-body">
                <div class="stat-row"><span>Sessies</span> <div class="val-group"><strong>{n_sessies}</strong> {format_diff_html(n_sessies, n_prev)}</div></div>
                <div class="stat-row"><span>Tijd</span> <strong>{format_time(tijd)}</strong></div>
                {dist_row}
                <div class="stat-row"><span>Gem. Snelh</span> <strong>{spd_val}</strong></div>
                <div class="stat-row"><span>Gem. Hartslag</span> <strong>{f'{hr:.0f} bpm' if pd.notna(hr) else '-'}</strong></div>
            </div>
        </div>"""
    return html + '</div>'

def generate_hall_of_fame(df):
    html = '<div class="hof-grid">'
    df_hof = df.dropna(subset=['Datum']).copy()
    
    for cat in ['Fiets', 'Virtueel', 'Hardlopen']:
        df_s = df_hof[df_hof['Categorie'] == cat].copy()
        if df_s.empty: continue
        style = get_sport_style(cat)
        
        def top3(col, unit, is_pace=False):
            d_sorted = df_s.sort_values(col, ascending=False).head(3)
            res = ""
            medals = ['🥇','🥈','🥉']
            for i, (_, r) in enumerate(d_sorted.iterrows()):
                v = r[col]
                d = r['Datum'].strftime('%d-%m-%y')
                val = f"{v:.1f} {unit}"
                if is_pace: val = f"{int((3600/v)//60)}:{int((3600/v)%60):02d} /km"
                res += f'<div class="top3-item"><span class="medal">{medals[i]}</span> <span class="t3-val">{val}</span> <span class="t3-date">{d}</span></div>'
            return res

        html += f"""<div class="hof-card">
            <div class="hof-header" style="color:{style['color']}">{style['icon']} {cat}</div>
            <div class="hof-sec"><div class="sec-lbl">Langste Afstand</div>{top3('Afstand_km', 'km')}</div>
            <div class="hof-sec"><div class="sec-lbl">Snelste (Gem.)</div>{top3('Gem_Snelheid', 'km/u', cat=='Hardlopen')}</div>
        </div>"""
    return html + '</div>'

def create_monthly_charts(df_cur, df_prev, year):
    months = ['Jan','Feb','Mrt','Apr','Mei','Jun','Jul','Aug','Sep','Okt','Nov','Dec']
    
    def make_chart(cat, title, color):
        c_m = df_cur[df_cur['Categorie'] == cat].groupby(df_cur['Datum'].dt.month)['Afstand_km'].sum().reindex(range(1,13), fill_value=0)
        p_m = df_prev[df_prev['Categorie'] == cat].groupby(df_prev['Datum'].dt.month)['Afstand_km'].sum().reindex(range(1,13), fill_value=0)
        
        if c_m.sum() == 0 and p_m.sum() == 0: return ""
        
        f = go.Figure()
        f.add_trace(go.Bar(x=months, y=p_m, name=f"{year-1}", marker_color=COLORS['ref_gray']))
        f.add_trace(go.Bar(x=months, y=c_m, name=f"{year}", marker_color=color))
        f.update_layout(title=title, template='plotly_white', barmode='group', margin=dict(t=40,b=20,l=20,r=20), height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=True, legend=dict(orientation="h", y=1.1))
        return f'<div class="chart-box full-width">{f.to_html(full_html=False, include_plotlyjs="cdn")}</div>'

    return f"""{make_chart('Fiets', '🚴 Fietsen Buiten (km per maand)', COLORS['bike_out'])}
               <div style="height:15px"></div>
               {make_chart('Hardlopen', '🏃 Hardlopen (km per maand)', COLORS['run'])}"""

def generate_gear_section(df):
    dfg = df.dropna(subset=['Gear']).copy()
    dfg = dfg[dfg['Gear'].str.strip() != '']
    if dfg.empty: return "<p>Geen data</p>"
    stats = dfg.groupby('Gear').agg(Count=('Categorie','count'), Km=('Afstand_km','sum'), Type=('Categorie', lambda x: x.mode()[0])).reset_index().sort_values('Km', ascending=False)
    
    html = '<div class="kpi-grid">'
    for _, r in stats.iterrows():
        icon = '🚲' if r['Type'] in ['Fiets', 'Virtueel'] else '👟'
        html += f"""<div class="kpi-card" style="padding:15px;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
                <span style="font-size:20px;">{icon}</span>
                <strong style="font-size:13px;">{r['Gear']}</strong>
            </div>
            <div style="font-size:18px;font-weight:700;color:{COLORS['primary']}">{r['Km']:,.0f} km</div>
            <div style="font-size:11px;color:{COLORS['text_light']}">{r['Count']} activiteiten</div>
        </div>"""
    return html + "</div>"

def generate_kpi(lbl, val, icon, diff_html):
    return f"""<div class="kpi-card">
        <div style="display:flex;justify-content:space-between;align-items:start">
            <div style="font-size:11px;color:#64748b;font-weight:700;text-transform:uppercase">{lbl}</div>
            <div style="font-size:16px;">{icon}</div>
        </div>
        <div style="font-size:24px;font-weight:700;color:#0f172a;margin:5px 0">{val}</div>
        <div style="font-size:12px;">{diff_html}</div>
    </div>"""

# --- MAIN ---
def genereer_dashboard():
    print("🚀 Start V41.0 (Alles-in-een Herstel)...")
    try:
        # INLEZEN
        df = pd.read_csv('activities.csv')
        
        # KOLOMMEN HERNOEMEN
        nm = {'Datum van activiteit':'Datum', 'Naam activiteit':'Naam', 'Activiteitstype':'Activiteitstype', 
              'Beweegtijd':'Beweegtijd_sec', 'Afstand':'Afstand_km', 'Gemiddelde hartslag':'Hartslag', 
              'Gemiddelde snelheid':'Gem_Snelheid', 'Uitrusting voor activiteit':'Gear'}
        df = df.rename(columns={k:v for k,v in nm.items() if k in df.columns})
        
        # GETALLEN FIXEN
        for c in ['Afstand_km', 'Beweegtijd_sec', 'Gem_Snelheid']:
            if c in df.columns: df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        df['Hartslag'] = pd.to_numeric(df['Hartslag'], errors='coerce')
        
        # DATUM & CATEGORIE
        df['Datum'] = df['Datum'].apply(parse_dutch_date)
        df = df.dropna(subset=['Datum']) # Nu veilig om te droppen, want parse is robuust
        df['Categorie'] = df.apply(determine_category, axis=1)
        df['Jaar'] = df['Datum'].dt.year
        df['Day'] = df['Datum'].dt.dayofyear
        
        # Snelheid fix (m/s naar km/u indien nodig)
        if df['Gem_Snelheid'].mean() < 10: df['Gem_Snelheid'] *= 3.6
        
        print(f"✅ Data geladen. Sessies in 2025: {len(df[df['Jaar']==2025])}")
        
        # HTML BOUWEN
        years = sorted(df['Jaar'].unique(), reverse=True)
        nav, sects = "", ""
        stats_box = generate_stats_box(df, datetime.now().year)
        
        for yr in years:
            df_yr = df[df['Jaar'] == yr]
            df_prev = df[df['Jaar'] == yr-1]
            # Vergelijking zelfde periode (Year-To-Date)
            ytd = datetime.now().timetuple().tm_yday
            df_prev_comp = df_prev[df_prev['Day'] <= ytd] if yr == datetime.now().year else df_prev
            
            nav += f'<button class="nav-btn {"active" if yr == datetime.now().year else ""}" onclick="openTab(event, \'v-{yr}\')">{yr}</button>'
            
            sects += f"""<div id="v-{yr}" class="tab-content" style="display:{"block" if yr == datetime.now().year else "none"}">
                <h2 class="sec-title">Overzicht {yr}</h2>
                <div class="kpi-grid">
                    {generate_kpi("Sessies", len(df_yr), "🔥", format_diff_html(len(df_yr), len(df_prev_comp)))}
                    {generate_kpi("Totaal Afstand", f"{df_yr['Afstand_km'].sum():,.0f} km", "📏", format_diff_html(df_yr['Afstand_km'].sum(), df_prev_comp['Afstand_km'].sum(), "km"))}
                    {generate_kpi("Tijd", format_time(df_yr['Beweegtijd_sec'].sum()), "⏱️", "")}
                </div>
                
                <h3 class="sec-sub">Stats per Sport</h3>
                {generate_sport_cards(df_yr, df_prev_comp)}
                
                <h3 class="sec-sub">Maandelijkse Voortgang</h3>
                {create_monthly_charts(df_yr, df_prev, yr)}
                
                <h3 class="sec-sub">Records {yr}</h3>
                {generate_hall_of_fame(df_yr)}
            </div>"""
            
        # TOTAAL & GARAGE TAB
        nav += '<button class="nav-btn" onclick="openTab(event, \'v-Tot\')">Carrière</button>'
        sects += f'<div id="v-Tot" class="tab-content" style="display:none"><h2 class="sec-title">All-Time Records</h2>{generate_hall_of_fame(df)}<h2 class="sec-title" style="margin-top:30px">De Garage</h2>{generate_gear_section(df)}</div>'
        
        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Dashboard</title><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet"><style>
        :root{{--primary:#0f172a;--bg:#f8fafc;--card:#ffffff;--text:#1e293b;--label:#94a3b8}}
        body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);margin:0;padding:15px;padding-bottom:60px}}
        .container{{max-width:800px;margin:0 auto}}
        .gold-banner{{background:linear-gradient(135deg, #d4af37 0%, #f59e0b 100%);color:white;padding:15px;border-radius:12px;margin-bottom:20px;font-weight:700;display:flex;align-items:center;cursor:pointer}}
        .nav{{display:flex;gap:8px;overflow-x:auto;margin-bottom:20px;padding-bottom:5px;scrollbar-width:none}}
        .nav-btn{{flex:0 0 auto;background:white;border:1px solid #e2e8f0;padding:8px 16px;border-radius:20px;font-size:13px;font-weight:600;color:#64748b;cursor:pointer}}
        .nav-btn.active{{background:var(--primary);color:white;border-color:var(--primary)}}
        
        .stats-box-container{{display:flex;gap:15px;margin-bottom:25px;flex-wrap:wrap}}
        .goals-section, .streaks-section{{flex:1;background:white;padding:15px;border-radius:16px;border:1px solid #e2e8f0;min-width:280px}}
        .box-title{{font-size:11px;color:var(--label);text-transform:uppercase;margin-bottom:12px;letter-spacing:1px;font-weight:700}}
        .goal-item{{margin-bottom:10px}}.goal-label{{display:flex;justify-content:space-between;font-size:12px;font-weight:600;margin-bottom:4px}}
        .goal-bar{{background:#f1f5f9;height:6px;border-radius:3px;overflow:hidden}}.goal-bar div{{height:100%;border-radius:3px}}
        .streak-row{{display:flex;justify-content:space-between;margin-bottom:4px;font-size:13px}}.streak-row .val{{font-weight:700;color:var(--primary)}}
        
        .kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:10px;margin-bottom:25px}}
        .kpi-card{{background:white;padding:15px;border-radius:16px;border:1px solid #e2e8f0}}
        
        .sport-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:15px;margin-bottom:25px}}
        .sport-card{{background:white;padding:15px;border-radius:16px;border:1px solid #e2e8f0}}
        .sport-header{{display:flex;align-items:center;gap:10px;margin-bottom:12px;font-size:16px}}
        .icon-circle{{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center}}
        .stat-row{{display:flex;justify-content:space-between;margin-bottom:6px;font-size:13px;color:#64748b}}
        .stat-row strong{{color:var(--text)}} .val-group{{display:flex;gap:6px;align-items:center}}
        
        .hof-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin-bottom:20px}}
        .hof-card{{background:white;padding:15px;border-radius:16px;border:1px solid #e2e8f0}}
        .hof-sec{{margin-bottom:12px}} .sec-lbl{{font-size:9px;color:var(--label);text-transform:uppercase;font-weight:700;margin-bottom:4px}}
        .top3-item{{display:flex;justify-content:space-between;font-size:12px;margin-bottom:2px}}
        .medal{{margin-right:5px}} .t3-val{{font-weight:600}} .t3-date{{color:var(--label);font-size:10px}}
        
        .sec-title{{font-size:20px;font-weight:700;margin-bottom:15px}}
        .sec-sub{{font-size:12px;color:var(--label);text-transform:uppercase;font-weight:700;margin:25px 0 10px 0;letter-spacing:1px}}
        .chart-box{{background:white;padding:15px;border-radius:16px;border:1px solid #e2e8f0}}
        .full-width{{width:100%;box-sizing:border-box}}
        </style></head><body><div class="container">
        <div class="gold-banner" onclick="window.location.reload()">🏆 Sport Dashboard Jorden</div>
        {stats_box}<div class="nav">{nav}</div>{sects}</div>
        <script>
        function openTab(e,n){{
            document.querySelectorAll('.tab-content').forEach(x=>x.style.display='none');
            document.querySelectorAll('.nav-btn').forEach(x=>x.classList.remove('active'));
            document.getElementById(n).style.display='block'; e.currentTarget.classList.add('active');
        }}
        </script></body></html>"""
        
        with open('dashboard.html', 'w', encoding='utf-8') as f: f.write(html)
        print("✅ Dashboard (V41.0) gegenereerd!")

    except Exception as e:
        print(f"❌ Fout: {e}")

if __name__ == "__main__":
    genereer_dashboard()
