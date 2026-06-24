# CLAUDE.md — StructureAI Project Context

This file is loaded automatically by Claude Code at every session. It contains all persistent
knowledge about this project: architecture, domain expertise, design decisions, and key bugs fixed.

---

## Project Overview

**StructureAI** — a Streamlit-based lifecycle management platform for structured products.
Built as a university capstone (UP, Lima, Peru). Presented June 24, 2026, slot 08:55–09:05.

Owner: Mauricio Jorge Benavides Bautista (mj.benavidesb@alum.up.edu.pe)
GitHub: https://github.com/mjbenavidesb-prog/Structured_Products_Data_Manager

**Core features:**
1. AI termsheet extraction (Claude API reads PDF, extracts 50+ fields)
2. Portfolio analytics dashboard (AUM by asset class, strategy, counterparty)
3. Event calendar (upcoming autocalls, maturities, coupon payments)
4. Factsheet generation (branded A4 PPTX: Autocall, Vencimiento, Ejecutado)
5. Excel portfolio reports
6. Custom branding (logo, colors)

**Tech stack:** Python, Streamlit, SQLite (via backend/database.py), python-pptx, matplotlib,
yfinance, anthropic SDK, crewAI, openpyxl, python-dotenv.

**Demo credentials:** username `admin` / password `demo2024`

---

## Architecture

```
app.py                        # Entry point: auth gate → landing → login → main tabs
pages/
  landing.py                  # render_landing() + render_login() — shown before auth
  tab_upload.py               # Load Product: PDF upload → Claude extraction → save
  tab_portfolio.py            # Portfolio dashboard: AUM charts, Plotly
  tab_events.py               # Maturities & Events calendar
  tab_factsheet.py            # Factsheet generation UI + validation
  tab_reports.py              # Excel report downloads
  tab_config.py               # Settings: company name, logo, colors, API key
backend/
  database.py                 # SQLite CRUD, seed_from_csv, DataValidation fix
  extractor.py                # Claude API: extract_termsheet(pdf_bytes, api_key)
  factsheet.py                # PPTX generation engine
  config.py                   # get(key)/save(key,val) + DEFAULTS dict
  excel_report.py             # openpyxl styled reports
ai/
  agents.py                   # crewAI agents (course requirement)
data/
  products.db                 # SQLite (gitignored)
  templates/                  # company_logo.png, etc. (gitignored)
.streamlit/
  config.toml                 # dark theme: #0A1628 bg, #2563EB primary
```

**Auth flow (session_state.auth_state):**
`"landing"` → render_landing() + st.stop()
`"login"`   → render_login() + st.stop()
`"app"`     → main app with tabs + sign-out button

---

## Design System (Luma-inspired)

- Background: `#0A1628` (dark navy)
- Primary: `#2563EB` (blue), Secondary: `#DC2626` (red)
- Secondary background: `#111E33`, Cards: `#0F1C30`
- Font: Inter (all text), 9pt body, 11pt titles
- Tabs: underline style (2px solid primary on selected, no filled boxes)
- No emojis anywhere in the UI
- "My Company" placeholder: completely removed — default company_name is `""`

---

## Factsheet Engine (backend/factsheet.py)

### Layout — `_YP` dict (A4 portrait, all in inches from top)
```python
_YP = {
    "header":    (0.00, 0.55),   # taller header bar
    "title":     (0.60, 0.30),
    "det_bar":   (0.95, 0.22),
    "narrative": (1.21, 0.92),
    "sbars":     (2.18, 0.22),
    "main":      (2.44, 3.40),
    "sumtbl":    (5.89, 0.85),
    "evol_bar":  (6.79, 0.22),
    "subhdr":    (7.05, 0.30),
    "bottom":    (7.40, 3.00),
    "footnote":  (10.49, 0.18),
}
```
Page: 8.27" × 11.69" (A4). All `_YP` values are (top_y, height) in inches.
Logo embedded via `slide.shapes.add_picture(BytesIO(logo_bytes), left, top, width=None, height=Inches(...))` — auto-scales width.

### Fonts
- All text: Inter (was Calibri, replaced globally)
- Body: 9pt, Title: 11pt
- Chart labels: 9pt (matplotlib rcParams['font.family'] = 'Inter')

### Factsheet types
- **Autocall**: product called early at an observation date. Shows worst-of chart + coupon paid.
- **Vencimiento**: product reached final maturity. Shows full performance + final return.
- **Ejecutado**: product is still live / in-progress view.

### Validation rules (tab_factsheet.py `_validate`)
1. All types: termsheet must exist (underlyings + start date)
2. Autocall: requires `fecha_autocall_N` in the past
3. Vencimiento: requires `fecha_obs_final` or `fecha_obs_final_ac` or `fecha_vencimiento` in the PAST
4. Ejecutado: no date restriction

