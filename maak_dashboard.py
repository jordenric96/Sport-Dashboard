import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime

# --- CONFIGURATIE: LUXE / CALM STYLE ---
COLORS = {
    'primary': '#1e293b',       # Midnight Blue (Luxe basis)
    'accent': '#d4af37',        # Muted Gold (Accent)
    'bg': '#f8fafc',            # Heel licht grijs/blauw (Rustgevende achtergrond)
    'card': '#ffffff',          # Wit
    'text': '#334155',          # Slate Grey (Zachter dan zwart)
    'text_light': '#64748b',    # Muted text
    'success': '#10b981',       # Zacht groen
    'danger': '#ef4444',        # Zacht rood
    'chart_main': '#3b82f6',    # Mooi blauw voor grafieken
    'chart_sec': '#cbd5e1'      # Grijs voor vergelijkingen
}

# Sport Config (Rustigere kleuren)
SPORT_CONFIG = {
    'Fiets': {'icon': '🚴', 'color': '#0ea5e9'},       # Sky Blue
    'Virtuele fietsrit': {'icon': '👾', 'color': '#6366f1'}, # Indigo
    'Hardloop': {'icon': '🏃', 'color': '#f59e0b'},    # Amber/Gold
    'Wandel': {'icon': '🚶', 'color': '#10b981'},      # Emerald
    'Padel': {'icon': '🎾', 'color': '#84cc16'},       # Lime (maar zacht)
    'Hike': {'icon': '🥾', 'color': '#06b6d4'},        # Cyan
    'Zwemmen': {'icon': '🏊', 'color': '#3b82f6'},      # Blue
    'Default': {'icon': '🏅', 'color': '#64748b'}       # Slate
}

def get_sport_style(sport_name):
    for key, config in SPORT_CONFIG.items():
        if key.lower() in str(sport_name).lower():
            return config
    return SPORT_CONFIG['Default']

# --- HULPFUNCTIES ---
def format_time(seconds):
    if pd.isna(seconds) or seconds <= 0: return '-'
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f'{hours}u {minutes:02d}m'

def format_diff_html(current, previous, unit="", inverse=False):
    if pd.isna(previous) or previous == 0:
        return '<span class="diff-neutral">Start</span>'
    diff = current - previous
    if diff == 0: return '<span class="diff-neutral">-</span>'
    
    is_good = (diff > 0) if not inverse else (diff < 0)
    color = COLORS['success'] if is_good else COLORS['danger']
    arrow = "▲" if diff > 0 else "▼"
    val_str = f"{abs(diff):.1f}" if isinstance(diff, float) else f"{abs(int(diff))}"
    
    # Luxe badge style
    bg_color = f"{color}15" # 15 is hex opacity (~10%)
    return f'<span style="color: {color}; background: {bg_color}; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.8em;">{arrow} {val_str} {unit}</span>'

def robust_date_parser(date_series):
    dutch_month_mapping = {
        'jan': 'Jan', 'feb': 'Feb', 'mrt': 'Mar', 'apr': 'Apr', 
        'mei': 'May', 'jun': 'Jun', 'jul': 'Jul', 'aug': 'Aug', 
        'sep': 'Sep', 'okt': 'Oct', 'nov': 'Nov', 'dec': 'Dec'
    }
    date_series_str = date_series.astype(str).str.lower()
    for dutch, eng in dutch_month_mapping.items():
        date_series_str = date_series_str.str.replace(dutch, eng, regex=False)
    dates = pd.to_datetime(date_series_str, format='%d %b %Y, %H:%M:%S', errors='coerce')
    mask = dates.isna()
    if mask.any():
        dates[mask] = pd.to_datetime(date_series_str[mask], errors='coerce', dayfirst=True)
    return dates

# --- HTML GENERATORS ---

def generate_kpi(title, value, subtext="", icon="", diff=""):
    return f"""
    <div class="kpi-card">
        <div class="kpi-icon-box">{icon}</div>
        <div class="kpi-content">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{diff} <span style="margin-left: 5px;">{subtext}</span></div>
        </div>
    </div>
    """

