import streamlit as st
import backend.config as cfg

_DEMO_USER = "admin"
_DEMO_PASS = "demo2024"

# ── CSS shared by landing + login ───────────────────────────────────────────────
_BASE_CSS = """
<style>
header[data-testid="stHeader"]      { display: none !important; }
#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }
.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
}
html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    background: #0A1628 !important;
}

/* Landing navbar */
.lp-nav {
    display: flex;
    align-items: center;
    padding: 0 56px;
    height: 64px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    position: sticky;
    top: 0;
    background: #0A1628;
    z-index: 100;
}
.lp-logo {
    font-size: 15px;
    font-weight: 800;
    color: #F8FAFC;
    letter-spacing: -0.04em;
    flex: 1;
}
.lp-logo span { color: #3B82F6; }
.lp-nav-links {
    display: flex;
    gap: 32px;
    flex: 1;
    justify-content: center;
}
.lp-nav-links a {
    font-size: 13px;
    font-weight: 500;
    color: #64748B;
    text-decoration: none;
}
.lp-nav-actions {
    flex: 1;
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    align-items: center;
}
.lp-btn-ghost {
    font-size: 13px;
    font-weight: 600;
    color: #94A3B8;
    background: transparent;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 7px;
    padding: 7px 18px;
    cursor: pointer;
    text-decoration: none;
    transition: all 0.15s;
}
.lp-btn-primary {
    font-size: 13px;
    font-weight: 600;
    color: white;
    background: #2563EB;
    border: none;
    border-radius: 7px;
    padding: 8px 20px;
    cursor: pointer;
    text-decoration: none;
    transition: background 0.15s;
}

/* Hero */
.lp-hero {
    padding: 96px 56px 80px;
    max-width: 780px;
}
.lp-eyebrow {
    display: inline-block;
    background: rgba(59,130,246,0.12);
    border: 1px solid rgba(59,130,246,0.25);
    color: #93C5FD;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 4px 14px;
    border-radius: 20px;
    margin-bottom: 28px;
}
.lp-h1 {
    font-size: 3.2rem;
    font-weight: 800;
    letter-spacing: -0.05em;
    line-height: 1.1;
    color: #F8FAFC;
    margin: 0 0 24px;
}
.lp-h1 span { color: #3B82F6; }
.lp-lead {
    font-size: 16px;
    color: #64748B;
    line-height: 1.75;
    margin: 0 0 36px;
    max-width: 580px;
}
.lp-hero-cta {
    display: flex;
    gap: 12px;
    align-items: center;
}
.hero-btn-primary {
    background: #2563EB;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    padding: 12px 28px;
    cursor: pointer;
}
.hero-btn-outline {
    background: transparent;
    color: #94A3B8;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    padding: 12px 24px;
    cursor: pointer;
}

/* Features */
.lp-section {
    padding: 72px 56px;
    border-top: 1px solid rgba(255,255,255,0.05);
}
.lp-section-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #3B82F6;
    margin-bottom: 16px;
}
.lp-section-title {
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -0.04em;
    color: #F8FAFC;
    margin: 0 0 12px;
}
.lp-section-sub {
    font-size: 14px;
    color: #475569;
    max-width: 540px;
    line-height: 1.7;
    margin: 0 0 48px;
}
.feat-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
}
.feat-card {
    background: #0F1C30;
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 12px;
    padding: 28px;
}
.feat-num {
    font-size: 11px;
    font-weight: 700;
    color: #3B82F6;
    letter-spacing: 0.08em;
    margin-bottom: 14px;
}
.feat-title {
    font-size: 14px;
    font-weight: 700;
    color: #E2E8F0;
    margin-bottom: 10px;
}
.feat-desc {
    font-size: 12.5px;
    color: #475569;
    line-height: 1.65;
}

/* Footer CTA */
.lp-cta {
    padding: 72px 56px;
    border-top: 1px solid rgba(255,255,255,0.05);
    text-align: center;
}
.lp-cta h2 {
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -0.04em;
    color: #F8FAFC;
    margin-bottom: 12px;
}
.lp-cta p {
    color: #475569;
    font-size: 14px;
    margin-bottom: 28px;
}

/* ── Login page ──────────────────────────────────────────────────────────── */
.login-wrap {
    display: flex;
    min-height: 100vh;
}
.login-left {
    flex: 1;
    background: #F8FAFC;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 56px 64px;
}
.login-logo {
    font-size: 20px;
    font-weight: 800;
    color: #0F172A;
    letter-spacing: -0.04em;
    margin-bottom: 48px;
}
.login-logo span { color: #2563EB; }
.login-title {
    font-size: 1.6rem;
    font-weight: 800;
    color: #0F172A;
    letter-spacing: -0.03em;
    margin-bottom: 6px;
}
.login-sub {
    font-size: 13.5px;
    color: #64748B;
    margin-bottom: 36px;
}
.login-demo-hint {
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 12px;
    color: #1D4ED8;
    margin-bottom: 24px;
}
.login-right {
    flex: 1;
    background: linear-gradient(160deg, #0A1628 0%, #0F2347 100%);
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 56px 64px;
    border-left: 1px solid rgba(255,255,255,0.05);
}
.login-right-title {
    font-size: 1.8rem;
    font-weight: 800;
    color: #F8FAFC;
    letter-spacing: -0.04em;
    margin-bottom: 14px;
}
.login-right-sub {
    font-size: 14px;
    color: #475569;
    line-height: 1.7;
    margin-bottom: 40px;
}
.login-feature-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 16px;
}
.login-feature-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
}
.feat-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #3B82F6;
    margin-top: 5px;
    flex-shrink: 0;
}
.feat-item-text {
    font-size: 13px;
    color: #94A3B8;
    line-height: 1.5;
}
.feat-item-text b {
    color: #E2E8F0;
    font-weight: 600;
}

/* Streamlit widget overrides for login */
.stTextInput input {
    background: #F1F5F9 !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 7px !important;
    color: #0F172A !important;
    font-size: 14px !important;
    padding: 10px 14px !important;
}
.stTextInput label {
    color: #64748B !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
.stButton > button[kind="primary"] {
    background: #2563EB !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    border-radius: 8px !important;
    border: none !important;
    height: 44px !important;
}
</style>
"""


