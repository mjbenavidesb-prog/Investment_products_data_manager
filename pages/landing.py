import base64
import streamlit as st
import backend.config as cfg

_DEMO_USER = "admin"
_DEMO_PASS = "demo2024"

_INDIGO  = "#6366F1"
_INDIGO2 = "#4F46E5"
_AMBER   = "#F59E0B"
_TEAL    = "#0D9488"

_BASE_CSS = f"""
<style>
header[data-testid="stHeader"]      {{ display: none !important; }}
#MainMenu, footer, [data-testid="stToolbar"] {{ display: none !important; }}
.main .block-container {{
    padding: 0 !important;
    max-width: 100% !important;
}}
html, body, [class*="css"], .stApp {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    background: #0A1628 !important;
}}

/* ── Navbar ──────────────────────────────────────────────────────────── */
.lp-nav {{
    display: flex;
    align-items: center;
    padding: 0 56px;
    height: 64px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    position: sticky;
    top: 0;
    background: #0A1628;
    z-index: 100;
}}
.lp-logo {{
    font-size: 15px;
    font-weight: 800;
    color: #F8FAFC;
    letter-spacing: -0.04em;
    flex: 1;
}}
.lp-logo span {{ color: {_INDIGO}; }}
.lp-nav-links {{
    display: flex;
    gap: 32px;
    flex: 1;
    justify-content: center;
}}
.lp-nav-links a {{
    font-size: 13px;
    font-weight: 500;
    color: #64748B;
    text-decoration: none;
}}
.lp-nav-actions {{
    flex: 1;
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    align-items: center;
}}

/* ── Hero ────────────────────────────────────────────────────────────── */
.lp-hero {{
    padding: 80px 56px 48px;
    max-width: 820px;
}}
.lp-eyebrow {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(99,102,241,0.1);
    border: 1px solid rgba(99,102,241,0.22);
    color: #A5B4FC;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 5px 14px;
    border-radius: 20px;
    margin-bottom: 28px;
}}
.lp-eyebrow-dot {{
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: {_INDIGO};
    display: inline-block;
}}
.lp-h1 {{
    font-size: 3.4rem;
    font-weight: 800;
    letter-spacing: -0.05em;
    line-height: 1.08;
    color: #F8FAFC;
    margin: 0 0 24px;
}}
.lp-h1 em {{
    font-style: normal;
    color: {_INDIGO};
}}
.lp-lead {{
    font-size: 16px;
    color: #475569;
    line-height: 1.75;
    margin: 0 0 36px;
    max-width: 560px;
}}

/* ── Dashboard preview ────────────────────────────────────────────────── */
.lp-preview {{
    padding: 0 56px 72px;
}}
.lp-preview-label {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: {_AMBER};
    margin-bottom: 18px;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.lp-preview-label::after {{
    content: '';
    flex: 1;
    height: 1px;
    background: rgba(255,255,255,0.05);
    max-width: 200px;
}}
.lp-preview-card {{
    background: #080E1A;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 24px 64px rgba(0,0,0,0.5), 0 0 0 1px rgba(99,102,241,0.08);
    max-width: 760px;
}}

/* ── Features ────────────────────────────────────────────────────────── */
.lp-section {{
    padding: 64px 56px 72px;
    border-top: 1px solid rgba(255,255,255,0.05);
}}
.lp-section-label {{
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {_INDIGO};
    margin-bottom: 16px;
}}
.lp-section-title {{
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -0.04em;
    color: #F8FAFC;
    margin: 0 0 12px;
}}
.lp-section-sub {{
    font-size: 14px;
    color: #475569;
    max-width: 540px;
    line-height: 1.7;
    margin: 0 0 44px;
}}
.feat-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
}}
.feat-card {{
    background: #0F1C30;
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 12px;
    padding: 28px;
    transition: border-color 0.2s;
}}
.feat-card:hover {{
    border-color: rgba(99,102,241,0.2);
}}
.feat-num {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    margin-bottom: 14px;
}}
.feat-num.indigo {{ color: {_INDIGO}; }}
.feat-num.teal   {{ color: {_TEAL}; }}
.feat-num.amber  {{ color: {_AMBER}; }}
.feat-title {{
    font-size: 13.5px;
    font-weight: 700;
    color: #E2E8F0;
    margin-bottom: 10px;
}}
.feat-desc {{
    font-size: 12.5px;
    color: #475569;
    line-height: 1.65;
}}

/* ── Footer CTA ──────────────────────────────────────────────────────── */
.lp-cta {{
    padding: 72px 56px;
    border-top: 1px solid rgba(255,255,255,0.05);
    text-align: center;
}}
.lp-cta h2 {{
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -0.04em;
    color: #F8FAFC;
    margin-bottom: 12px;
}}
.lp-cta p {{
    color: #475569;
    font-size: 14px;
    margin-bottom: 28px;
}}

/* ── Login page ──────────────────────────────────────────────────────── */
.login-wrap {{
    display: flex;
    min-height: 100vh;
}}
.login-left {{
    flex: 1;
    background: #0D1829;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 56px 64px;
    border-right: 1px solid rgba(255,255,255,0.05);
}}
.login-logo {{
    font-size: 18px;
    font-weight: 800;
    color: #F8FAFC;
    letter-spacing: -0.04em;
    margin-bottom: 48px;
}}
.login-logo span {{ color: {_INDIGO}; }}
.login-title {{
    font-size: 1.6rem;
    font-weight: 800;
    color: #F8FAFC;
    letter-spacing: -0.03em;
    margin-bottom: 6px;
}}
.login-sub {{
    font-size: 13.5px;
    color: #475569;
    margin-bottom: 28px;
}}
.login-demo-hint {{
    background: rgba(99,102,241,0.08);
    border: 1px solid rgba(99,102,241,0.22);
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 12px;
    color: #A5B4FC;
    margin-bottom: 24px;
}}
.login-demo-hint code {{
    background: rgba(99,102,241,0.2);
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 11px;
    color: #C7D2FE;
}}
.login-right {{
    flex: 1;
    background: linear-gradient(160deg, #070D1A 0%, #0D1829 100%);
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 56px 64px;
}}
.login-right-title {{
    font-size: 1.8rem;
    font-weight: 800;
    color: #F8FAFC;
    letter-spacing: -0.04em;
    line-height: 1.2;
    margin-bottom: 14px;
}}
.login-right-sub {{
    font-size: 14px;
    color: #334155;
    line-height: 1.7;
    margin-bottom: 40px;
}}
.login-feature-list {{
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 18px;
}}
.login-feature-item {{
    display: flex;
    align-items: flex-start;
    gap: 14px;
}}
.feat-dot {{
    width: 28px;
    height: 28px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 1px;
    font-size: 11px;
    font-weight: 800;
}}
.feat-dot.indigo {{ background: rgba(99,102,241,0.15); color: {_INDIGO}; }}
.feat-dot.teal   {{ background: rgba(13,148,136,0.15); color: {_TEAL}; }}
.feat-dot.amber  {{ background: rgba(245,158,11,0.15); color: {_AMBER}; }}
.feat-item-text {{
    font-size: 13px;
    color: #64748B;
    line-height: 1.55;
}}
.feat-item-text b {{
    color: #CBD5E1;
    font-weight: 600;
    display: block;
    margin-bottom: 2px;
}}

/* Streamlit widget overrides for dark login */
.stTextInput input {{
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 7px !important;
    color: #F8FAFC !important;
    font-size: 14px !important;
    padding: 10px 14px !important;
}}
.stTextInput input:focus {{
    border-color: rgba(99,102,241,0.5) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.12) !important;
}}
.stTextInput label {{
    color: #475569 !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}}
.stButton > button[kind="primary"] {{
    background: {_INDIGO} !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    border-radius: 8px !important;
    border: none !important;
    height: 44px !important;
    transition: background 0.15s !important;
}}
.stButton > button[kind="primary"]:hover {{
    background: {_INDIGO2} !important;
}}
.stButton > button:not([kind="primary"]) {{
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #64748B !important;
    height: 44px !important;
    border-radius: 8px !important;
}}
</style>
"""

