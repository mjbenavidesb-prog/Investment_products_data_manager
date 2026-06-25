"""
Load Product tab — two-panel layout.

Left panel  (auto-filled by Claude AI): financial structure, underlyings, dates, barriers, product engineering.
Right panel (manual user input): identity, classification, amounts, segment breakdown.
"""

import json as _json
import os
import streamlit as st
from datetime import date, datetime
import backend.config as cfg
from backend.database import insert_product, get_all_products
from backend.extractor import extract_termsheet


def _to_date(val) -> date:
    if not val:
        return date.today()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%b-%y", "%d-%b-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(val), fmt).date()
        except ValueError:
            continue
    return date.today()


def _safe_float(val, default=0.0) -> float:
    try:
        v = float(val)
        return default if (v != v) else v
    except (TypeError, ValueError):
        return default


def _pct_display(raw_val) -> float:
    """Convert extracted decimal to display percentage. Returns 0.0 for null/missing (no default fallback)."""
    v = _safe_float(raw_val, 0.0)
    if v > 1:
        v /= 100
    return round(v * 100, 2)


def _auto_status(trade_date: date, maturity_date: date) -> str:
    today = date.today()
    if trade_date >= today:
        return "POR EJECUTAR"
    if maturity_date <= today:
        return "VENCIDO"
    return "VIGENTE"


# ── Dropdown options ──────────────────────────────────────────────────────────
_ELEM_1_TYPES = [
    "Daily Range Accrual",
    "Phoenix Autocall",
    "Phoenix with Memory",
    "Athena Autocall",
    "Fixed Coupon",
    "Digital Coupon",
    "Capital Protected Participation",
    "Long Call (ATM)",
    "Long Call (ITM)",
    "Other",
]
_ELEM_2_TYPES = [
    "None",
    "Low Strike Put",
    "KI Put (European)",
    "KI Put (American)",
    "KO Put (ATM)",
    "Short Put (ATM)",
    "Low Strike Call",
    "Short Call (OTM)",
    "Other",
]
_ELEM_3_TYPES = [
    "None",
    "Low Strike Put",
    "KI Put (European)",
    "KI Put (American)",
    "KO Put (ATM)",
    "Short Put (ATM)",
    "Short Call (OTM)",
    "Short Put (OTM)",
    "Other",
]
_POSITIONS   = ["Long", "Short"]
_STATUS_OPTS = ["POR EJECUTAR", "VIGENTE", "AUTOCALL", "VENCIDO", "CANCELADO"]


