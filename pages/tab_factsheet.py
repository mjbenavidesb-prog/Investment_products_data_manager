import streamlit as st
import pandas as pd
from datetime import date, timedelta
from pathlib import Path
from backend.database import get_all_products
from backend.factsheet import (
    generate_factsheet_pdf,
    generate_factsheet_participation,
    generate_factsheet_ejecutado_dist,
    is_participation_product,
)
from backend.market_data import resolve_ticker
import backend.config as cfg

_TEMPLATES_DIR = Path("data/templates")

try:
    import yfinance as yf
    _YF = True
except ImportError:
    _YF = False

_BADGE = {
    "AUTOCALL":     "#2563EB",
    "VENCIDO":      "#DC2626",
    "VIGENTE":      "#16A34A",
    "POR EJECUTAR": "#9CA3AF",
}


def _badge(status: str) -> str:
    color = _BADGE.get(status, "#6B7280")
    return (
        f"<span style='background:{color};color:white;padding:2px 10px;"
        f"border-radius:12px;font-size:0.78rem;font-weight:600'>{status}</span>"
    )


_ES_MON = {"Ene":"Jan","Feb":"Feb","Mar":"Mar","Abr":"Apr","May":"May",
           "Jun":"Jun","Jul":"Jul","Ago":"Aug","Set":"Sep","Sep":"Sep",
           "Oct":"Oct","Nov":"Nov","Dic":"Dec"}

def _parse_date(val) -> date | None:
    if val is None:
        return None
    s = str(val).strip()
    if s in ("", "nan", "None", "NaT"):
        return None
    for es, en in _ES_MON.items():
        s = s.replace(es, en)
    try:
        d = pd.to_datetime(s, dayfirst=True, errors="coerce")
        return d.date() if pd.notna(d) else None
    except Exception:
        return None


def _safe_float(v):
    try:
        f = float(v)
        return None if f != f else f
    except (TypeError, ValueError):
        return None


def _has_termsheet(p: dict) -> bool:
    has_underlying = any(
        p.get(f"underlying_{i}") and
        str(p.get(f"underlying_{i}")).strip() not in ("", "nan", "None")
        for i in range(1, 5)
    )
    has_start = bool(p.get("fecha_inicio") or p.get("fecha_strike"))
    return has_underlying and has_start


# ── Pre-validation (fast, no API calls) ───────────────────────────────────────

def _validate(ftype: str, p: dict) -> tuple[bool, str]:
    """
    Returns (is_valid, reason).
    Only fast checks — no price fetching.
    For Autocall, just checks that past dates and trigger data exist.
    The actual price verification happens at generate time.
    """
    today = date.today()

    # All factsheet types require at least one underlying and a start date
    if not _has_termsheet(p):
        return False, (
            "El producto no tiene datos de termsheet (subyacentes y fecha de inicio). "
            "Carga el termsheet primero desde el tab **Load Product**."
        )

    if ftype == "Autocall":
        past_obs = [
            d for i in range(1, 11)
            if (d := _parse_date(p.get(f"fecha_autocall_{i}"))) and d <= today
        ]
        if not past_obs:
            return False, (
                "No hay fechas de observación de autocall en el pasado. "
                "Para que el producto haya autocalleado necesita al menos una "
                "fecha de observación ya transcurrida."
            )
        unds = [
            str(p.get(f"underlying_{i}")).strip()
            for i in range(1, 5)
            if p.get(f"underlying_{i}") and
               str(p.get(f"underlying_{i}")).strip() not in ("", "nan", "None")
        ]
        strikes = [_safe_float(p.get(f"strike_{i}")) for i in range(1, len(unds) + 1)]
        trigger = _safe_float(p.get("trigger_autocall"))
        if not unds or not any(s for s in strikes if s):
            return False, (
                "Faltan subyacentes o niveles de strike para verificar si autocalleó. "
                "Carga el termsheet primero."
            )
        if trigger is None:
            return False, (
                "Falta el nivel de trigger de autocall en el termsheet."
            )
        # Looks OK for a fast check — price verification happens at generate time
        return True, ""

    if ftype == "Vencimiento":
        obs_final = _parse_date(
            p.get("fecha_obs_final") or p.get("fecha_obs_final_ac")
        )
        vcto = _parse_date(p.get("fecha_vencimiento"))
        ref  = obs_final or vcto
        if not ref:
            return False, (
                "No hay fecha de observación final ni de vencimiento registrada para este "
                "producto. Completa el campo **Fecha de Obs. Final** o **Fecha de "
                "Vencimiento** en el portafolio antes de generar el factsheet."
            )
        if ref > today:
            return False, (
                f"La fecha de vencimiento ({ref.strftime('%d/%m/%Y')}) aún no ha llegado. "
                "Solo se puede generar el factsheet Vencimiento cuando el producto ya venció."
            )
        return True, ""

    if ftype == "Ejecutado":
        # Participation products always pass for Ejecutado type
        return True, ""

    return False, "Tipo de factsheet desconocido."