def generate_sport_cards(df_cur, df_prev):
    html = '<div class="sport-grid">'
    sports = sorted(df_cur['Activiteitstype'].unique())
    
    for sport in sports:
        df_s_cur = df_cur[df_cur['Activiteitstype'] == sport]
        if df_prev is not None and not df_prev.empty:
            df_s_prev = df_prev[df_prev['Activiteitstype'] == sport]
            prev_count = len(df_s_prev)
            prev_dist = df_s_prev['Afstand_km'].sum()
        else:
            prev_count = 0
            prev_dist = 0
            
        style = get_sport_style(sport)
        count = len(df_s_cur)
        dist = df_s_cur['Afstand_km'].sum()
        time = df_s_cur['Beweegtijd_sec'].sum()
        avg_hr = df_s_cur['Gemiddelde_Hartslag'].mean()
        
        diff_count = format_diff_html(count, prev_count)
        diff_dist = format_diff_html(dist, prev_dist, "km")
        
        # Hall of Fame achtige stat in de card
        extra_stat = ""
        if 'Fiets' in sport:
            # We gebruiken nu GEMIDDELDE snelheid voor de max, om GPS glitches te voorkomen
            max_spd = df_s_cur['Gemiddelde_Snelheid_km_u'].max() 
            if max_spd > 0: extra_stat = f'<div class="stat-row"><span>Snelste rit (gem.)</span> <strong>{max_spd:.1f} km/u</strong></div>'
        else:
            max_dst = df_s_cur['Afstand_km'].max()
            if max_dst > 0: extra_stat = f'<div class="stat-row"><span>Langste sessie</span> <strong>{max_dst:.1f} km</strong></div>'
        
        hr_html = ""
        if pd.notna(avg_hr) and avg_hr > 0:
            hr_html = f'<div class="stat-row"><span>Gem. Hartslag</span> <strong class="hr-blur">{avg_hr:.0f} bpm</strong></div>'

        html += f"""
        <div class="sport-card">
            <div class="sport-header">
                <div class="sport-icon-circle" style="background: {style['color']}20; color: {style['color']}">{style['icon']}</div>
                <h3>{sport}</h3>
            </div>
            <div class="sport-body">
                <div class="stat-main">
                    <div class="stat-col">
                        <div class="label">Sessies</div>
                        <div class="val">{count}</div>
                        <div class="sub">{diff_count}</div>
                    </div>
                    <div class="stat-divider"></div>
                    <div class="stat-col">
                        <div class="label">Afstand</div>
                        <div class="val">{dist:,.0f} <small>km</small></div>
                        <div class="sub">{diff_dist}</div>
                    </div>
                </div>
                <div class="sport-details">
                    <div class="stat-row"><span>Totaal tijd</span> <strong>{format_time(time)}</strong></div>
                    {extra_stat}
                    {hr_html}
                </div>
            </div>
        </div>
        """
    html += '</div>'
    return html

