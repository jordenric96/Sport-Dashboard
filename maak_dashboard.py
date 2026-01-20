import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime
import json
import os

# --- CONFIGURATIE ---
COLORS = {
    'primary': '#0f172a', 
    'gold': '#d4af37', 
    'silver': '#94a3b8', 
    'bronze': '#b45309',
    'bg': '#f8fafc', 
    'card': '#ffffff', 
    'text': '#1e293b', 
    'text_light': '#64748b',
    'success': '#10b981', 
    'danger': '#ef4444', 
    'chart_main': '#3b82f6', 
    'chart_sub': '#06b6d4', 
    'chart_sec': '#cbd5e1'
}

SPORT_CONFIG = {
    'Fiets': {'icon': '🚴', 'color': '#0ea5e9'},
    'Virtuele fietsrit': {'icon': '👾', 'color': '#6366f1'},
    'Hardloop': {'icon': '🏃', 'color': '#f59e0b'},
    'Wandel': {'icon': '🚶', 'color': '#10b981'},
    'Padel': {'icon': '🎾', 'color': '#84cc16'},
    'Zwemmen': {'icon': '🏊', 'color': '#3b82f6'},
    'Default': {'icon': '🏅', 'color': '#64748b'}
}

def get_sport_style(sport_name):
    for key, config in SPORT_CONFIG.items():
        if key.lower() in str(sport_name).lower(): return config
    return SPORT_CONFIG['Default']

def format_time(seconds):
    if pd.isna(seconds) or seconds <= 0: return '-'
    h, r = divmod(int(seconds), 3600)
    m, _ = divmod(r, 60)
    return f'{h}u {m:02d}m'

def format_diff_html(cur, prev, unit=""):
    if pd.isna(prev): prev = 0
    diff = cur - prev
    if diff == 0: return '<span class="diff-neutral">-</span>'
    color = COLORS['success'] if diff > 0 else COLORS['danger']
    arrow = "▲" if diff > 0 else "▼"
    return f'<span style="color:{color}; background:{color}15; padding:2px 6px; border-radius:4px; font-weight:700; font-size:0.85em;">{arrow} {abs(diff):.1f} {unit}</span>'

def robust_date_parser(date_series):
    # Stap 1: Probeer direct te parsen (voor ISO formaten)
    # We zetten errors='coerce' zodat foute formaten NaT worden (en geen crash veroorzaken)
    dates = pd.to_datetime(date_series, errors='coerce')
    
    # Stap 2: Als er veel NaT zijn (waarschijnlijk Nederlandse maanden), probeer tekstuele vervanging
    if dates.isna().sum() > len(dates) * 0.5: # Als meer dan 50% faalt
        dutch = {'jan': 'Jan', 'feb': 'Feb', 'mrt': 'Mar', 'apr': 'Apr', 'mei': 'May', 'jun': 'Jun', 'jul': 'Jul', 'aug': 'Aug', 'sep': 'Sep', 'okt': 'Oct', 'nov': 'Nov', 'dec': 'Dec'}
        ds = date_series.astype(str).str.lower()
        for nl, en in dutch.items(): 
            ds = ds.str.replace(nl, en, regex=False)
        # Forceer format dag-maand-jaar voor Strava CSV stijl
        dates = pd.to_datetime(ds, format='%d %b %Y, %H:%M:%S', errors='coerce')
    
    return dates

# --- HTML GENERATOREN ---

def generate_kpi(title, val, icon="", diff=""):
    return f"""
    <div class="kpi-card">
        <div class="kpi-icon-box">{icon}</div>
        <div class="kpi-content">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{val}</div>
            <div class="kpi-sub">{diff}</div>
        </div>
    </div>
    """