# ── Deep price verification (runs at generate time) ───────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _verify_autocall_prices(
    tickers: tuple, start_date_str: str, trigger: float, obs_dates: tuple
) -> tuple[bool, str | None, str]:
    """
    Downloads prices from the product start date through the last observation date,
    normalizes them (100 = inception price), then checks on each observation date
    whether the worst-of normalized return >= trigger level.

    This approach is independent of how strikes are stored in the DB, because it
    derives the performance relative to the actual inception price from yfinance.

    Returns:
        (did_autocall: bool, autocall_date_str: str | None, message: str)
    """
    if not _YF:
        return True, None, "yfinance not available — skipping price check."

    yf_syms = [resolve_ticker(t) for t in tickers if resolve_ticker(t)]
    if not yf_syms:
        return True, None, "No yfinance tickers resolved — skipping price check."

    trigger_level = (trigger if trigger <= 1.5 else trigger / 100) * 100  # as percentage (e.g. 100.0)

    try:
        start_dt = pd.to_datetime(start_date_str, dayfirst=True, errors="coerce")
        if pd.isna(start_dt):
            return True, None, "Invalid start date — skipping price check."
        start_dt = start_dt.date()

        fetch_start = str(start_dt - timedelta(days=7))
        fetch_end   = str(max(obs_dates) + timedelta(days=2))

        # auto_adjust=False: raw unadjusted prices — autocall triggers are based on
        # price performance only, not total return (dividends go to the issuer).
        raw = yf.download(yf_syms, start=fetch_start, end=fetch_end,
                          auto_adjust=False, progress=False)

        if raw.empty:
            return True, None, "No price data returned — skipping check."

        # Extract Close prices; handle both MultiIndex (multi-ticker) and flat (single)
        if isinstance(raw.columns, pd.MultiIndex):
            closes = raw["Close"].copy()
        else:
            closes = raw[["Close"]].copy()
            closes.columns = yf_syms

        closes.index = pd.to_datetime(closes.index).tz_localize(None)
        # Keep only the tickers we care about (column order may vary)
        present = [s for s in yf_syms if s in closes.columns]
        closes = closes[present]

        # Initial prices: last close on or before start_dt (handles weekends/holidays)
        pre = closes[closes.index.date <= start_dt]
        if pre.empty:
            pre = closes[closes.index.date <= start_dt + timedelta(days=5)]
        if pre.empty:
            return True, None, "No prices near start date — skipping check."
        initial = pre.iloc[-1]

        # Normalize: 100 = inception price
        normalized = closes / initial * 100

        for obs_date in sorted(obs_dates):
            window = normalized[normalized.index.date <= obs_date]
            if window.empty:
                continue
            last_row = window.iloc[-1]
            # Require all tickers to have data; if any is NaN, skip this date
            if last_row.isna().any():
                continue
            worst = float(last_row.min())
            if worst >= trigger_level:
                return True, str(obs_date), ""

    except Exception as e:
        return True, None, f"Price check error ({e}) — proceeding."

    dates_str = ", ".join(str(d) for d in sorted(obs_dates))
    return False, None, (
        f"El producto **no ha autocalleado**. Se verificaron los rendimientos normalizados "
        f"en las fechas de observación pasadas ({dates_str}) y en ninguna el "
        f"peor subyacente alcanzó el {trigger_level:.0f}% de su nivel inicial."
    )