def generate_hall_of_fame(df):
    html = '<div class="hof-grid">'
    sports = sorted(df['Activiteitstype'].unique())
    
    for sport in sports:
        df_s = df[df['Activiteitstype'] == sport]
        if df_s.empty: continue
        style = get_sport_style(sport)
        records = []
        
        # LOGICA FIX: Gebruik Gemiddelde Snelheid voor 'Snelste' records, niet Max Snelheid (GPS Fouten)
        
        # 1. Langste Afstand
        idx_dist = df_s['Afstand_km'].idxmax()
        if pd.notna(idx_dist):
            row = df_s.loc[idx_dist]
            records.append({'label': 'Langste Afstand', 'val': f"{row['Afstand_km']:.1f} km", 'date': row['Datum'], 'icon': '📏'})
            
        # 2. Snelste (Gebaseerd op de beste gemiddelde snelheid van een sessie)
        if 'Fiets' in sport:
            idx_spd = df_s['Gemiddelde_Snelheid_km_u'].idxmax() # AANGEPAST: Gemiddelde ipv Max
            if pd.notna(idx_spd) and df_s.loc[idx_spd, 'Gemiddelde_Snelheid_km_u'] > 0:
                row = df_s.loc[idx_spd]
                records.append({'label': 'Hoogste Gem. Snelheid', 'val': f"{row['Gemiddelde_Snelheid_km_u']:.1f} km/u", 'date': row['Datum'], 'icon': '🚀'})
        elif 'Hardloop' in sport:
             idx_spd = df_s['Gemiddelde_Snelheid_km_u'].idxmax()
             if pd.notna(idx_spd) and df_s.loc[idx_spd, 'Gemiddelde_Snelheid_km_u'] > 0:
                row = df_s.loc[idx_spd]
                pace_sec = 3600 / row['Gemiddelde_Snelheid_km_u']
                pace = f"{int(pace_sec//60)}:{int(pace_sec%60):02d} /km"
                records.append({'label': 'Snelste Tempo (Gem.)', 'val': pace, 'date': row['Datum'], 'icon': '⚡'})

        # 3. Langste Duur
        idx_time = df_s['Beweegtijd_sec'].idxmax()
        if pd.notna(idx_time):
             row = df_s.loc[idx_time]
             records.append({'label': 'Langste Duur', 'val': format_time(row['Beweegtijd_sec']), 'date': row['Datum'], 'icon': '⏱️'})
             
        rec_html = ""
        for r in records:
            date_str = r['date'].strftime('%d %b %Y')
            rec_html += f"""
            <div class="hof-record">
                <div class="hof-icon" style="color:{style['color']}">{r['icon']}</div>
                <div class="hof-data">
                    <div class="hof-label">{r['label']}</div>
                    <div class="hof-val">{r['val']}</div>
                    <div class="hof-date">{date_str}</div>
                </div>
            </div>
            """
            
        html += f"""
        <div class="hof-card">
             <div class="hof-header">
                <h3 style="color:{style['color']}">{style['icon']} {sport}</h3>
             </div>
             <div class="hof-body">{rec_html}</div>
        </div>
        """
    html += "</div>"
    return html