def render_landing():
    st.markdown(_BASE_CSS, unsafe_allow_html=True)

    st.markdown("""
<div class="lp-nav">
    <div class="lp-logo">Structure<span>AI</span></div>
    <div class="lp-nav-links">
        <a href="#">Features</a>
        <a href="#">How it works</a>
        <a href="#">Contact</a>
    </div>
    <div class="lp-nav-actions">
        <span id="login-link" style="font-size:13px;font-weight:600;color:#94A3B8;
              border:1px solid rgba(255,255,255,0.1);border-radius:7px;
              padding:7px 18px;cursor:pointer;background:transparent;">
            Login
        </span>
    </div>
</div>

<div class="lp-hero">
    <div class="lp-eyebrow">Structured Products Platform</div>
    <h1 class="lp-h1">
        Lifecycle management<br>for <span>structured products</span>
    </h1>
    <p class="lp-lead">
        From termsheet ingestion to client delivery — extract data with AI,
        monitor your portfolio in real time, and generate professional
        factsheets in one click.
    </p>
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
            <div class="feat-num">01 — INGEST</div>
            <div class="feat-title">AI Termsheet Extraction</div>
            <div class="feat-desc">
                Upload any PDF termsheet. Claude AI reads the document and
                extracts 50+ fields automatically — underlyings, barriers,
                autocall triggers, coupon schedules — in seconds.
            </div>
        </div>
        <div class="feat-card">
            <div class="feat-num">02 — MONITOR</div>
            <div class="feat-title">Portfolio Analytics</div>
            <div class="feat-desc">
                Real-time AUM breakdown by asset class, strategy, counterparty,
                and risk profile. Track upcoming autocall dates, maturities,
                and coupon payments across your entire book.
            </div>
        </div>
        <div class="feat-card">
            <div class="feat-num">03 — DELIVER</div>
            <div class="feat-title">Client Factsheet Generation</div>
            <div class="feat-desc">
                One-click branded PPTX factsheets for Autocall, Vencimiento,
                and Ejecutado events — with performance charts, Range Accrual
                overlay, and payment schedules.
            </div>
        </div>
        <div class="feat-card">
            <div class="feat-num">04 — EXPORT</div>
            <div class="feat-title">Excel Portfolio Reports</div>
            <div class="feat-desc">
                Styled, grouped Excel reports by asset class, strategy,
                or counterparty — ready to share with compliance,
                management, or clients.
            </div>
        </div>
        <div class="feat-card">
            <div class="feat-num">05 — ALERT</div>
            <div class="feat-title">Event Calendar</div>
            <div class="feat-desc">
                View upcoming autocall observation dates, maturity events,
                and coupon payment dates across your full portfolio at
                a glance.
            </div>
        </div>
        <div class="feat-card">
            <div class="feat-num">06 — BRAND</div>
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

    # Centered login button
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("Sign In", type="primary", use_container_width=True):
            st.session_state.auth_state = "login"
            st.rerun()


def render_login():
    st.markdown(_BASE_CSS, unsafe_allow_html=True)

    # Left side: form | Right side: feature highlights
    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown("""
<div class="login-left">
    <div class="login-logo">Structure<span>AI</span></div>
    <div class="login-title">Sign in to your account</div>
    <div class="login-sub">Enter your credentials to access the platform.</div>
    <div class="login-demo-hint">
        <b>Demo credentials</b> &nbsp;&mdash;&nbsp; Username: <code>admin</code>
        &nbsp;/&nbsp; Password: <code>demo2024</code>
    </div>
</div>
""", unsafe_allow_html=True)

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

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
<div class="login-right">
    <div class="login-right-title">
        One platform.<br>Your entire product lifecycle.
    </div>
    <div class="login-right-sub">
        Everything you need to manage, monitor, and report
        on your structured products portfolio.
    </div>
    <ul class="login-feature-list">
        <li class="login-feature-item">
            <div class="feat-dot"></div>
            <div class="feat-item-text">
                <b>AI Termsheet Extraction</b> — upload a PDF, get all fields
                populated automatically via Claude AI
            </div>
        </li>
        <li class="login-feature-item">
            <div class="feat-dot"></div>
            <div class="feat-item-text">
                <b>Live Portfolio Dashboard</b> — AUM breakdowns, exposure maps,
                and upcoming event alerts
            </div>
        </li>
        <li class="login-feature-item">
            <div class="feat-dot"></div>
            <div class="feat-item-text">
                <b>One-click Factsheets</b> — branded PPTX with performance charts
                and Range Accrual coupon overlay
            </div>
        </li>
        <li class="login-feature-item">
            <div class="feat-dot"></div>
            <div class="feat-item-text">
                <b>Excel Reports</b> — styled, grouped portfolio exports
                ready for compliance and management
            </div>
        </li>
    </ul>
</div>
""", unsafe_allow_html=True)