_DASHBOARD_SVG = """
<svg width="760" height="360" viewBox="0 0 760 360" xmlns="http://www.w3.org/2000/svg">
  <!-- App chrome -->
  <rect width="760" height="360" fill="#080E1A"/>
  <!-- Top bar -->
  <rect width="760" height="44" fill="#060C17"/>
  <rect y="44" width="760" height="1" fill="rgba(255,255,255,0.05)"/>
  <!-- Logo mark -->
  <rect x="18" y="14" width="16" height="16" rx="4" fill="#6366F1"/>
  <rect x="40" y="17" width="52" height="5" rx="2.5" fill="rgba(255,255,255,0.18)"/>
  <!-- Tab items -->
  <rect x="120" y="19" width="62" height="5" rx="2.5" fill="rgba(255,255,255,0.06)"/>
  <rect x="196" y="19" width="50" height="5" rx="2.5" fill="rgba(255,255,255,0.06)"/>
  <rect x="260" y="19" width="74" height="5" rx="2.5" fill="rgba(255,255,255,0.06)"/>
  <rect x="348" y="19" width="58" height="5" rx="2.5" fill="rgba(255,255,255,0.06)"/>
  <rect x="120" y="39" width="62" height="2" rx="1" fill="#6366F1"/>
  <!-- Active tab underline -->
  <rect x="690" y="14" width="52" height="16" rx="6" fill="rgba(99,102,241,0.15)"/>
  <rect x="700" y="18" width="32" height="8" rx="2" fill="rgba(99,102,241,0.4)"/>

  <!-- ── Metric cards ── -->
  <!-- Card 1: Total AUM -->
  <rect x="16" y="60" width="160" height="82" rx="8" fill="#0F1C30" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
  <text x="28" y="79" font-family="Inter,sans-serif" font-size="8" fill="#475569" font-weight="700" letter-spacing="0.08em">TOTAL AUM</text>
  <text x="28" y="108" font-family="Inter,sans-serif" font-size="22" fill="#F8FAFC" font-weight="700">$147.2M</text>
  <rect x="28" y="120" width="40" height="5" rx="2.5" fill="rgba(99,102,241,0.25)"/>
  <rect x="152" y="64" width="16" height="16" rx="4" fill="rgba(99,102,241,0.12)"/>

  <!-- Card 2: Vigente -->
  <rect x="186" y="60" width="130" height="82" rx="8" fill="#0F1C30" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
  <text x="198" y="79" font-family="Inter,sans-serif" font-size="8" fill="#475569" font-weight="700" letter-spacing="0.08em">VIGENTE</text>
  <text x="198" y="108" font-family="Inter,sans-serif" font-size="22" fill="#F8FAFC" font-weight="700">28</text>
  <rect x="198" y="120" width="54" height="5" rx="2.5" fill="rgba(13,148,136,0.25)"/>

  <!-- Card 3: Vencidos -->
  <rect x="326" y="60" width="130" height="82" rx="8" fill="#0F1C30" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
  <text x="338" y="79" font-family="Inter,sans-serif" font-size="8" fill="#475569" font-weight="700" letter-spacing="0.08em">VENCIDOS</text>
  <text x="338" y="108" font-family="Inter,sans-serif" font-size="22" fill="#F8FAFC" font-weight="700">6</text>
  <rect x="338" y="120" width="30" height="5" rx="2.5" fill="rgba(255,255,255,0.06)"/>

  <!-- Card 4: Próx. Autocall (highlighted amber) -->
  <rect x="466" y="60" width="142" height="82" rx="8" fill="#0F1C30" stroke="rgba(245,158,11,0.18)" stroke-width="1"/>
  <text x="478" y="79" font-family="Inter,sans-serif" font-size="8" fill="#475569" font-weight="700" letter-spacing="0.08em">PRÓX. AUTOCALL</text>
  <text x="478" y="108" font-family="Inter,sans-serif" font-size="22" fill="#F59E0B" font-weight="700">7</text>
  <rect x="478" y="120" width="64" height="5" rx="2.5" fill="rgba(245,158,11,0.2)"/>

  <!-- Card 5: AUM Perú -->
  <rect x="618" y="60" width="126" height="82" rx="8" fill="#0F1C30" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
  <text x="630" y="79" font-family="Inter,sans-serif" font-size="8" fill="#475569" font-weight="700" letter-spacing="0.08em">AUM PERÚ</text>
  <text x="630" y="108" font-family="Inter,sans-serif" font-size="22" fill="#F8FAFC" font-weight="700">$94M</text>
  <rect x="630" y="120" width="46" height="5" rx="2.5" fill="rgba(99,102,241,0.15)"/>

  <!-- ── LEFT: Bar chart ── -->
  <rect x="16" y="156" width="412" height="190" rx="8" fill="#0F1C30" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
  <text x="28" y="176" font-family="Inter,sans-serif" font-size="8.5" fill="#475569" font-weight="700" letter-spacing="0.07em">AUM POR ESTRATEGIA (USD M)</text>

  <!-- Grid lines -->
  <line x1="80" y1="188" x2="400" y2="188" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
  <line x1="80" y1="218" x2="400" y2="218" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
  <line x1="80" y1="248" x2="400" y2="248" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
  <line x1="80" y1="278" x2="400" y2="278" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
  <line x1="80" y1="308" x2="400" y2="308" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
  <line x1="80" y1="188" x2="80" y2="320" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>

  <!-- Y axis labels -->
  <text x="74" y="192" font-family="Inter,sans-serif" font-size="7.5" fill="#334155" text-anchor="end">120</text>
  <text x="74" y="222" font-family="Inter,sans-serif" font-size="7.5" fill="#334155" text-anchor="end">90</text>
  <text x="74" y="252" font-family="Inter,sans-serif" font-size="7.5" fill="#334155" text-anchor="end">60</text>
  <text x="74" y="282" font-family="Inter,sans-serif" font-size="7.5" fill="#334155" text-anchor="end">30</text>
  <text x="74" y="312" font-family="Inter,sans-serif" font-size="7.5" fill="#334155" text-anchor="end">0</text>

  <!-- Bars (bottom at y=308, max height for 120M = 120px) -->
  <!-- Opportunity $89M - height 89 -->
  <rect x="96" y="219" width="44" height="89" rx="3" fill="#6366F1" opacity="0.9"/>
  <text x="118" y="213" font-family="Inter,sans-serif" font-size="8" fill="#A5B4FC" font-weight="600" text-anchor="middle">$89M</text>
  <text x="118" y="320" font-family="Inter,sans-serif" font-size="8" fill="#475569" text-anchor="middle">Opp.</text>

  <!-- Cap. Proteg. $60M - height 60 -->
  <rect x="162" y="248" width="44" height="60" rx="3" fill="#0D9488" opacity="0.85"/>
  <text x="184" y="242" font-family="Inter,sans-serif" font-size="8" fill="#5EEAD4" font-weight="600" text-anchor="middle">$60M</text>
  <text x="184" y="320" font-family="Inter,sans-serif" font-size="8" fill="#475569" text-anchor="middle">Cap.P.</text>

  <!-- Híbrido $32M - height 32 -->
  <rect x="228" y="276" width="44" height="32" rx="3" fill="#F59E0B" opacity="0.85"/>
  <text x="250" y="270" font-family="Inter,sans-serif" font-size="8" fill="#FCD34D" font-weight="600" text-anchor="middle">$32M</text>
  <text x="250" y="320" font-family="Inter,sans-serif" font-size="8" fill="#475569" text-anchor="middle">Híbr.</text>

  <!-- Renta Fija $14M - height 14 -->
  <rect x="294" y="294" width="44" height="14" rx="3" fill="#8B5CF6" opacity="0.85"/>
  <text x="316" y="288" font-family="Inter,sans-serif" font-size="8" fill="#C4B5FD" font-weight="600" text-anchor="middle">$14M</text>
  <text x="316" y="320" font-family="Inter,sans-serif" font-size="8" fill="#475569" text-anchor="middle">R.Fija</text>

  <!-- Commodities $2M - height 2 -->
  <rect x="360" y="306" width="44" height="2" rx="1" fill="#64748B" opacity="0.7"/>
  <text x="382" y="300" font-family="Inter,sans-serif" font-size="8" fill="#475569" font-weight="600" text-anchor="middle">$2M</text>
  <text x="382" y="320" font-family="Inter,sans-serif" font-size="8" fill="#475569" text-anchor="middle">Comm.</text>

  <!-- ── RIGHT: Donut chart ── -->
  <rect x="440" y="156" width="304" height="190" rx="8" fill="#0F1C30" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
  <text x="452" y="176" font-family="Inter,sans-serif" font-size="8.5" fill="#475569" font-weight="700" letter-spacing="0.07em">DISTRIBUCIÓN ASSET CLASS</text>

  <!-- Donut: r=54, cx=544, cy=256, circumference≈339.3 -->
  <!-- Track -->
  <circle cx="544" cy="256" r="54" fill="none" stroke="#1A2840" stroke-width="24"/>
  <!-- Renta Variable 60% = 203.6 -->
  <circle cx="544" cy="256" r="54" fill="none" stroke="#6366F1"
          stroke-dasharray="204 136" stroke-dashoffset="0"
          stroke-width="24" transform="rotate(-90,544,256)" opacity="0.9"/>
  <!-- Renta Fija 24% = 81.4 -->
  <circle cx="544" cy="256" r="54" fill="none" stroke="#0D9488"
          stroke-dasharray="81 258" stroke-dashoffset="-204"
          stroke-width="24" transform="rotate(-90,544,256)" opacity="0.85"/>
  <!-- Commodities 9% = 30.5 -->
  <circle cx="544" cy="256" r="54" fill="none" stroke="#F59E0B"
          stroke-dasharray="31 309" stroke-dashoffset="-285"
          stroke-width="24" transform="rotate(-90,544,256)" opacity="0.85"/>
  <!-- Otros 7% = 23.8 -->
  <circle cx="544" cy="256" r="54" fill="none" stroke="#8B5CF6"
          stroke-dasharray="24 316" stroke-dashoffset="-316"
          stroke-width="24" transform="rotate(-90,544,256)" opacity="0.85"/>

  <!-- Center label -->
  <text x="544" y="251" font-family="Inter,sans-serif" font-size="16" fill="#F8FAFC" font-weight="700" text-anchor="middle">60%</text>
  <text x="544" y="265" font-family="Inter,sans-serif" font-size="8" fill="#475569" text-anchor="middle">Renta Var.</text>

  <!-- Legend 2-col -->
  <rect x="452" y="310" width="9" height="9" rx="2" fill="#6366F1"/>
  <text x="465" y="318" font-family="Inter,sans-serif" font-size="8.5" fill="#64748B">Renta Variable 60%</text>
  <rect x="452" y="325" width="9" height="9" rx="2" fill="#0D9488"/>
  <text x="465" y="333" font-family="Inter,sans-serif" font-size="8.5" fill="#64748B">Renta Fija 24%</text>
  <rect x="588" y="310" width="9" height="9" rx="2" fill="#F59E0B"/>
  <text x="601" y="318" font-family="Inter,sans-serif" font-size="8.5" fill="#64748B">Commodities 9%</text>
  <rect x="588" y="325" width="9" height="9" rx="2" fill="#8B5CF6"/>
  <text x="601" y="333" font-family="Inter,sans-serif" font-size="8.5" fill="#64748B">Otros 7%</text>

  <!-- Subtle glow effect on the donut -->
  <circle cx="544" cy="256" r="72" fill="rgba(99,102,241,0.03)"/>
</svg>
"""