def generate_sport_cards(df_cur, df_prev):
    html = '<div class="sport-grid">'
    for sport in sorted(df_cur['Activiteitstype'].unique()):
        dfs = df_cur[df_cur['Activiteitstype'] == sport]
        
        dfp = pd.DataFrame()
        if df_prev is not None and not df_prev.empty:
            dfp = df_prev[df_prev['Activiteitstype'] == sport]
        
        st = get_sport_style(sport)
        n = len(dfs)
        dist = dfs['Afstand_km'].sum()
        tm = dfs['Beweegtijd_sec'].sum()
        
        pn = len(dfp)
        pdist = dfp['Afstand_km'].sum() if not dfp.empty else 0
        
        dist_html = f'<div class="stat-col"><div class="label">Km</div><div class="val">{dist:,.0f}</div><div class="sub">{format_diff_html(dist, pdist, "km")}</div></div>'
        if sport == 'Padel': 
            dist_html = '<div class="stat-col" style="opacity:0.3"><div class="label">Km</div><div class="val">-</div></div>'
        
        hr = dfs['Gemiddelde_Hartslag'].mean()
        hr_html = f'<div class="stat-row"><span>Hartslag</span> <strong class="hr-blur">{hr:.0f}</strong></div>' if pd.notna(hr) else ""

        html += f"""
        <div class="sport-card">
            <div class="sport-header">
                <div class="sport-icon-circle" style="color:{st['color']};background:{st['color']}20">{st['icon']}</div>
                <h3>{sport}</h3>
            </div>
            <div class="sport-body">
                <div class="stat-main">
                    <div class="stat-col">
                        <div class="label">Sessies</div>
                        <div class="val">{n}</div>
                        <div class="sub">{format_diff_html(n, pn)}</div>
                    </div>
                    <div class="stat-divider"></div>
                    {dist_html}
                </div>
                <div class="sport-details">
                    <div class="stat-row"><span>Tijd</span> <strong>{format_time(tm)}</strong></div>
                    {hr_html}
                </div>
            </div>
        </div>
        """
    return html + '</div>'

def generate_gear_section(df):
    if 'Uitrusting voor activiteit' not in df.columns: 
        return "<p>Geen kolom 'Uitrusting voor activiteit'</p>"
    
    dfg = df.copy()
    dfg['Uitrusting voor activiteit'] = dfg['Uitrusting voor activiteit'].fillna('').astype(str)
    dfg = dfg[dfg['Uitrusting voor activiteit'].str.strip() != '']
    dfg = dfg[dfg['Uitrusting voor activiteit'].str.lower() != 'nan']
    
    if dfg.empty: 
        return "<p style='color:#999; text-align:center'>Geen uitrusting gevonden in de CSV.</p>"
    
    stats = dfg.groupby('Uitrusting voor activiteit').agg(
        Count=('Activiteitstype','count'), 
        Km=('Afstand_km','sum'), 
        Type=('Activiteitstype', lambda x: x.mode()[0] if not x.mode().empty else 'Onbekend')
    ).reset_index().sort_values('Km', ascending=False)
    
    html = '<div class="kpi-grid">'
    for _, r in stats.iterrows():
        icon = '🚲' if 'Fiets' in str(r['Type']) else '👟'
        max_k = 10000 if icon == '🚲' else 1000
        pct = min(100, (r['Km']/max_k)*100)
        col = COLORS['success'] if pct < 50 else (COLORS['gold'] if pct < 80 else COLORS['danger'])
        
        fun_txt = ""
        if icon == '👟':
            if r['Km'] > 800: fun_txt = "💀 Tijd voor nieuwe?"
            elif r['Km'] < 100: fun_txt = "✨ Inlopen"
            else: fun_txt = "🔥 Going strong"
        else:
            if r['Km'] > 15000: fun_txt = "🔧 Check ketting"
            else: fun_txt = "🚴 Lekker bezig"

        html += f"""
        <div class="kpi-card" style="display:block; padding:20px;">
            <div style="display:flex;align-items:center;gap:15px;margin-bottom:15px">
                <div style="font-size:28px;background:#f1f5f9;width:54px;height:54px;display:flex;align-items:center;justify-content:center;border-radius:12px">{icon}</div>
                <div>
                    <div style="font-weight:700;font-size:15px;color:{COLORS['text']};margin-bottom:4px;line-height:1.2">{r['Uitrusting voor activiteit']}</div>
                    <div style="font-size:12px;color:{COLORS['text_light']}">{r['Count']} activiteiten</div>
                </div>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:end;margin-bottom:10px">
                <div style="font-size:22px;font-weight:700;color:{COLORS['primary']}">{r['Km']:,.0f} <span style="font-size:14px;color:{COLORS['text_light']};font-weight:500">km</span></div>
                <div style="font-size:11px;font-weight:600;color:{col}">{fun_txt}</div>
            </div>
            <div style="background:#e2e8f0;height:6px;border-radius:3px;overflow:hidden">
                <div style="width:{pct}%;background:{col};height:100%"></div>
            </div>
        </div>"""
    return html + '</div>'