### Spanish date parsing — CRITICAL
Dates in the DB are stored as "12-Ene-26" (Spanish months). strptime %b is English.
**Must translate before parsing:**
```python
_ES_MON = {"Ene":"Jan","Feb":"Feb","Mar":"Mar","Abr":"Apr","May":"May",
           "Jun":"Jun","Jul":"Jul","Ago":"Aug","Set":"Sep","Sep":"Sep",
           "Oct":"Oct","Nov":"Nov","Dic":"Dec"}

def _parse_date(val) -> date | None:
    s = str(val).strip()
    if s in ("", "nan", "None", "NaT"): return None
    for es, en in _ES_MON.items():
        s = s.replace(es, en)
    d = pd.to_datetime(s, dayfirst=True, errors="coerce")
    return d.date() if pd.notna(d) else None
```
This dict exists in BOTH `backend/factsheet.py` AND `pages/tab_factsheet.py`.

### Range Accrual overlay (in `_chart_all`)
Orange/red line showing daily coupon accumulation:
```python
if barrier_pct is not None and cupon_annual and not df.empty:
    worst = df.min(axis=1)
    daily_rate = cupon_annual / 252
    above = (worst >= barrier_pct).astype(float)
    accrual = 100 + above.cumsum() * daily_rate
    ax.plot(accrual.index, accrual.values,
            color=accrual_color, linewidth=1.8, zorder=5,
            label="Cupón acumulado RA")
```

### `fecha_vencto` fallback chain
```python
fecha_vencto = (_parse_date(p.get("fecha_vencimiento"))
             or _parse_date(p.get("fecha_obs_final"))
             or _parse_date(p.get("fecha_obs_final_ac")))
```

---

## Database (backend/database.py)

### openpyxl DataValidation fix (openpyxl 3.1+)
```python
# CORRECT — add range before attaching to worksheet:
dv.add(f"{ltr}2:{ltr}500")
ws.add_data_validation(dv)
# WRONG (was):
# ws.add_data_validation(dv); dv.sqref = "B2:500"
```

### API key lookup order (tab_upload.py)
```python
api_key = cfg.get("claude_api_key") or os.environ.get("ANTHROPIC_API_KEY") or ""
```
`load_dotenv()` is called in `app.py` entry point.

---

## Structured Products Domain Knowledge

### Phoenix Autocall (Standard)
Worst-of basket with conditional coupons and automatic early redemption.
- **Autocall barrier** (trigger): typically 100% of strike. If worst-of >= trigger on obs date → product calls, returns 100% + coupon.
- **Coupon barrier**: typically 70–80%. Coupon only paid if worst-of >= coupon barrier on obs date.
- **Capital barrier** (KI): typically 60–75%. If worst-of NEVER breaches this level → 100% capital returned. If breached → capital at risk (downside = worst_final/strike).
- **Observation schedule**: quarterly or semi-annual autocall dates; monthly coupon observations.
- **Payoff at maturity (if never called):**
  - worst_final >= capital_barrier → 100%
  - worst_final < capital_barrier → 100 × (worst_final / strike)

### Phoenix with Memory
Same as Phoenix but unpaid coupons accumulate:
- If coupon barrier not breached in period N, the coupon is "remembered"
- When barrier is next observed, ALL accumulated coupons are paid at once
- Memory coupon = Σ(unpaid_coupons) paid in first period where barrier is observed
- Example: 10% annual = 2.5%/quarter. Miss Q1 and Q2 → Q3 pays 7.5% if barrier met
- Factsheet shows "Cupón acumulado" line on performance chart

### Daily Range Accrual
- Each trading day: if worst-of >= coupon_barrier → earns `annual_coupon / 252`
- Daily observation (not periodic snapshot like Phoenix)
- Formula: `cumulative = 100 + Σ(I{worst_t >= barrier} × annual_rate/252)`
- Payoff: 100 + accumulated coupon at maturity
- `barrier_pct` = coupon barrier (separate from capital barrier)
- `cupon_annual` = annual coupon rate (e.g., 0.12 for 12%)
- The orange overlay line in charts IS this cumulative accrual
- Worst-of basket: `worst_t = min(underlying_1_t, ..., underlying_n_t)` normalized to 100 at inception

### Worst-of Basket
- Performance = `min(S_i_t / S_i_0)` across all underlyings i, expressed as % of inception
- Higher yield premium than single-asset or average-basket products
- Used in Phoenix, Range Accrual, BRC (Barrier Reverse Convertible)
- yfinance downloads each ticker; normalize each series to 100 at inception date; take min per day