_DASHBOARD_SVG_B64 = base64.b64encode(_DASHBOARD_SVG.encode()).decode()


def render_landing():
    st.markdown(_BASE_CSS, unsafe_allow_html=True)

    st.markdown(f"""
<div class="lp-nav">
    <div class="lp-logo">Structure<span>AI</span></div>
    <div class="lp-nav-links">
        <a href="#">Features</a>
        <a href="#">How it works</a>
        <a href="#">Contact</a>
    </div>
</div>

<div class="lp-hero">
    <div class="lp-eyebrow">
        <span class="lp-eyebrow-dot"></span>
        Structured Products Platform
    </div>
    <h1 class="lp-h1">
        Lifecycle management<br>for <em>structured products</em>
    </h1>
    <p class="lp-lead">
        From termsheet ingestion to client delivery — extract data with AI,
        monitor your portfolio in real time, and generate professional
        factsheets in one click.
    </p>
</div>

<div class="lp-preview">
    <div class="lp-preview-label">Live dashboard preview</div>
    <div class="lp-preview-card">
        <img src="data:image/svg+xml;base64,{_DASHBOARD_SVG_B64}" width="760" style="display:block;"/>
    </div>
</div>

<div class="lp-section">
    <div class="lp-section-label">What you get</div>
    <h2 class="lp-section-title">Everything in one platform</h2>
    <p class="lp-section-sub">
        Replace spreadsheets and manual processes with an integrated
        system built for structured product lifecycle management.
    </p>
    <div class="feat-grid">
        <div class="feat-card">
            <div class="feat-num indigo">01 — INGEST</div>
            <div class="feat-title">AI Termsheet Extraction</div>
            <div class="feat-desc">
                Upload any PDF termsheet. Claude AI reads the document and
                extracts 50+ fields automatically — underlyings, barriers,
                autocall triggers, coupon schedules — in seconds.
            </div>
        </div>
        <div class="feat-card">
            <div class="feat-num teal">02 — MONITOR</div>
            <div class="feat-title">Portfolio Analytics</div>
            <div class="feat-desc">
                Real-time AUM breakdown by asset class, strategy, counterparty,
                and risk profile. Track upcoming autocall dates, maturities,
                and coupon payments across your entire book.
            </div>
        </div>
        <div class="feat-card">
            <div class="feat-num amber">03 — DELIVER</div>
            <div class="feat-title">Client Factsheet Generation</div>
            <div class="feat-desc">
                One-click branded PPTX factsheets for Autocall, Vencimiento,
                and Ejecutado events — with performance charts and Range Accrual
                coupon overlay.
            </div>
        </div>
        <div class="feat-card">
            <div class="feat-num indigo">04 — EXPORT</div>
            <div class="feat-title">Excel Portfolio Reports</div>
            <div class="feat-desc">
                Styled, grouped Excel reports by asset class, strategy,
                or counterparty — ready for compliance, management, or clients.
            </div>
        </div>
        <div class="feat-card">
            <div class="feat-num teal">05 — ALERT</div>
            <div class="feat-title">Event Calendar</div>
            <div class="feat-desc">
                View upcoming autocall observation dates, maturity events,
                and coupon payment dates across your full portfolio at a glance.
            </div>
        </div>
        <div class="feat-card">
            <div class="feat-num amber">06 — BRAND</div>
            <div class="feat-title">Custom Branding</div>
            <div class="feat-desc">
                Configure your company logo, primary colors, and brand
                identity. Every factsheet and report reflects your
                firm's visual identity.
            </div>
        </div>
    </div>
</div>

<div class="lp-cta">
    <h2>Ready to get started?</h2>
    <p>Sign in to access your portfolio dashboard and generate your first factsheet.</p>
</div>
""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("Sign In", type="primary", use_container_width=True):
            st.session_state.auth_state = "login"
            st.rerun()


def render_login():
    st.markdown(_BASE_CSS, unsafe_allow_html=True)

    # Style the two Streamlit columns to look like distinct panels
    st.markdown("""
<style>
section[data-testid="stMain"] > div > div > div[data-testid="stVerticalBlock"]
  > div[data-testid="stHorizontalBlock"] > div:first-child {
    background: #0D1829 !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
    min-height: 100vh;
    padding: 52px 40px !important;
}
section[data-testid="stMain"] > div > div > div[data-testid="stVerticalBlock"]
  > div[data-testid="stHorizontalBlock"] > div:last-child {
    background: #070D1A !important;
    min-height: 100vh;
    padding: 52px 40px !important;
}
</style>
""", unsafe_allow_html=True)

    left, right = st.columns([1, 1], gap="small")

    with left:
        st.markdown(f"""
<div style="margin-bottom: 40px;">
    <div class="login-logo">Structure<span>AI</span></div>
    <div class="login-title" style="margin-top: 40px;">Sign in to your account</div>
    <div class="login-sub">Enter your credentials to access the platform.</div>
    <div class="login-demo-hint">
        Demo &mdash; Username: <code>admin</code> &nbsp;/&nbsp; Password: <code>demo2024</code>
    </div>
</div>
""", unsafe_allow_html=True)

        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button("Sign In", type="primary", use_container_width=True):
                if username == _DEMO_USER and password == _DEMO_PASS:
                    st.session_state.auth_state = "app"
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
        with col_b:
            if st.button("Back", use_container_width=True):
                st.session_state.auth_state = "landing"
                st.rerun()

    with right:
        st.markdown("""
<div style="padding-top: 40px;">
    <div class="login-right-title">
        One platform.<br>Your entire product lifecycle.
    </div>
    <div class="login-right-sub" style="margin-top: 14px; margin-bottom: 36px;">
        Everything you need to manage, monitor, and report
        on your structured products portfolio.
    </div>
    <ul class="login-feature-list">
        <li class="login-feature-item">
            <div class="feat-dot indigo">AI</div>
            <div class="feat-item-text">
                <b>AI Termsheet Extraction</b>
                Upload a PDF, get all fields populated automatically via Claude AI.
            </div>
        </li>
        <li class="login-feature-item">
            <div class="feat-dot teal">&#9783;</div>
            <div class="feat-item-text">
                <b>Live Portfolio Dashboard</b>
                AUM breakdowns, exposure maps, and upcoming event alerts.
            </div>
        </li>
        <li class="login-feature-item">
            <div class="feat-dot amber">&#9654;</div>
            <div class="feat-item-text">
                <b>One-click Factsheets</b>
                Branded PPTX with performance charts and Range Accrual coupon overlay.
            </div>
        </li>
        <li class="login-feature-item">
            <div class="feat-dot indigo">XL</div>
            <div class="feat-item-text">
                <b>Excel Reports</b>
                Styled, grouped portfolio exports ready for compliance and management.
            </div>
        </li>
    </ul>
</div>
""", unsafe_allow_html=True)