def genereer_dashboard(csv_input='activities.csv', html_output='dashboard.html'):
    print("🚀 Start Generatie Luxe Dashboard...")
    try:
        df = pd.read_csv(csv_input)
    except:
        print("❌ CSV niet gevonden.")
        return

    # Renames & Cleaning
    df = df.rename(columns={
        'Datum van activiteit': 'Datum', 'Naam activiteit': 'Naam', 
        'Activiteitstype': 'Activiteitstype', 'Beweegtijd': 'Beweegtijd_sec',
        'Afstand': 'Afstand_km', 'Totale stijging': 'Hoogte_m',
        'Gemiddelde hartslag': 'Gemiddelde_Hartslag',
        'Gemiddelde snelheid': 'Gemiddelde_Snelheid_km_u',
        'Max. snelheid': 'Max_Snelheid_km_u'
    })
    
    cols = ['Afstand_km', 'Hoogte_m', 'Gemiddelde_Snelheid_km_u', 'Gemiddelde_Hartslag', 'Max_Snelheid_km_u']
    for c in cols:
        if c in df.columns and df[c].dtype == object:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce')

    # PADEL LOGICA
    padel_types = ['Training', 'Workout', 'WeightTraining', 'Krachttraining', 'Fitness']
    mask_padel = df['Activiteitstype'].isin(padel_types) | df['Activiteitstype'].str.contains('Training', case=False)
    df.loc[mask_padel, 'Activiteitstype'] = 'Padel'

    mask_swim = df['Activiteitstype'].str.contains('Zwemmen', case=False)
    df.loc[mask_swim, 'Afstand_km'] /= 1000
    
    df['Datum'] = robust_date_parser(df['Datum'])
    df['Jaar'] = df['Datum'].dt.year
    df['DagVanJaar'] = df['Datum'].dt.dayofyear
    
    now = datetime.now()
    huidig_jaar = now.year
    max_datum = df['Datum'].max()
    ytd_day = max_datum.dayofyear if max_datum.year == huidig_jaar else 366

    # --- HTML ---
    nav_html = ""
    sections_html = ""
    jaren = sorted(df['Jaar'].unique(), reverse=True)
    
    # 1. JAAR TABS
    for jaar in jaren:
        is_current = (jaar == max_datum.year)
        df_jaar = df[df['Jaar'] == jaar]
        
        # YTD Logic
        prev_jaar = jaar - 1
        df_prev_full = df[df['Jaar'] == prev_jaar]
        if is_current:
            df_prev_comp = df_prev_full[df_prev_full['DagVanJaar'] <= ytd_day]
        else:
            df_prev_comp = df_prev_full

        s_cur = {'n': len(df_jaar), 'km': df_jaar['Afstand_km'].sum(), 'h': df_jaar['Hoogte_m'].sum()}
        s_prev = {'n': len(df_prev_comp), 'km': df_prev_comp['Afstand_km'].sum(), 'h': df_prev_comp['Hoogte_m'].sum()}
        
        label = "vs. vorig jaar (YTD)" if is_current else "vs. vorig jaar"
        
        kpis = f"""<div class="kpi-grid">
            {generate_kpi("Sessies", s_cur['n'], label, "🔥", format_diff_html(s_cur['n'], s_prev['n']))}
            {generate_kpi("Afstand", f"{s_cur['km']:,.0f} km", label, "📏", format_diff_html(s_cur['km'], s_prev['km'], "km"))}
            {generate_kpi("Hoogtemeters", f"{s_cur['h']:,.0f} m", label, "⛰️", format_diff_html(s_cur['h'], s_prev['h'], "m"))}
        </div>"""
        
        # Koersverloop Grafiek - Clean & Soft
        df_cum = df_jaar.sort_values('DagVanJaar')[['DagVanJaar', 'Afstand_km']].copy()
        df_cum['Cum'] = df_cum['Afstand_km'].cumsum()
        df_cum_prev = df_prev_full.sort_values('DagVanJaar')[['DagVanJaar', 'Afstand_km']].copy()
        df_cum_prev['Cum'] = df_cum_prev['Afstand_km'].cumsum()
        
        fig_line = px.line(title=f"Koersverloop {jaar}")
        fig_line.add_scatter(x=df_cum['DagVanJaar'], y=df_cum['Cum'], name=f"{jaar}", line_color=COLORS['chart_main'], line_width=3)
        if not df_cum_prev.empty:
            fig_line.add_scatter(x=df_cum_prev['DagVanJaar'], y=df_cum_prev['Cum'], name=f"{prev_jaar}", line_color=COLORS['chart_sec'], line_dash='dot')
        
        fig_line.update_layout(
            template='plotly_white', 
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            font={'family': 'Inter, sans-serif', 'color': COLORS['text_light']},
            margin=dict(t=50,b=20,l=20,r=20), 
            height=380,
            hovermode="x unified"
        )
        fig_line.update_xaxes(showgrid=False)
        fig_line.update_yaxes(showgrid=True, gridcolor='#e2e8f0')

        # Pie Chart
        sessies_per_sport = df_jaar['Activiteitstype'].value_counts().reset_index()
        sessies_per_sport.columns = ['Sport', 'Aantal']
        pie_colors = {row['Sport']: get_sport_style(row['Sport'])['color'] for _, row in sessies_per_sport.iterrows()}
        
        fig_pie = px.pie(sessies_per_sport, values='Aantal', names='Sport', title=f"Verdeling", color='Sport', color_discrete_map=pie_colors, hole=0.6)
        fig_pie.update_layout(template='plotly_white', paper_bgcolor='rgba(0,0,0,0)', font={'family': 'Inter', 'color': COLORS['text_light']}, height=380)

        active = "active" if is_current else ""
        nav_html += f'<button class="nav-btn {active}" onclick="openTab(event, \'view-{jaar}\')">{jaar}</button>'
        disp = 'block' if is_current else 'none'
        
        sections_html += f"""
        <div id="view-{jaar}" class="tab-content" style="display: {disp};">
            <h2 class="section-title">Overzicht {jaar}</h2>
            {kpis}
            <h3 class="section-subtitle">Prestaties per Sport</h3>
            {generate_sport_cards(df_jaar, df_prev_comp)}
            <h3 class="section-subtitle">Analyse</h3>
            <div class="chart-grid">
                <div class="chart-box full-width">{fig_line.to_html(full_html=False, include_plotlyjs='cdn')}</div>
                <div class="chart-box">{fig_pie.to_html(full_html=False, include_plotlyjs='cdn')}</div>
            </div>
        </div>
        """

    # 2. TOTAAL TAB
    nav_html += '<button class="nav-btn" onclick="openTab(event, \'view-Total\')">Totaal</button>'
    tk_n = len(df); tk_km = df['Afstand_km'].sum(); tk_h = df['Hoogte_m'].sum()
    kpis_tot = f"""<div class="kpi-grid">
        {generate_kpi("Totaal Sessies", tk_n, "Carrière", "🏆")}
        {generate_kpi("Totaal Afstand", f"{tk_km:,.0f} km", "Carrière", "🌍")}
        {generate_kpi("Hoogtemeters", f"{tk_h:,.0f} m", f"{(tk_h/8848):.1f}x Everest", "⛰️")}
    </div>"""
    
    sections_html += f"""
    <div id="view-Total" class="tab-content" style="display: none;">
        <h2 class="section-title">Carrière Overzicht</h2>
        {kpis_tot}
        <h3 class="section-subtitle">Statistieken per Sport</h3>
        {generate_sport_cards(df, None)}
    </div>
    """

    # 3. HALL OF FAME TAB
    nav_html += '<button class="nav-btn" onclick="openTab(event, \'view-HOF\')">Eregalerij</button>'
    sections_html += f"""
    <div id="view-HOF" class="tab-content" style="display: none;">
        <h2 class="section-title">🏆 Hall of Fame</h2>
        <p style="color:var(--text_light); margin-bottom:20px;">De beste prestaties op basis van gemiddelde snelheid en afstand.</p>
        {generate_hall_of_fame(df)}
    </div>
    """

    # 4. DETAIL TABEL
    df_sorted = df.sort_values('Datum', ascending=False)
    sports_list = sorted(df['Activiteitstype'].unique())
    opt_html = "".join([f'<option value="{s}">{s}</option>' for s in sports_list])
    rows = ""
    for _, row in df_sorted.iterrows():
        st = get_sport_style(row['Activiteitstype'])
        hr = f"{row['Gemiddelde_Hartslag']:.0f}" if pd.notna(row['Gemiddelde_Hartslag']) else "-"
        rows += f"""<tr data-sport="{row['Activiteitstype']}">
            <td><div class="sport-dot" style="background:{st['color']}"></div></td>
            <td>{row['Datum'].strftime('%d %b %Y')}</td>
            <td>{row['Activiteitstype']}</td>
            <td><span class="activity-name">{row['Naam']}</span></td>
            <td class="num">{row['Afstand_km']:.1f}</td>
            <td class="num">{format_time(row['Beweegtijd_sec'])}</td>
            <td class="num hr-blur">{hr}</td>
        </tr>"""

    detail_table = f"""
    <div class="detail-section">
        <div class="detail-header">
            <h3>Logboek</h3>
            <div class="select-wrapper">
                <select id="sportFilter" onchange="filterTable()">
                    <option value="ALL">Alle Sporten</option>
                    {opt_html}
                </select>
            </div>
        </div>
        <div class="table-responsive">
            <table id="detailTable">
                <thead><tr><th width="20"></th><th>Datum</th><th>Type</th><th>Naam</th><th class="num">Km</th><th class="num">Tijd</th><th class="num">❤️</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </div>
    """

    html = f"""
    <!DOCTYPE html>
    <html lang="nl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sportoverzicht Jorden</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --primary: {COLORS['primary']}; --accent: {COLORS['accent']};
                --bg: {COLORS['bg']}; --card: {COLORS['card']}; 
                --text: {COLORS['text']}; --text-light: {COLORS['text_light']};
            }}
            body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 40px 20px; line-height: 1.6; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            
            /* Header */
            .top-bar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }}
            h1 {{ margin: 0; font-weight: 700; font-size: 28px; color: var(--primary); letter-spacing: -0.5px; }}
            
            .lock-btn {{ 
                background: white; border: 1px solid #e2e8f0; color: var(--text-light); 
                border-radius: 8px; padding: 8px 16px; cursor: pointer; font-weight: 500; font-size: 14px;
                transition: 0.2s; display: flex; align-items: center; gap: 8px;
            }}
            .lock-btn:hover {{ border-color: var(--accent); color: var(--accent); }}

            /* Navigation */
            .nav-bar {{ display: flex; gap: 8px; margin-bottom: 30px; overflow-x: auto; padding-bottom: 5px; }}
            .nav-btn {{ 
                background: transparent; border: none; padding: 10px 20px; border-radius: 6px; 
                cursor: pointer; font-weight: 500; color: var(--text-light); font-size: 15px; transition: 0.2s; 
            }}
            .nav-btn:hover {{ background: #e2e8f0; color: var(--text); }}
            .nav-btn.active {{ background: var(--primary); color: white; font-weight: 600; box-shadow: 0 4px 12px rgba(30, 41, 59, 0.2); }}
            
            /* Cards & Grids */
            .kpi-grid, .sport-grid, .chart-grid, .hof-grid {{ display: grid; gap: 24px; margin-bottom: 40px; }}
            .kpi-grid {{ grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); }}
            .sport-grid {{ grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }}
            .chart-grid {{ grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); }}
            .hof-grid {{ grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }}

            .kpi-card, .sport-card, .hof-card, .chart-box, .detail-section {{ 
                background: var(--card); border-radius: 16px; padding: 24px; 
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); 
                border: 1px solid rgba(0,0,0,0.02);
            }}
            .full-width {{ grid-column: 1 / -1; }}
            
            /* KPI Styles */
            .kpi-card {{ display: flex; align-items: center; gap: 20px; }}
            .kpi-icon-box {{ 
                width: 56px; height: 56px; background: #f1f5f9; border-radius: 12px; 
                display: flex; align-items: center; justify-content: center; font-size: 24px; color: var(--primary);
            }}
            .kpi-title {{ font-size: 13px; font-weight: 600; text-transform: uppercase; color: var(--text-light); letter-spacing: 0.5px; margin-bottom: 4px; }}
            .kpi-value {{ font-size: 28px; font-weight: 700; color: var(--primary); line-height: 1.1; }}
            .kpi-sub {{ font-size: 13px; color: var(--text-light); margin-top: 4px; display: flex; align-items: center; }}
            
            /* Sport Card */
            .sport-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }}
            .sport-icon-circle {{ width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; }}
            .sport-header h3 {{ margin: 0; font-size: 18px; font-weight: 600; color: var(--text); }}
            
            .stat-main {{ display: flex; margin-bottom: 20px; }}
            .stat-col {{ flex: 1; }}
            .stat-divider {{ width: 1px; background: #e2e8f0; margin: 0 20px; }}
            .label {{ font-size: 12px; color: var(--text-light); text-transform: uppercase; margin-bottom: 4px; font-weight: 500; }}
            .val {{ font-size: 22px; font-weight: 700; color: var(--text); }}
            .sub {{ font-size: 12px; margin-top: 4px; }}
            
            .sport-details {{ background: #f8fafc; padding: 16px; border-radius: 12px; }}
            .stat-row {{ display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 8px; color: var(--text-light); }}
            .stat-row:last-child {{ margin-bottom: 0; }}
            .stat-row strong {{ color: var(--text); font-weight: 600; }}
            
            /* Hall of Fame */
            .hof-card {{ text-align: left; transition: transform 0.2s; }}
            .hof-card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05); }}
            .hof-header {{ margin-bottom: 15px; border-bottom: 1px solid #f1f5f9; padding-bottom: 10px; }}
            .hof-header h3 {{ margin: 0; font-size: 16px; font-weight: 600; }}
            .hof-record {{ display: flex; align-items: flex-start; gap: 12px; padding: 8px 0; }}
            .hof-icon {{ font-size: 18px; margin-top: 2px; }}
            .hof-label {{ font-size: 11px; font-weight: 600; color: var(--text-light); text-transform: uppercase; margin-bottom: 2px; }}
            .hof-val {{ font-size: 16px; font-weight: 700; color: var(--primary); }}
            .hof-date {{ font-size: 12px; color: var(--text-light); }}

            /* Table */
            .detail-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
            .detail-header h3 {{ margin: 0; font-size: 18px; color: var(--text); }}
            .select-wrapper select {{ 
                padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; 
                font-family: 'Inter'; font-size: 14px; color: var(--text); outline: none;
            }}
            table {{ width: 100%; border-collapse: separate; border-spacing: 0; }}
            th {{ text-align: left; padding: 12px 16px; border-bottom: 2px solid #f1f5f9; color: var(--text-light); font-size: 12px; font-weight: 600; text-transform: uppercase; }}
            td {{ padding: 16px; border-bottom: 1px solid #f1f5f9; font-size: 14px; vertical-align: middle; }}
            tr:last-child td {{ border-bottom: none; }}
            .sport-dot {{ width: 8px; height: 8px; border-radius: 50%; }}
            .activity-name {{ font-weight: 500; color: var(--text); }}
            .num {{ text-align: right; font-feature-settings: "tnum"; font-weight: 500; }}
            
            /* Utils */
            .section-title {{ font-size: 20px; font-weight: 700; color: var(--primary); margin: 0 0 24px 0; }}
            .section-subtitle {{ font-size: 14px; font-weight: 600; color: var(--text-light); margin: 30px 0 16px 0; text-transform: uppercase; letter-spacing: 0.5px; }}
            .hr-blur {{ filter: blur(6px); transition: 0.3s; background: #e2e8f0; padding: 0 4px; border-radius: 4px; }}
            
            @media (max-width: 768px) {{ 
                .chart-grid {{ grid-template-columns: 1fr; }} 
                body {{ padding: 20px 10px; }}
                .kpi-grid {{ grid-template-columns: 1fr 1fr; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="top-bar">
                <h1>Sportoverzicht Jorden</h1>
                <button class="lock-btn" onclick="unlockHR()">
                    <span>❤️</span> Hartslag
                    <span style="font-size:10px; color:#cbd5e1">🔒</span>
                </button>
            </div>
            
            <div class="nav-bar">{nav_html}</div>
            
            {sections_html}
            {detail_table}
        </div>
        
        <script>
            function openTab(evt, tabName) {{
                var i, tabcontent, tablinks;
                tabcontent = document.getElementsByClassName("tab-content");
                for (i = 0; i < tabcontent.length; i++) {{ tabcontent[i].style.display = "none"; }}
                tablinks = document.getElementsByClassName("nav-btn");
                for (i = 0; i < tablinks.length; i++) {{ tablinks[i].className = tablinks[i].className.replace(" active", ""); }}
                document.getElementById(tabName).style.display = "block";
                evt.currentTarget.className += " active";
            }}
            function filterTable() {{
                var input = document.getElementById("sportFilter").value;
                var tr = document.getElementById("detailTable").getElementsByTagName("tr");
                for (i = 1; i < tr.length; i++) {{
                    var sport = tr[i].getAttribute('data-sport');
                    if (input === "ALL" || sport === input) {{ tr[i].style.display = ""; }} 
                    else {{ tr[i].style.display = "none"; }}
                }}
            }}
            function unlockHR() {{
                var pass = prompt("Wachtwoord (Tip: Niet Gust):");
                if(pass === "Nala") {{
                    document.querySelectorAll('.hr-blur').forEach(e => {{
                        e.style.filter = 'none';
                        e.style.background = 'transparent';
                    }});
                    document.querySelector('.lock-btn').style.display = 'none';
                }} else if(pass !== null) {{ alert("❌ Fout!"); }}
            }}
        </script>
    </body>
    </html>
    """
    
    with open(html_output, 'w', encoding='utf-8') as f:
        f.write(html)
    print("✅ Luxe Dashboard gereed!")

if __name__ == "__main__":
    genereer_dashboard()