def render():
    st.subheader("Load Product")

    # ── Upload & Extract ──────────────────────────────────────────────────────
    api_key = cfg.get("claude_api_key") or os.environ.get("ANTHROPIC_API_KEY") or ""
    if not api_key:
        st.warning("Claude API key not set — add it in Settings or as ANTHROPIC_API_KEY secret.")

    up_col, btn_col, clr_col = st.columns([4, 2, 1])
    with up_col:
        uploaded = st.file_uploader("Upload Termsheet PDF", type=["pdf"], label_visibility="collapsed")
    with btn_col:
        if uploaded and api_key:
            if st.button("Extract with Claude AI", type="primary", use_container_width=True):
                with st.spinner("Reading termsheet..."):
                    try:
                        result = extract_termsheet(uploaded.read(), api_key, filename=uploaded.name)
                        st.session_state["extracted"] = result
                        st.success("Extraction complete — review and correct the fields below.")
                    except Exception as e:
                        st.error(f"Extraction failed: {e}")
    with clr_col:
        if st.session_state.get("extracted"):
            if st.button("Clear", use_container_width=True):
                st.session_state["extracted"] = None
                st.rerun()

    if "extracted" not in st.session_state:
        st.session_state["extracted"] = None

    ex = st.session_state.get("extracted") or {}
    existing_names = get_all_products()["nombre_producto"].dropna().tolist()

    st.markdown("---")

    # Pre-compute auto-filled values
    _trade_pre    = _to_date(ex.get("fecha_inicio") or ex.get("fecha_strike"))
    _maturity_pre = _to_date(ex.get("fecha_vencimiento"))
    _auto_st      = _auto_status(_trade_pre, _maturity_pre) if ex else "POR EJECUTAR"
    _max_gain_pre = ex.get("ganancia_maxima") or ""
    _plazo_pre    = int(_safe_float(ex.get("plazo_meses")))

    # ── Form ─────────────────────────────────────────────────────────────────
    with st.form("product_form", border=True):
        left, right = st.columns([11, 9])

        # ══════════════════════════════════════════════════════════════════════
        # LEFT — Auto-filled from termsheet
        # ══════════════════════════════════════════════════════════════════════
        with left:
            st.markdown("#### Extracted from Termsheet")
            st.caption("Fields populated by Claude AI — review and correct if needed.")

            # Identity row
            id1, id2, id3 = st.columns(3)
            with id1:
                isin = st.text_input("ISIN", value=ex.get("isin") or ex.get("cusip") or "")
            with id2:
                tipo_opts = ["Note", "Certificate", "Warrant", "Bond"]
                tipo_val  = ex.get("tipo", "Note")
                tipo = st.selectbox("Type", tipo_opts,
                    index=tipo_opts.index(tipo_val) if tipo_val in tipo_opts else 0)
            with id3:
                moneda_opts = ["USD", "EUR", "GBP", "PEN", "CLP", "COP"]
                mon_val = ex.get("moneda", "USD")
                moneda = st.selectbox("Currency", moneda_opts,
                    index=moneda_opts.index(mon_val) if mon_val in moneda_opts else 0)

            contraparte = st.text_input("Guarantor / Counterparty",
                value=ex.get("contraparte") or ex.get("garante") or "")

            # Underlyings
            st.markdown("**Underlyings**")
            u1c, u2c, u3c, u4c = st.columns(4)
            with u1c:
                u1 = st.text_input("U1 Ticker", value=ex.get("underlying_1") or "")
                s1 = st.number_input("U1 Initial Level", value=_safe_float(ex.get("strike_1")),
                    min_value=0.0, step=0.01, format="%.4f")
            with u2c:
                u2 = st.text_input("U2 Ticker", value=ex.get("underlying_2") or "")
                s2 = st.number_input("U2 Initial Level", value=_safe_float(ex.get("strike_2")),
                    min_value=0.0, step=0.01, format="%.4f")
            with u3c:
                u3 = st.text_input("U3 Ticker", value=ex.get("underlying_3") or "")
                s3 = st.number_input("U3 Initial Level", value=_safe_float(ex.get("strike_3")),
                    min_value=0.0, step=0.01, format="%.4f")
            with u4c:
                u4 = st.text_input("U4 Ticker", value=ex.get("underlying_4") or "")
                s4 = st.number_input("U4 Initial Level", value=_safe_float(ex.get("strike_4")),
                    min_value=0.0, step=0.01, format="%.4f")

            fmt_opts = ["Worst of", "Individual", "Basket"]
            fmt_val  = ex.get("formato_subyacente", "Worst of")
            formato_subyacente = st.selectbox("Underlying Structure", fmt_opts,
                index=fmt_opts.index(fmt_val) if fmt_val in fmt_opts else 0)

            # Key Dates
            st.markdown("**Key Dates**")
            fd1, fd2, fd3 = st.columns(3)
            with fd1:
                fecha_inicio = st.date_input("Trade Date",
                    value=_to_date(ex.get("fecha_inicio") or ex.get("fecha_strike")))
            with fd2:
                fecha_obs_final = st.date_input("Final Obs. Date",
                    value=_to_date(ex.get("fecha_obs_final")))
            with fd3:
                fecha_vencimiento = st.date_input("Maturity Date",
                    value=_to_date(ex.get("fecha_vencimiento")))

            # Tenor & Max Gain
            tg1, tg2 = st.columns(2)
            with tg1:
                plazo_meses = st.number_input("Tenor (months)",
                    value=_plazo_pre, min_value=0, step=1,
                    help="Extracted from termsheet — edit if needed.")
            with tg2:
                ganancia_maxima = st.text_input("Maximum Gain",
                    value=_max_gain_pre,
                    help="E.g. '33%', '16.25%', 'Ilimitada'. Extracted by AI — editable.")

            # Coupon & Barriers
            st.markdown("**Coupon & Barriers**")
            cb1, cb2, cb3, cb4 = st.columns(4)
            with cb1:
                cupon_raw = _safe_float(ex.get("cupon_contingente") or ex.get("cupon_fijo"))
                if cupon_raw > 1:
                    cupon_raw /= 100
                cupon_contingente = st.number_input("Coupon p.a. (%)",
                    value=round(cupon_raw * 100, 4), min_value=0.0, max_value=100.0, step=0.01)
            with cb2:
                barrera_cupon = st.number_input("Coupon Barrier (%)",
                    value=_pct_display(ex.get("barrera_cupon")),
                    min_value=0.0, max_value=150.0, step=0.5,
                    help="0 = no coupon barrier (e.g. participation products)")
            with cb3:
                barrera_capital = st.number_input("Capital Barrier (%)",
                    value=_pct_display(ex.get("barrera_capital")),
                    min_value=0.0, max_value=150.0, step=0.5)
            with cb4:
                trig_raw = _safe_float(ex.get("trigger_autocall"), 0.0)
                if trig_raw > 1:
                    trig_raw /= 100
                trigger_autocall = st.number_input("Autocall Trigger (%)",
                    value=round(trig_raw * 100, 2), min_value=0.0, max_value=200.0, step=1.0)

            # Asset class
            ac_opts = cfg.get("asset_classes") or cfg.DEFAULTS["asset_classes"]
            ac_val  = ex.get("asset_class", ac_opts[0])
            asset_class = st.selectbox("Asset Class", ac_opts,
                index=ac_opts.index(ac_val) if ac_val in ac_opts else 0)

            # Autocall observation dates
            st.markdown("**Autocall / Knock-Out Observation Dates**")
            n_extracted = sum(1 for i in range(1, 11) if ex.get(f"fecha_autocall_{i}"))
            n_autocalls = st.number_input("Number of dates", min_value=0, max_value=10,
                value=n_extracted, step=1)
            ac_dates = []
            if n_autocalls > 0:
                ac_cols = st.columns(min(int(n_autocalls), 5))
                for i in range(int(n_autocalls)):
                    with ac_cols[i % 5]:
                        d = st.date_input(f"AC {i+1}",
                            value=_to_date(ex.get(f"fecha_autocall_{i+1}")), key=f"ac_{i}")
                        ac_dates.append(d)

            # ── Product Engineering ──────────────────────────────────────────
            st.markdown("---")
            st.markdown("**Product Engineering**")
            st.caption("Derivative building blocks — AI-extracted, editable.")

            e1a, e1b, e1c = st.columns([3, 2, 2])
            with e1a:
                e1_val = ex.get("elemento_1_tipo", "")
                e1_idx = _ELEM_1_TYPES.index(e1_val) if e1_val in _ELEM_1_TYPES else 0
                elemento_1_tipo = st.selectbox("Element 1", _ELEM_1_TYPES, index=e1_idx)
            with e1b:
                elemento_1_leverage = st.number_input("Leverage 1",
                    value=_safe_float(ex.get("elemento_1_leverage"), 1.0),
                    min_value=0.0, max_value=10.0, step=0.001, format="%.3f")
            with e1c:
                e1p_val = ex.get("elemento_1_posicion", "Long")
                elemento_1_posicion = st.selectbox("Position 1", _POSITIONS,
                    index=_POSITIONS.index(e1p_val) if e1p_val in _POSITIONS else 0)

            e2a, e2b, e2c = st.columns([3, 2, 2])
            with e2a:
                e2_val = ex.get("elemento_2_tipo") or "None"
                e2_idx = _ELEM_2_TYPES.index(e2_val) if e2_val in _ELEM_2_TYPES else 0
                elemento_2_tipo = st.selectbox("Element 2", _ELEM_2_TYPES, index=e2_idx)
            with e2b:
                elemento_2_leverage = st.number_input("Leverage 2",
                    value=_safe_float(ex.get("elemento_2_leverage"), 1.0),
                    min_value=0.0, max_value=10.0, step=0.001, format="%.3f")
            with e2c:
                e2p_val = ex.get("elemento_2_posicion", "Short")
                elemento_2_posicion = st.selectbox("Position 2", _POSITIONS,
                    index=_POSITIONS.index(e2p_val) if e2p_val in _POSITIONS else 1)

            e3a, e3b, e3c = st.columns([3, 2, 2])
            with e3a:
                e3_val = ex.get("elemento_3_tipo") or "None"
                e3_idx = _ELEM_3_TYPES.index(e3_val) if e3_val in _ELEM_3_TYPES else 0
                elemento_3_tipo = st.selectbox("Element 3", _ELEM_3_TYPES, index=e3_idx)
            with e3b:
                elemento_3_leverage = st.number_input("Leverage 3",
                    value=_safe_float(ex.get("elemento_3_leverage"), 1.0),
                    min_value=0.0, max_value=10.0, step=0.001, format="%.3f")
            with e3c:
                e3p_val = ex.get("elemento_3_posicion", "Short")
                elemento_3_posicion = st.selectbox("Position 3", _POSITIONS,
                    index=_POSITIONS.index(e3p_val) if e3p_val in _POSITIONS else 1)

        # ══════════════════════════════════════════════════════════════════════
        # RIGHT — Manual inputs
        # ══════════════════════════════════════════════════════════════════════
        with right:
            st.markdown("#### Manual Input")
            st.caption("Fields requiring user input.")

            nombre_producto = st.text_input("Product Name *",
                value=ex.get("nombre_producto") or "",
                help="Internal commercial name")

            status = st.selectbox("Status", _STATUS_OPTS,
                index=_STATUS_OPTS.index(_auto_st) if _auto_st in _STATUS_OPTS else 0,
                help="Auto-calculated from trade/maturity dates — override if needed.")

            vehicle_opts = cfg.get("vehicles") or cfg.DEFAULTS["vehicles"]
            vehiculo = st.selectbox("Vehicle", vehicle_opts)

            entity_opts = cfg.get("entities") or cfg.DEFAULTS["entities"]
            entidad = st.selectbox("Entity", entity_opts)

            juris_opts = cfg.get("jurisdictions") or cfg.DEFAULTS["jurisdictions"]
            jurisdiccion = st.selectbox("Jurisdiction", juris_opts)

            profile_opts = cfg.get("profiles") or cfg.DEFAULTS["profiles"]
            p_val = ex.get("perfil", profile_opts[0])
            perfil = st.selectbox("Risk Profile", profile_opts,
                index=profile_opts.index(p_val) if p_val in profile_opts else 0)

            client_opts = cfg.get("client_types") or cfg.DEFAULTS["client_types"]
            tipo_cliente = st.selectbox("Client Type", client_opts)

            dias_habiles_pago = st.number_input("Business Days to Client Payment",
                value=int(_safe_float(ex.get("dias_habiles_pago"),
                    cfg.get("business_days_payment") or 3)),
                min_value=0, max_value=30, step=1,
                help="Added to Final Obs. Date to compute client payment date.")

            # AUM by country
            st.markdown("**AUM by Country (USD)**")
            r1, r2 = st.columns(2)
            with r1:
                monto_peru     = st.number_input("Peru", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_colombia = st.number_input("Colombia", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
            with r2:
                monto_chile = st.number_input("Chile", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_usa   = st.number_input("USA", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")

            # Segment breakdown
            st.markdown("**Segment Breakdown (USD)**")
            sg1, sg2 = st.columns(2)
            with sg1:
                monto_bp_peru     = st.number_input("BP Peru", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_bp_chile    = st.number_input("BP Chile", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_bp_colombia = st.number_input("BP Colombia", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_bp_us       = st.number_input("BP US", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_ria         = st.number_input("RIA", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
            with sg2:
                monto_w9    = st.number_input("W9", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_enalta = st.number_input("Enalta", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_bex   = st.number_input("BEX", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_mfo   = st.number_input("MFO", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_tyba  = st.number_input("TYBA", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")

            # ── Custom fields from Settings ───────────────────────────────────
            custom_field_defs = cfg.get("custom_fields") or []
            custom_values = {}
            if custom_field_defs:
                st.markdown("**Campos Adicionales**")
                for _cf in custom_field_defs:
                    _lbl  = _cf.get("label", "")
                    _key  = _cf.get("key") or _lbl.lower().replace(" ", "_")
                    _opts = _cf.get("options", [])
                    _wkey = f"cf_{_key}"
                    if _opts:
                        custom_values[_key] = st.selectbox(_lbl, _opts, key=_wkey)
                    else:
                        custom_values[_key] = st.text_input(_lbl, value="", key=_wkey)

        # ── Submit ────────────────────────────────────────────────────────────
        submitted = st.form_submit_button(
            "Save Product to Database", type="primary", use_container_width=True
        )

    # ── Save ─────────────────────────────────────────────────────────────────
    if submitted:
        if not nombre_producto.strip():
            st.error("Product name is required.")
            return
        if nombre_producto.strip() in existing_names:
            st.error(f"Product '{nombre_producto}' already exists in the database.")
            return

        monto_total = monto_peru + monto_chile + monto_colombia + monto_usa

        record = {
            "nombre_producto":    nombre_producto.strip(),
            "isin":               isin or None,
            "tipo":               tipo,
            "status":             status,
            "contraparte":        contraparte or None,
            "contraparte_derivado": None,
            "asset_class":        asset_class,
            "vehiculo":           vehiculo,
            "entidad":            entidad,
            "tipo_cliente":       tipo_cliente,
            "perfil":             perfil,
            "jurisdiccion":       jurisdiccion,
            "moneda":             moneda,
            "monto_total":        monto_total,
            "monto_peru":         monto_peru,
            "monto_chile":        monto_chile,
            "monto_colombia":     monto_colombia,
            "monto_usa":          monto_usa,
            "monto_bp_peru":      monto_bp_peru,
            "monto_bp_chile":     monto_bp_chile,
            "monto_bp_colombia":  monto_bp_colombia,
            "monto_bp_us":        monto_bp_us,
            "monto_ria":          monto_ria,
            "monto_w9":           monto_w9,
            "monto_enalta":       monto_enalta,
            "monto_bex":          monto_bex,
            "monto_mfo":          monto_mfo,
            "monto_tyba":         monto_tyba,
            "fecha_inicio":       fecha_inicio.isoformat(),
            "fecha_strike":       fecha_inicio.isoformat(),
            "fecha_obs_final":    fecha_obs_final.isoformat(),
            "fecha_vencimiento":  fecha_vencimiento.isoformat(),
            "fecha_pago_maximo":  fecha_vencimiento.isoformat(),
            "dias_habiles_pago":  int(dias_habiles_pago),
            "underlying_1":       u1 or None,
            "underlying_2":       u2 or None,
            "underlying_3":       u3 or None,
            "underlying_4":       u4 or None,
            "strike_1":           s1 if u1 and s1 > 0 else None,
            "strike_2":           s2 if u2 and s2 > 0 else None,
            "strike_3":           s3 if u3 and s3 > 0 else None,
            "strike_4":           s4 if u4 and s4 > 0 else None,
            "formato_subyacente": formato_subyacente,
            "cupon_contingente":  cupon_contingente / 100,
            "barrera_cupon":      barrera_cupon / 100 if barrera_cupon else None,
            "barrera_capital":    barrera_capital / 100 if barrera_capital else None,
            "trigger_autocall":   trigger_autocall / 100 if trigger_autocall else None,
            "ganancia_maxima":    ganancia_maxima or None,
            "plazo_meses":        int(plazo_meses),
            "elemento_1_tipo":    elemento_1_tipo,
            "elemento_1_leverage": elemento_1_leverage,
            "elemento_1_posicion": elemento_1_posicion,
            "elemento_2_tipo":    elemento_2_tipo if elemento_2_tipo != "None" else None,
            "elemento_2_leverage": elemento_2_leverage if elemento_2_tipo != "None" else None,
            "elemento_2_posicion": elemento_2_posicion if elemento_2_tipo != "None" else None,
            "elemento_3_tipo":    elemento_3_tipo if elemento_3_tipo != "None" else None,
            "elemento_3_leverage": elemento_3_leverage if elemento_3_tipo != "None" else None,
            "elemento_3_posicion": elemento_3_posicion if elemento_3_tipo != "None" else None,
        }

        for i, d in enumerate(ac_dates):
            record[f"fecha_autocall_{i+1}"] = d.isoformat()

        if custom_values:
            record["custom_fields_json"] = _json.dumps(custom_values, ensure_ascii=False)

        try:
            insert_product(record)
            st.success(f"Product '{nombre_producto}' saved successfully.")
            st.session_state["extracted"] = None
            st.rerun()
        except Exception as e:
            st.error(f"Error saving product: {e}")