def generate_top3_list(df, col, unit, ascending=False, is_pace=False):
    df_sorted = df.sort_values(col, ascending=ascending).head(3)
    if df_sorted.empty: return ""
    
    html = '<div class="top3-list">'
    medals = ['🥇', '🥈', '🥉']
    for i, (idx, row) in enumerate(df_sorted.iterrows()):
        val = row[col]
        if is_pace:
            pace_sec = 3600 / val if val > 0 else 0
            val_str = f"{int(pace_sec//60)}:{int(pace_sec%60):02d} /km"
        else:
            val_str = f"{val:.1f} {unit}"
            if unit == 'u': val_str = format_time(val)
            
        html += f"""
        <div class="top3-item">
            <span class="medal">{medals[i]}</span>
            <span class="top3-val">{val_str}</span>
            <span class="top3-date">{row['Datum'].strftime('%d %b')}</span>
        </div>
        """
    html += '</div>'
    return html

def generate_hall_of_fame(df):
    html = '<div class="hof-grid">'
    sports = sorted(df['Activiteitstype'].unique())
    
    for sport in sports:
        if sport == 'Padel': continue
        
        df_s = df[(df['Activiteitstype'] == sport) & (df['Afstand_km'] > 1.0)]
        if df_s.empty: continue
        
        style = get_sport_style(sport)
        
        t3_dist = generate_top3_list(df_s, 'Afstand_km', 'km', ascending=False)
        
        t3_speed = ""
        if 'Fiets' in sport:
            df_spd = df_s[df_s['Gemiddelde_Snelheid_km_u'] > 10]
            t3_speed = generate_top3_list(df_spd, 'Gemiddelde_Snelheid_km_u', 'km/u', ascending=False)
        elif 'Hardloop' in sport:
            df_spd = df_s[(df_s['Gemiddelde_Snelheid_km_u'] > 5) & (df_s['Gemiddelde_Snelheid_km_u'] < 25)]
            t3_speed = generate_top3_list(df_spd, 'Gemiddelde_Snelheid_km_u', '', ascending=False, is_pace=True)
            
        t3_time = generate_top3_list(df_s, 'Beweegtijd_sec', 'u', ascending=False)
        
        html += f"""
        <div class="hof-card">
            <div class="hof-header" style="color:{style['color']}">
                <span style="font-size:20px;margin-right:8px">{style['icon']}</span> {sport}
            </div>
            <div class="hof-section">
                <div class="hof-label">Langste Afstand</div>
                {t3_dist}
            </div>
            <div class="hof-section">
                <div class="hof-label">Snelste (Gem.)</div>
                {t3_speed if t3_speed else '<span style="color:#ccc;font-size:11px">-</span>'}
            </div>
            <div class="hof-section" style="border:none">
                <div class="hof-label">Langste Duur</div>
                {t3_time}
            </div>
        </div>
        """
    html += "</div>"
    return html

def generate_detail_table(df, uid):
    if df.empty: return "<p style='text-align:center;color:#999'>Geen activiteiten dit jaar.</p>"
    
    opts = "".join([f'<option value="{s}">{s}</option>' for s in sorted(df['Activiteitstype'].unique())])
    rows = ""
    for _, r in df.sort_values('Datum', ascending=False).iterrows():
        st = get_sport_style(r['Activiteitstype'])
        hr = f"{r['Gemiddelde_Hartslag']:.0f}" if pd.notna(r['Gemiddelde_Hartslag']) else "-"
        rows += f'<tr data-sport="{r["Activiteitstype"]}"><td><div style="width:8px;height:8px;border-radius:50%;background:{st["color"]}"></div></td><td>{r["Datum"].strftime("%d-%m-%y")}</td><td>{r["Activiteitstype"]}</td><td>{r["Naam"]}</td><td class="num">{r["Afstand_km"]:.1f}</td><td class="num hr-blur">{hr}</td></tr>'

    return f"""
    <div class="detail-section">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px">
            <h3 style="margin:0;font-size:16px;">Logboek</h3>
            <select id="sf-{uid}" onchange="filterTable('{uid}')" style="padding:5px;border-radius:6px;border:1px solid #ddd">
                <option value="ALL">Alles</option>{opts}
            </select>
        </div>
        <div style="overflow-x:auto">
            <table id="dt-{uid}">
                <thead><tr><th></th><th>Datum</th><th>Type</th><th>Naam</th><th class="num">Km</th><th class="num">❤️</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </div>
    """

