import os
from dotenv import load_dotenv
load_dotenv()   # loads .env if present

import streamlit as st
import backend.config as cfg

st.set_page_config(
    page_title="StructureAI",
    page_icon="assets/favicon.ico" if __import__("pathlib").Path("assets/favicon.ico").exists() else None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Auth gate ───────────────────────────────────────────────────────────────────
if "auth_state" not in st.session_state:
    st.session_state.auth_state = "landing"

_state = st.session_state.auth_state

if _state == "landing":
    from pages.landing import render_landing
    render_landing()
    st.stop()

if _state == "login":
    from pages.landing import render_login
    render_login()
    st.stop()

# ── Authenticated: init DB once ─────────────────────────────────────────────────
from backend.database import init_db, seed_from_csv

@st.cache_resource
def startup():
    init_db()
    seed_from_csv()
    return True

startup()

primary   = cfg.get("primary_color")   or "#2563EB"
secondary = cfg.get("secondary_color") or "#DC2626"

st.markdown(f"""
<style>
/* ── Global typography ───────────────────────────────────────────────────────── */
html, body, [class*="css"], .stApp {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}}

/* ── Layout ──────────────────────────────────────────────────────────────────── */
.main .block-container {{
    padding-top: 1.25rem;
    padding-bottom: 2.5rem;
    max-width: 100%;
}}

/* ── Top navbar ──────────────────────────────────────────────────────────────── */
.app-navbar {{
    display: flex;
    align-items: center;
    gap: 14px;
    padding-bottom: 18px;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    margin-bottom: 4px;
}}
.app-navbar .logo-mark {{
    width: 34px;
    height: 34px;
    background: {primary};
    border-radius: 7px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 13px;
    color: white;
    letter-spacing: -0.5px;
    flex-shrink: 0;
}}
.app-navbar .logo-name {{
    font-size: 15px;
    font-weight: 700;
    color: #F8FAFC;
    letter-spacing: -0.03em;
}}
.app-navbar .nav-pipe {{
    color: rgba(255,255,255,0.12);
    font-size: 18px;
}}
.app-navbar .nav-subtitle {{
    font-size: 11px;
    color: #475569;
    font-weight: 500;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}}

/* ── Navigation tabs ─────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    background: transparent;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    gap: 0;
    padding: 0;
}}
.stTabs [data-baseweb="tab"] {{
    height: 40px;
    padding: 0 20px;
    border-radius: 0;
    font-weight: 500;
    font-size: 13px;
    color: #475569;
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    transition: color 0.15s ease;
}}
.stTabs [data-baseweb="tab"]:hover {{
    color: #94A3B8;
    background: transparent !important;
}}
.stTabs [aria-selected="true"] {{
    color: #F8FAFC !important;
    border-bottom: 2px solid {primary} !important;
    background: transparent !important;
}}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {{
    display: none;
}}

/* ── Metric cards ────────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {{
    background: #0F1C30;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 8px;
    padding: 16px 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.3);
}}
[data-testid="stMetricLabel"] p {{
    font-size: 10.5px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
    color: #475569 !important;
}}
[data-testid="stMetricValue"] {{
    font-size: 1.4rem !important;
    font-weight: 700 !important;
    color: #F8FAFC !important;
    letter-spacing: -0.02em !important;
}}

/* ── Primary buttons ─────────────────────────────────────────────────────────── */
.stButton > button[kind="primary"] {{
    font-family: inherit !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    border-radius: 6px !important;
    background: {primary} !important;
    border: none !important;
    color: white !important;
    transition: background 0.15s ease, box-shadow 0.15s ease !important;
}}
.stButton > button[kind="primary"]:hover {{
    background: #1D4ED8 !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.2) !important;
}}

/* ── Secondary buttons ───────────────────────────────────────────────────────── */
.stButton > button[kind="secondary"],
.stButton > button:not([kind="primary"]) {{
    font-family: inherit !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    border-radius: 6px !important;
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #94A3B8 !important;
    transition: all 0.15s ease !important;
}}
.stButton > button[kind="secondary"]:hover,
.stButton > button:not([kind="primary"]):hover {{
    border-color: rgba(255,255,255,0.22) !important;
    color: #F8FAFC !important;
}}

/* ── Download buttons ────────────────────────────────────────────────────────── */
.stDownloadButton > button {{
    font-family: inherit !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    border-radius: 6px !important;
    background: {primary} !important;
    border: none !important;
    color: white !important;
}}
.stDownloadButton > button:hover {{
    background: #1D4ED8 !important;
}}

/* ── DataFrames ──────────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {{
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 8px !important;
    overflow: hidden;
}}

/* ── Text inputs / select / textarea ────────────────────────────────────────── */
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {{
    font-family: inherit !important;
    font-size: 13px !important;
}}
[data-baseweb="select"] * {{
    font-family: inherit !important;
    font-size: 13px !important;
}}

/* ── Form labels ─────────────────────────────────────────────────────────────── */
label[data-testid="stWidgetLabel"] p,
[data-testid="stSelectbox"] label,
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stRadio"] label,
[data-testid="stFileUploader"] label {{
    font-size: 12px !important;
    font-weight: 500 !important;
    color: #64748B !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}}

/* ── Headings ────────────────────────────────────────────────────────────────── */
h1 {{
    font-size: 1.4rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.03em !important;
    color: #F8FAFC !important;
}}
h2 {{
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    color: #F8FAFC !important;
}}
h3 {{
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    color: #CBD5E1 !important;
}}
h4 {{
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    color: #94A3B8 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}}

/* ── Captions ────────────────────────────────────────────────────────────────── */
[data-testid="stCaptionContainer"] p,
.stCaption {{
    color: #334155 !important;
    font-size: 11.5px !important;
}}

/* ── Info / warning / error / success ───────────────────────────────────────── */
[data-testid="stAlert"] {{
    border-radius: 6px !important;
    border-left-width: 3px !important;
    font-size: 13px !important;
    font-family: inherit !important;
}}

/* ── Expanders ───────────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {{
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 8px !important;
    background: #0F1C30 !important;
}}
[data-testid="stExpander"] summary {{
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #94A3B8 !important;
}}

/* ── Dividers ────────────────────────────────────────────────────────────────── */
hr {{
    border: none !important;
    border-top: 1px solid rgba(255,255,255,0.06) !important;
    margin: 12px 0 !important;
}}

/* ── Sidebar ─────────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background: #060F1E !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
}}

/* ── Scrollbars ──────────────────────────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{
    background: rgba(255,255,255,0.08);
    border-radius: 3px;
}}
::-webkit-scrollbar-thumb:hover {{
    background: rgba(255,255,255,0.15);
}}

/* ── Plotly chart background ─────────────────────────────────────────────────── */
[data-testid="stPlotlyChart"] {{
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 8px;
    overflow: hidden;
}}

/* ── Radio options ───────────────────────────────────────────────────────────── */
[data-testid="stRadio"] > div {{
    gap: 6px;
}}

/* ── Markdown paragraphs ─────────────────────────────────────────────────────── */
[data-testid="stMarkdownContainer"] p {{
    font-size: 13.5px;
    color: #CBD5E1;
    line-height: 1.6;
}}

/* ── Sign-out button in navbar area ─────────────────────────────────────────── */
.signout-wrap {{
    display: flex;
    align-items: center;
    padding-bottom: 18px;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    margin-bottom: 4px;
    justify-content: flex-end;
    gap: 8px;
}}
.signout-user {{
    font-size: 11.5px;
    color: #334155;
    font-weight: 500;
}}
</style>
""", unsafe_allow_html=True)

# ── Top navbar ─────────────────────────────────────────────────────────────────
company_name = cfg.get("company_name") or ""
if company_name:
    initials = "".join(w[0] for w in company_name.split()[:2]).upper()
    display_name = company_name
else:
    initials = "SA"
    display_name = "StructureAI"

nav_col, signout_col = st.columns([11, 1])
with nav_col:
    st.markdown(f"""
<div class="app-navbar">
    <div class="logo-mark">{initials}</div>
    <span class="logo-name">{display_name}</span>
    <span class="nav-pipe">|</span>
    <span class="nav-subtitle">Structured Products Manager</span>
</div>
""", unsafe_allow_html=True)

with signout_col:
    st.markdown('<div style="padding-top:8px">', unsafe_allow_html=True)
    if st.button("Sign out", key="signout_btn", use_container_width=True):
        st.session_state.auth_state = "landing"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Navigation tabs ─────────────────────────────────────────────────────────────
tabs = st.tabs([
    "Load Product",
    "Portfolio",
    "Maturities & Events",
    "Factsheet",
    "Reports",
    "Settings",
])

with tabs[0]:
    from pages.tab_upload import render
    render()

with tabs[1]:
    from pages.tab_portfolio import render
    render()

with tabs[2]:
    from pages.tab_events import render
    render()

with tabs[3]:
    from pages.tab_factsheet import render
    render()

with tabs[4]:
    from pages.tab_reports import render
    render()

with tabs[5]:
    from pages.tab_config import render
    render()