# ── Tab render ────────────────────────────────────────────────────────────────

def render():
    st.subheader("Generate Factsheet")

    df = get_all_products()
    if df.empty:
        st.warning("No products found. Load products first.")
        return

    col1, col2, col3 = st.columns([3, 2, 1])

    with col1:
        selected = st.selectbox("Select Product", df["nombre_producto"].dropna().tolist())

    with col2:
        ftype = st.selectbox(
            "Factsheet Type",
            ["Autocall", "Vencimiento", "Ejecutado"],
            help=(
                "Autocall — producto fue llamado anticipadamente  |  "
                "Vencimiento — producto llegó a plazo  |  "
                "Ejecutado — producto activo (marketing sheet)"
            ),
        )

    with col3:
        st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
        generate = st.button("Generate PDF", type="primary", use_container_width=True)

    if not selected:
        return

    row     = df[df["nombre_producto"] == selected].iloc[0]
    product = row.to_dict()
    status  = str(product.get("status") or "").upper()

    st.markdown(_badge(status), unsafe_allow_html=True)

    # Fast pre-validation (no API)
    valid, reason = _validate(ftype, product)
    if not valid:
        st.error(f"**No se puede generar factsheet {ftype}:** {reason}")

    # ── KPIs ──────────────────────────────────────────────────────────────────
    st.markdown("---")
    k1, k2, k3, k4, k5 = st.columns(5)

    aum = product.get("monto_total") or 0
    k1.metric("AUM", f"${float(aum):,.0f}" if aum else "—")
    k2.metric("Maturity", str(product.get("fecha_vencimiento") or "—"))

    underlyings = [
        str(product.get(f"underlying_{i}")).strip()
        for i in range(1, 5)
        if product.get(f"underlying_{i}")
        and str(product.get(f"underlying_{i}")).strip() not in ("", "nan", "None")
    ]
    k3.metric("Underlyings", " / ".join(underlyings) if underlyings else "—")
    k4.metric("Counterparty", str(product.get("contraparte") or "—"))

    rt = product.get("rendimiento_total")
    if rt is not None:
        rt_f   = float(rt)
        rt_pct = rt_f * 100 if abs(rt_f) <= 1 else rt_f
        k5.metric("Total Return", f"{rt_pct:.2f}%")
    else:
        k5.metric("Total Return", "—")

    # ── Disclaimer ────────────────────────────────────────────────────────────
    disclaimer = st.text_area(
        "Disclaimer (opcional)",
        placeholder=(
            "Escribe aquí el texto legal o disclaimer que aparecerá en la parte inferior "
            "del factsheet. Si se deja vacío se mostrará la nota estándar de rentabilidad."
        ),
        height=75,
        key="disclaimer_input",
    )

    # ── Data expander ─────────────────────────────────────────────────────────
    with st.expander("Product data used for factsheet", expanded=False):
        display_fields = [
            "isin", "moneda", "contraparte", "perfil", "asset_class", "tipo",
            "plazo_meses", "cupon_contingente", "cupon_fijo", "barrera_capital",
            "trigger_autocall", "ganancia_maxima", "cap", "factor_participacion",
            "fecha_inicio", "fecha_strike", "fecha_emision", "fecha_obs_final",
            "fecha_vencimiento", "rendimiento_total",
            "underlying_1", "strike_1", "spot_1",
            "underlying_2", "strike_2", "spot_2",
            "underlying_3", "strike_3", "spot_3",
            "underlying_4", "strike_4", "spot_4",
            *(f"fecha_autocall_{i}" for i in range(1, 11)),
        ]
        available = {k: product.get(k) for k in display_fields if product.get(k) is not None}
        st.json(available)

    # ── Generation ────────────────────────────────────────────────────────────
    if generate:
        if not valid:
            st.warning("Corrige la selección antes de generar.")
            return

        company_name = cfg.get("company_name") or ""
        primary      = cfg.get("primary_color") or "#CC2200"
        secondary    = cfg.get("secondary_color") or "#DC2626"
        ac_date_str  = None   # set below for Autocall, stays None for other types

        # Load company logo (PNG/JPG, optional)
        logo_bytes: bytes | None = None
        for _ext in ("png", "jpg", "jpeg"):
            _lp = _TEMPLATES_DIR / f"company_logo.{_ext}"
            if _lp.exists():
                logo_bytes = _lp.read_bytes()
                break

        # For Autocall: verify prices on observation dates before generating
        if ftype == "Autocall":
            unds_list = [
                str(product.get(f"underlying_{i}")).strip()
                for i in range(1, 5)
                if product.get(f"underlying_{i}")
                and str(product.get(f"underlying_{i}")).strip() not in ("", "nan", "None")
            ]
            trigger = _safe_float(product.get("trigger_autocall")) or 1.0
            today   = date.today()
            past_obs = tuple(
                d for i in range(1, 11)
                if (d := _parse_date(product.get(f"fecha_autocall_{i}"))) and d <= today
            )
            start_date_str = str(
                product.get("fecha_inicio") or product.get("fecha_strike") or ""
            )

            with st.spinner("Verificando precios en fechas de observación..."):
                did_ac, ac_date_str, msg = _verify_autocall_prices(
                    tuple(unds_list), start_date_str, trigger, past_obs
                )

            if not did_ac:
                st.error(msg)
                return

            if ac_date_str:
                try:
                    from datetime import datetime as _dt
                    _d = _dt.strptime(ac_date_str, "%Y-%m-%d")
                    _MESES = ["Ene","Feb","Mar","Abr","May","Jun",
                              "Jul","Ago","Set","Oct","Nov","Dic"]
                    ac_display = f"{_d.day:02d}-{_MESES[_d.month-1]}-{str(_d.year)[2:]}"
                except Exception:
                    ac_display = ac_date_str
                st.info(f"Autocall verificado en fecha de observación: **{ac_display}**")

        with st.spinner(f"Generating {ftype} factsheet — fetching market data..."):
            try:
                # Route to specialized generators
                if is_participation_product(product):
                    pdf_bytes = generate_factsheet_participation(
                        product=product,
                        event_type=ftype,
                        company_name=company_name,
                        primary=primary,
                        secondary=secondary,
                        logo_bytes=logo_bytes,
                        disclaimer=disclaimer.strip() or None,
                    )
                elif ftype == "Ejecutado":
                    pdf_bytes = generate_factsheet_ejecutado_dist(
                        product=product,
                        company_name=company_name,
                        primary=primary,
                        secondary=secondary,
                        logo_bytes=logo_bytes,
                        disclaimer=disclaimer.strip() or None,
                    )
                else:
                    pdf_bytes = generate_factsheet_pdf(
                        product=product,
                        event_type=ftype,
                        company_name=company_name,
                        primary=primary,
                        secondary=secondary,
                        verified_autocall_date=ac_date_str if ftype == "Autocall" else None,
                        logo_bytes=logo_bytes,
                        disclaimer=disclaimer.strip() or None,
                    )
                st.success(f"Factsheet **{ftype}** generado correctamente.")

                safe = selected[:50].replace("/", "-").replace("\\", "-").replace(":", "-")
                file_name = f"{ftype} – {safe}.pptx"
                st.download_button(
                    label=f"Descargar PPTX — {file_name}",
                    data=pdf_bytes,
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    type="primary",
                    use_container_width=True,
                )

            except Exception as e:
                st.error(f"Factsheet generation failed: {e}")
                st.exception(e)

    # ── Legend ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.caption(
        "**Validación de tipos:**  "
        "Autocall — verifica precios reales en fechas de observación vs. trigger  |  "
        "Vencimiento — fecha obs. final o vencimiento ya pasó  |  "
        "Ejecutado — termsheet cargado"
    )