def genereer_manifest():
    m = {
        "name":"Sport Jorden",
        "short_name":"Sport",
        "start_url":"./dashboard.html",
        "display":"standalone",
        "background_color":"#f8fafc",
        "theme_color":"#0f172a",
        "icons":[{"src":"1768922516256~2.jpg","sizes":"512x512","type":"image/jpeg"}]
    }
    with open('manifest.json', 'w') as f: json.dump(m, f)

# --- MAIN ---
def genereer_dashboard():
    print("🚀 Start V14.1 (Crash Fix)...")
    try: 
        df = pd.read_csv('activities.csv')
    except: 
        print("❌ Geen activities.csv gevonden!")
        return

    nm = {
        'Datum van activiteit':'Datum',
        'Activiteitstype':'Activiteitstype',
        'Beweegtijd':'Beweegtijd_sec',
        'Afstand':'Afstand_km',
        'Totale stijging':'Hoogte_m',
        'Gemiddelde hartslag':'Gemiddelde_Hartslag',
        'Uitrusting voor activiteit':'Uitrusting voor activiteit'
    }
    df = df.rename(columns={k:v for k,v in nm.items() if k in df.columns})
    
    for c in ['Afstand_km','Hoogte_m','Gemiddelde_Hartslag']:
        if c in df.columns: 
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(',','.'), errors='coerce')
    
    df.loc[df['Activiteitstype'].str.contains('Training|Workout|Fitness', case=False, na=False), 'Activiteitstype'] = 'Padel'
    df.loc[df['Activiteitstype'].str.contains('Zwemmen', case=False, na=False), 'Afstand_km'] /= 1000

    # Datums parse
    df['Datum'] = robust_date_parser(df['Datum'])
    df['Jaar'] = df['Datum'].dt.year
    df['DagVanJaar'] = df['Datum'].dt.dayofyear
    
    genereer_manifest()
    
    nav, sects = "", ""
    
    # HIER ZAT DE FOUT: Nu gebruiken we timetuple().tm_yday
    today_doy = datetime.now().timetuple().tm_yday
    
    years = sorted(df['Jaar'].dropna().unique(), reverse=True)
    
    for yr in years:
        is_current_year = (yr == datetime.now().year)
        df_yr = df[df['Jaar'] == yr]
        
        df_prev_yr = df[df['Jaar'] == yr-1]
        if is_current_year:
            df_prev_comp = df_prev_yr[df_prev_yr['DagVanJaar'] <= today_doy]
        else:
            df_prev_comp = df_prev_yr
        
        sc = {
            'n': len(df_yr), 
            'km': df_yr['Afstand_km'].sum(), 
            'h': df_yr['Hoogte_m'].sum(), 
            't': df_yr['Beweegtijd_sec'].sum()
        }
        sp = {
            'n': len(df_prev_comp), 
            'km': df_prev_comp['Afstand_km'].sum(), 
            'h': df_prev_comp['Hoogte_m'].sum(), 
            't': df_prev_comp['Beweegtijd_sec'].sum()
        }
        
        kpis = f"""
        <div class="kpi-grid">
            {generate_kpi("Sessies", sc['n'], "🔥", format_diff_html(sc['n'], sp['n']))}
            {generate_kpi("Afstand", f"{sc['km']:,.0f} km", "📏", format_diff_html(sc['km'], sp['km'], "km"))}
            {generate_kpi("Hoogtemeters", f"{sc['h']:,.0f} m", "⛰️", format_diff_html(sc['h'], sp['h'], "m"))}
            {generate_kpi("Tijd", format_time(sc['t']), "⏱️", format_diff_html((sc['t']-sp['t'])/3600, 0, "u"))}
        </div>
        """
        
        df_cum = df_yr.sort_values('DagVanJaar')
        df_cum['C'] = df_cum['Afstand_km'].cumsum()
        
        df_real = df_yr[df_yr['Activiteitstype'] != 'Virtuele fietsrit'].sort_values('DagVanJaar')
        df_real['C'] = df_real['Afstand_km'].cumsum()
        
        df_prev_cum = df[df['Jaar'] == yr-1].sort_values('DagVanJaar')
        if is_current_year: 
            df_prev_cum = df_prev_cum[df_prev_cum['DagVanJaar'] <= today_doy]
        df_prev_cum['C'] = df_prev_cum['Afstand_km'].cumsum()
        
        fig = px.line(title=f"Koersverloop {yr}")
        fig.add_scatter(x=df_cum['DagVanJaar'], y=df_cum['C'], name=f"Totaal {yr}", line_color=COLORS['chart_main'], line_width=3)
        
        if len(df_real) > 0 and sc['km'] != df_real['Afstand_km'].sum():
             fig.add_scatter(x=df_real['DagVanJaar'], y=df_real['C'], name=f"Buiten (Real)", line_color=COLORS['chart_sub'], line_dash='dot', line_width=2)
        
        if not df_prev_cum.empty: 
            fig.add_scatter(x=df_prev_cum['DagVanJaar'], y=df_prev_cum['C'], name=f"{yr-1} (YTD)", line_color=COLORS['chart_sec'], line_dash='dot')
            
        fig.update_layout(template='plotly_white', margin=dict(t=30,b=20,l=20,r=20), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=1.1))
        
        top3_html = f'<h3 class="section-subtitle">Top Prestaties {yr}</h3>{generate_hall_of_fame(df_yr)}'
        tbl = generate_detail_table(df_yr, str(yr))

        nav += f'<button class="nav-btn {"active" if is_current_year else ""}" onclick="openTab(event, \'v-{yr}\')">{yr}</button>'
        
        display_style = "block" if is_current_year else "none"
        sects += f"""
        <div id="v-{yr}" class="tab-content" style="display:{display_style}">
            <h2 class="section-title">Overzicht {yr}</h2>
            {kpis}
            <h3 class="section-subtitle">Per Sport</h3>
            {generate_sport_cards(df_yr, df_prev_comp)}
            <div class="chart-box full-width">{fig.to_html(full_html=False, include_plotlyjs="cdn")}</div>
            {top3_html}
            {tbl}
        </div>
        """

    tbl_tot = generate_detail_table(df, "Tot")
    nav += '<button class="nav-btn" onclick="openTab(event, \'v-Tot\')">Totaal</button>'
    sects += f"""
    <div id="v-Tot" class="tab-content" style="display:none">
        <h2 class="section-title">Carrière</h2>
        <div class="kpi-grid">
            {generate_kpi("Sessies", len(df), "🏆")}
            {generate_kpi("Km", f"{df['Afstand_km'].sum():,.0f}", "🌍")}
            {generate_kpi("Tijd", format_time(df['Beweegtijd_sec'].sum()), "⏱️")}
        </div>
        {generate_sport_cards(df, pd.DataFrame())}
        {tbl_tot}
    </div>
    """
    
    nav += '<button class="nav-btn" onclick="openTab(event, \'v-Gar\')">Garage</button>'
    sects += f'<div id="v-Gar" class="tab-content" style="display:none"><h2 class="section-title">De Garage</h2>{generate_gear_section(df)}</div>'
    
    nav += '<button class="nav-btn" onclick="openTab(event, \'v-HOF\')">Records</button>'
    sects += f'<div id="v-HOF" class="tab-content" style="display:none"><h2 class="section-title">All-Time Eregalerij</h2>{generate_hall_of_fame(df)}</div>'

    html = f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"><link rel="manifest" href="manifest.json"><link rel="apple-touch-icon" href="1768922516256~2.jpg"><title>Sport Jorden</title><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet"><style>:root{{--primary:{COLORS['primary']};--gold:{COLORS['gold']};--bg:{COLORS['bg']};--card:{COLORS['card']};--text:{COLORS['text']}}}body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);margin:0;padding:20px;padding-bottom:80px;-webkit-tap-highlight-color:transparent}}.container{{max-width:1000px;margin:0 auto}}h1{{margin:0;font-size:24px;font-weight:700;color:var(--primary);display:flex;align-items:center;gap:10px}}h1::after{{content:'';display:block;width:40px;height:3px;background:var(--gold);border-radius:2px}}.header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}}.lock-btn{{background:white;border:1px solid #cbd5e1;padding:6px 12px;border-radius:20px;font-size:13px;font-weight:600;color:#64748b;transition:0.2s}}.nav{{display:flex;gap:8px;overflow-x:auto;padding-bottom:10px;margin-bottom:20px;scrollbar-width:none}}.nav::-webkit-scrollbar{{display:none}}.nav-btn{{flex:0 0 auto;background:white;border:1px solid #e2e8f0;padding:8px 16px;border-radius:20px;font-size:14px;font-weight:600;color:#64748b;transition:0.2s}}.nav-btn.active{{background:var(--primary);color:white;border-color:var(--primary)}}.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:25px}}.sport-grid,.hof-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:15px;margin-bottom:25px}}.kpi-card,.sport-card,.chart-box,.detail-section,.hof-card{{background:var(--card);border-radius:16px;padding:16px;box-shadow:0 2px 4px rgba(0,0,0,0.03);border:1px solid #f1f5f9}}.sport-header{{display:flex;align-items:center;gap:10px;margin-bottom:12px}}.sport-icon-circle{{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px}}.stat-main{{display:flex;margin-bottom:12px}}.stat-col{{flex:1}}.stat-divider{{width:1px;background:#e2e8f0;margin:0 12px}}.label{{font-size:10px;text-transform:uppercase;color:#94a3b8;font-weight:700}}.val{{font-size:18px;font-weight:700;color:var(--primary)}}.sub{{font-size:11px;margin-top:2px}}.sport-details{{background:#f8fafc;padding:10px;border-radius:8px;font-size:12px}}.stat-row{{display:flex;justify-content:space-between;margin-bottom:4px;color:#64748b}}.stat-row strong{{color:var(--text)}}table{{width:100%;border-collapse:collapse;font-size:13px}}th{{text-align:left;color:#94a3b8;font-size:10px;text-transform:uppercase;padding:10px}}td{{padding:10px;border-bottom:1px solid #f1f5f9}}.num{{text-align:right;font-weight:600}}.hr-blur{{filter:blur(4px);background:#e2e8f0;border-radius:4px;color:transparent;transition:0.3s}}.section-title{{font-size:18px;font-weight:700;margin-bottom:15px;color:var(--primary)}}.section-subtitle{{font-size:12px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin:25px 0 10px 0}}
        .hof-card {{ display:flex; flex-direction:column; gap:12px; }}
        .hof-section {{ border-bottom:1px solid #f1f5f9; padding-bottom:8px; }}
        .hof-label {{ font-size:10px; text-transform:uppercase; color:#94a3b8; font-weight:700; margin-bottom:6px; }}
        .top3-list {{ display:flex; flex-direction:column; gap:6px; }}
        .top3-item {{ display:flex; justify-content:space-between; align-items:center; font-size:13px; }}
        .medal {{ font-size:14px; margin-right:6px; }}
        .top3-val {{ font-weight:700; color:var(--text); }}
        .top3-date {{ font-size:11px; color:#94a3b8; }}
        </style></head><body><div class="container"><div class="header"><h1>Sport Jorden</h1><button class="lock-btn" onclick="unlock()">❤️ 🔒</button></div><div class="nav">{nav}</div>{sects}</div><script>function openTab(e,n){{document.querySelectorAll('.tab-content').forEach(x=>x.style.display='none');document.querySelectorAll('.nav-btn').forEach(x=>x.classList.remove('active'));document.getElementById(n).style.display='block';e.currentTarget.classList.add('active')}}function filterTable(uid){{var v=document.getElementById('sf-'+uid).value;document.querySelectorAll('#dt-'+uid+' tbody tr').forEach(tr=>tr.style.display=(v==='ALL'||tr.dataset.sport===v)?'':'none')}}function unlock(){{if(prompt("Wachtwoord:")==='Nala'){{document.querySelectorAll('.hr-blur').forEach(e=>{{e.style.filter='none';e.style.color='inherit';e.style.background='transparent'}});document.querySelector('.lock-btn').style.display='none'}}}}</script></body></html>"""
    
    with open('dashboard.html', 'w', encoding='utf-8') as f: f.write(html)
    print("✅ Dashboard (V14.1) gegenereerd: Validated.")

if __name__ == "__main__":
    genereer_dashboard()