### Callable Bonds
- Issuer (not automatic) can redeem before maturity at call price (typically 100–105%)
- Call schedule: specific dates + notice period (30–45 days)
- Differs from autocall: callable = issuer discretion; autocall = automatic if condition met
- Field: `call_dates`, `call_price`

### Cap (Participation Cap)
- Limits upside: `payoff = min(S_final/S_initial, cap_level) × 100`
- Example: cap = 1.26 → max gain = 26% even if underlying +50%
- Used to fund barrier protection or reduce hedging cost
- Field: `nivel_cap` (e.g., 1.26)

### Barrier Types
| Type | Description |
|------|-------------|
| European | Observed only on specific dates (safer for investor) |
| American | Monitored continuously (higher risk, higher yield) |
| Knock-In | Must be breached to activate downside risk (KI put) |
| Knock-Out | Breach terminates upside participation |
| Capital barrier | ~60–75%; breach → downside exposure at maturity |
| Coupon barrier | ~70–80%; below → no coupon paid that period |
| Autocall barrier | ~100%; above → early redemption |

### Low Strike Leveraged
- Strike set below spot at inception (e.g., strike = spot × 0.90)
- Leverage = spot / strike (e.g., 6400 / 6000 = 1.067 embedded)
- Full leverage factor declared: e.g., 133% = 1.33× participation
- Payoff: `100 + 1.33 × (S_final/S_strike - 1) × 100`
- Higher delta than standard; no capital protection; funds leverage via strike discount
- Field: `factor_participacion` (e.g., 1.33)

### Capital Protection Levels
| Level | Meaning | Typical Barrier |
|-------|---------|-----------------|
| Fully protected (100%) | Investor never loses principal | KI barrier rarely touched |
| Partially protected (90%) | Minimum 90% returned | Moderate barrier |
| Capital at risk | No protection floor | Low/no barrier |

Field: `barrera_capital` (e.g., 0.70 = 70% barrier)

### Key Lifecycle Dates
| Date | Description | DB field |
|------|-------------|----------|
| Trade date | Contract signed | `fecha_inicio` (used as inception) |
| Inception/valuation date | Strike prices fixed | `fecha_inicio` |
| Autocall obs. dates | Quarterly/semi-annual checks | `fecha_autocall_1` … `fecha_autocall_10` |
| Final obs. date | Last autocall check | `fecha_obs_final_ac` |
| Maturity/settlement | Payment to client | `fecha_vencimiento` |
| Final obs. (Vencimiento) | For Vencimiento factsheet | `fecha_obs_final` |

### Common Underlyings
| Ticker (yfinance) | Name |
|-------------------|------|
| `^GSPC` | S&P 500 (SPX) |
| `^NDX` | NASDAQ 100 |
| `^RUT` | Russell 2000 (RTY) |
| `^STOXX50E` | Euro Stoxx 50 (SX5E) |
| `^N225` | Nikkei 225 |
| `IWM` | iShares Russell 2000 ETF |
| `XLF`, `XLV`, `XLP` | Sector ETFs |

### Performance Calculation at Maturity
```
total_return = (Σ coupons_received + capital_at_maturity) / principal - 1
underlying_return = worst_final / strike - 1
```
Factsheet shows both: "Rendimiento del Producto" (total) and "Rendimiento del subyacente" (worst-of).

---

## Key Bugs Fixed (don't reintroduce)

1. **Spanish months**: "12-Ene-26" fails pd.to_datetime without the `_ES_MON` translation. Always apply the dict before parsing any date from the DB.

2. **openpyxl DataValidation**: Call `dv.add("B2:B500")` BEFORE `ws.add_data_validation(dv)`. Never assign to `dv.sqref` directly.

3. **PPTX logo in group shapes**: `_apply_template()` filtered bare `pic` XML tags but logos live in `grpSp` group shapes. Solution: abandoned template approach entirely — use PNG logo uploaded by user, embedded directly with `add_picture()`.

4. **Vencimiento validation**: Only block if date EXISTS AND is in the future. If date parses as None (unknown), it WAS a Spanish month parsing failure, not a missing date.

5. **"My Company" placeholder**: Fully removed. `backend/config.py` DEFAULTS has `"company_name": ""`. Never add fallback `or "My Company"` anywhere.

---

## Streamlit Cloud Deployment

URL: https://structured-funds-data-manager.streamlit.app
Repo: https://github.com/mjbenavidesb-prog/Structured_Products_Data_Manager

Secrets to set in Streamlit Cloud dashboard:
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

On Streamlit Cloud the DB starts empty (products.db is gitignored).
Users upload products via "Load Product" tab using the Claude AI extraction.
