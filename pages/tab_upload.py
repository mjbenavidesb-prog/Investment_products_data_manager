"""
Load Product tab — two-panel layout.

Left panel  (auto-filled by Claude AI): financial structure, underlyings, dates, barriers, product engineering.
Right panel (manual user input): identity, classification, amounts, segment breakdown.
"""

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


def _auto_status(trade_date: date, maturity_date: date) -> str:
    today = date.today()
    if trade_date >= today:
        return "POR EJECUTAR"
    if maturity_date <= today:
        return "VENCIDO"
    return "VIGENTE"


# ── Dropdown options for product engineering ──────────────────────────────────
_ELEM_1_TYPES = [
    "Daily Range Accrual",
    "Phoenix Autocall",
    "Phoenix with Memory",
    "Athena Autocall",
    "Fixed Coupon",
    "Digital Coupon",
    "Capital Protected Participation",
    "Other",
]
_ELEM_2_TYPES = [
    "None",
    "Low Strike Put",
    "KI Put (European)",
    "KI Put (American)",
    "Vanilla Put (100%)",
    "Low Strike Call",
    "Other",
]
_POSITIONS = ["Long", "Short"]
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
                        result = extract_termsheet(uploaded.read(), api_key)
                        st.session_state["extracted"] = result
                        st.success("Extraction complete — review and complete the fields below.")
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

    # Pre-compute status from extracted dates (before form renders)
    _trade_pre = _to_date(ex.get("fecha_inicio") or ex.get("fecha_strike"))
    _maturity_pre = _to_date(ex.get("fecha_vencimiento"))
    _auto_st = _auto_status(_trade_pre, _maturity_pre) if ex else "POR EJECUTAR"

    # Pre-compute max gain from extracted coupon × years
    _cupon_pre = _safe_float(ex.get("cupon_contingente") or ex.get("cupon_fijo"), 0.0)
    if _cupon_pre > 1:
        _cupon_pre /= 100
    _anos_pre = _safe_float(ex.get("plazo_meses"), 0.0) / 12
    _max_gain_pre = f"{_cupon_pre * _anos_pre * 100:.1f}%" if _cupon_pre and _anos_pre else (ex.get("ganancia_maxima") or "")

    # ── Form ─────────────────────────────────────────────────────────────────
    with st.form("product_form", border=True):
        left, right = st.columns([11, 9])

        # ══════════════════════════════════════════════════════════════════════
        # LEFT — Auto-filled from termsheet
        # ══════════════════════════════════════════════════════════════════════
        with left:
            st.markdown("#### Extraído del Termsheet")
            st.caption("Campos completados por Claude AI — revisa y corrige si es necesario.")

            # Identity row
            id1, id2, id3 = st.columns(3)
            with id1:
                isin = st.text_input("ISIN", value=ex.get("isin") or ex.get("cusip") or "")
            with id2:
                tipo_opts = ["Note", "Certificate", "Warrant", "Bond"]
                tipo_val = ex.get("tipo", "Note")
                tipo = st.selectbox("Tipo", tipo_opts,
                    index=tipo_opts.index(tipo_val) if tipo_val in tipo_opts else 0)
            with id3:
                moneda_opts = ["USD", "EUR", "GBP", "PEN", "CLP", "COP"]
                mon_val = ex.get("moneda", "USD")
                moneda = st.selectbox("Moneda", moneda_opts,
                    index=moneda_opts.index(mon_val) if mon_val in moneda_opts else 0)

            cp1, cp2 = st.columns(2)
            with cp1:
                contraparte = st.text_input("Garante / Contraparte",
                    value=ex.get("contraparte") or ex.get("garante") or "")
            with cp2:
                emisor = st.text_input("Emisor",
                    value=ex.get("emisor") or ex.get("contraparte_derivado") or "")

            # Underlyings
            st.markdown("**Subyacentes**")
            u1c, u2c, u3c, u4c = st.columns(4)
            with u1c:
                u1 = st.text_input("U1 Ticker", value=ex.get("underlying_1") or "")
                s1 = st.number_input("U1 Nivel Inicial", value=_safe_float(ex.get("strike_1")),
                    min_value=0.0, step=0.01, format="%.4f")
            with u2c:
                u2 = st.text_input("U2 Ticker", value=ex.get("underlying_2") or "")
                s2 = st.number_input("U2 Nivel Inicial", value=_safe_float(ex.get("strike_2")),
                    min_value=0.0, step=0.01, format="%.4f")
            with u3c:
                u3 = st.text_input("U3 Ticker", value=ex.get("underlying_3") or "")
                s3 = st.number_input("U3 Nivel Inicial", value=_safe_float(ex.get("strike_3")),
                    min_value=0.0, step=0.01, format="%.4f")
            with u4c:
                u4 = st.text_input("U4 Ticker", value=ex.get("underlying_4") or "")
                s4 = st.number_input("U4 Nivel Inicial", value=_safe_float(ex.get("strike_4")),
                    min_value=0.0, step=0.01, format="%.4f")

            fmt_opts = ["Worst of", "Individual", "Basket"]
            fmt_val = ex.get("formato_subyacente", "Worst of")
            formato_subyacente = st.selectbox("Estructura Subyacente", fmt_opts,
                index=fmt_opts.index(fmt_val) if fmt_val in fmt_opts else 0)

            # Key Dates
            st.markdown("**Fechas Clave**")
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

            # Coupon & Barriers
            st.markdown("**Cupón y Barreras**")
            cb1, cb2, cb3, cb4 = st.columns(4)
            with cb1:
                cupon_raw = _safe_float(ex.get("cupon_contingente") or ex.get("cupon_fijo"))
                if cupon_raw > 1:
                    cupon_raw /= 100
                cupon_contingente = st.number_input("Cupón p.a. (%)",
                    value=round(cupon_raw * 100, 4), min_value=0.0, max_value=100.0, step=0.01)
            with cb2:
                bc_raw = _safe_float(ex.get("barrera_cupon"))
                if bc_raw > 1:
                    bc_raw /= 100
                barrera_cupon = st.number_input("Barrera Cupón (%)",
                    value=round(bc_raw * 100, 2) or 75.0, min_value=0.0, max_value=150.0, step=0.5)
            with cb3:
                bk_raw = _safe_float(ex.get("barrera_capital"))
                if bk_raw > 1:
                    bk_raw /= 100
                barrera_capital = st.number_input("Barrera Capital (%)",
                    value=round(bk_raw * 100, 2) or 75.0, min_value=0.0, max_value=150.0, step=0.5)
            with cb4:
                trig_raw = _safe_float(ex.get("trigger_autocall"), 0.0)
                if trig_raw > 1:
                    trig_raw /= 100
                trigger_autocall = st.number_input("Trigger Autocall (%)",
                    value=round(trig_raw * 100, 2), min_value=0.0, max_value=200.0, step=1.0)

            # Asset class
            ac_opts = cfg.get("asset_classes") or cfg.DEFAULTS["asset_classes"]
            ac_val = ex.get("asset_class", ac_opts[0])
            asset_class = st.selectbox("Asset Class", ac_opts,
                index=ac_opts.index(ac_val) if ac_val in ac_opts else 0)

            # Autocall dates
            st.markdown("**Fechas de Observación Autocall / Knock-Out**")
            n_extracted = sum(1 for i in range(1, 11) if ex.get(f"fecha_autocall_{i}"))
            n_autocalls = st.number_input("Número de fechas", min_value=0, max_value=10,
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
            st.markdown("**Ingeniería del Producto**")
            st.caption("Bloques derivados que componen el producto — extraídos por AI, editables.")

            e1a, e1b, e1c = st.columns([3, 2, 2])
            with e1a:
                e1_val = ex.get("elemento_1_tipo", "")
                e1_idx = _ELEM_1_TYPES.index(e1_val) if e1_val in _ELEM_1_TYPES else 0
                elemento_1_tipo = st.selectbox("Elemento 1", _ELEM_1_TYPES, index=e1_idx)
            with e1b:
                elemento_1_leverage = st.number_input("Leverage 1",
                    value=_safe_float(ex.get("elemento_1_leverage"), 1.0),
                    min_value=0.0, max_value=10.0, step=0.001, format="%.3f")
            with e1c:
                e1p_val = ex.get("elemento_1_posicion", "Long")
                elemento_1_posicion = st.selectbox("Posición 1", _POSITIONS,
                    index=_POSITIONS.index(e1p_val) if e1p_val in _POSITIONS else 0)

            e2a, e2b, e2c = st.columns([3, 2, 2])
            with e2a:
                e2_val = ex.get("elemento_2_tipo") or "None"
                e2_idx = _ELEM_2_TYPES.index(e2_val) if e2_val in _ELEM_2_TYPES else 0
                elemento_2_tipo = st.selectbox("Elemento 2", _ELEM_2_TYPES, index=e2_idx)
            with e2b:
                elemento_2_leverage = st.number_input("Leverage 2",
                    value=_safe_float(ex.get("elemento_2_leverage"), 1.0),
                    min_value=0.0, max_value=10.0, step=0.001, format="%.3f")
            with e2c:
                e2p_val = ex.get("elemento_2_posicion", "Short")
                elemento_2_posicion = st.selectbox("Posición 2", _POSITIONS,
                    index=_POSITIONS.index(e2p_val) if e2p_val in _POSITIONS else 1)

        # ══════════════════════════════════════════════════════════════════════
        # RIGHT — Manual inputs
        # ══════════════════════════════════════════════════════════════════════
        with right:
            st.markdown("#### Ingreso Manual")
            st.caption("Campos que requieren criterio del usuario.")

            nombre_producto = st.text_input("Nombre del Producto *",
                value=ex.get("nombre_producto") or "",
                help="Nombre comercial interno")

            status = st.selectbox("Status *", _STATUS_OPTS,
                index=_STATUS_OPTS.index(_auto_st) if _auto_st in _STATUS_OPTS else 0,
                help="Auto-calculado en base a fechas — editable.")

            vehicle_opts = cfg.get("vehicles") or cfg.DEFAULTS["vehicles"]
            vehiculo = st.selectbox("Vehículo", vehicle_opts)

            entity_opts = cfg.get("entities") or cfg.DEFAULTS["entities"]
            entidad = st.selectbox("Entidad", entity_opts)

            juris_opts = cfg.get("jurisdictions") or cfg.DEFAULTS["jurisdictions"]
            jurisdiccion = st.selectbox("Jurisdicción", juris_opts)

            profile_opts = cfg.get("profiles") or cfg.DEFAULTS["profiles"]
            p_val = ex.get("perfil", profile_opts[0])
            perfil = st.selectbox("Perfil de Riesgo", profile_opts,
                index=profile_opts.index(p_val) if p_val in profile_opts else 0)

            client_opts = cfg.get("client_types") or cfg.DEFAULTS["client_types"]
            tipo_cliente = st.selectbox("Tipo de Cliente", client_opts)

            plazo_meses = st.number_input("Plazo (meses)",
                value=int(_safe_float(ex.get("plazo_meses"))), min_value=0, step=1)

            dias_habiles_pago = st.number_input("Días Hábiles a Pago Cliente",
                value=int(_safe_float(ex.get("dias_habiles_pago"),
                    cfg.get("business_days_payment") or 3)),
                min_value=0, max_value=30, step=1,
                help="Se suma a la Final Obs. Date para calcular la fecha de pago al cliente.")

            ganancia_maxima = st.text_input("Ganancia Máxima",
                value=_max_gain_pre,
                help="Cupón anual × años. Auto-calculado, editable.")

            # AUM by country
            st.markdown("**AUM por País (USD)**")
            r1, r2 = st.columns(2)
            with r1:
                monto_peru = st.number_input("Peru", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_colombia = st.number_input("Colombia", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
            with r2:
                monto_chile = st.number_input("Chile", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_usa = st.number_input("USA", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")

            # Segment breakdown — always visible
            st.markdown("**Desglose por Segmento (USD)**")
            sg1, sg2 = st.columns(2)
            with sg1:
                monto_bp_peru = st.number_input("BP Peru", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_bp_chile = st.number_input("BP Chile", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_bp_colombia = st.number_input("BP Colombia", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_bp_us = st.number_input("BP US", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_ria = st.number_input("RIA", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
            with sg2:
                monto_w9 = st.number_input("W9", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_enalta = st.number_input("Enalta", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_bex = st.number_input("BEX", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_mfo = st.number_input("MFO", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")
                monto_tyba = st.number_input("TYBA", value=0.0, min_value=0.0,
                    step=10_000.0, format="%.0f")

        # ── Submit ────────────────────────────────────────────────────────────
        submitted = st.form_submit_button(
            "Guardar Producto en Base de Datos", type="primary", use_container_width=True
        )

    # ── Save ─────────────────────────────────────────────────────────────────
    if submitted:
        if not nombre_producto.strip():
            st.error("El nombre del producto es obligatorio.")
            return
        if nombre_producto.strip() in existing_names:
            st.error(f"El producto '{nombre_producto}' ya existe en la base de datos.")
            return

        monto_total = monto_peru + monto_chile + monto_colombia + monto_usa

        record = {
            "nombre_producto": nombre_producto.strip(),
            "isin": isin or None,
            "tipo": tipo,
            "status": status,
            "contraparte": contraparte or None,
            "contraparte_derivado": emisor or None,
            "asset_class": asset_class,
            "vehiculo": vehiculo,
            "entidad": entidad,
            "tipo_cliente": tipo_cliente,
            "perfil": perfil,
            "jurisdiccion": jurisdiccion,
            "moneda": moneda,
            "monto_total": monto_total,
            "monto_peru": monto_peru,
            "monto_chile": monto_chile,
            "monto_colombia": monto_colombia,
            "monto_usa": monto_usa,
            "monto_bp_peru": monto_bp_peru,
            "monto_bp_chile": monto_bp_chile,
            "monto_bp_colombia": monto_bp_colombia,
            "monto_bp_us": monto_bp_us,
            "monto_ria": monto_ria,
            "monto_w9": monto_w9,
            "monto_enalta": monto_enalta,
            "monto_bex": monto_bex,
            "monto_mfo": monto_mfo,
            "monto_tyba": monto_tyba,
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_strike": fecha_inicio.isoformat(),
            "fecha_obs_final": fecha_obs_final.isoformat(),
            "fecha_vencimiento": fecha_vencimiento.isoformat(),
            "fecha_pago_maximo": fecha_vencimiento.isoformat(),
            "dias_habiles_pago": int(dias_habiles_pago),
            "underlying_1": u1 or None,
            "underlying_2": u2 or None,
            "underlying_3": u3 or None,
            "underlying_4": u4 or None,
            "strike_1": s1 if u1 and s1 > 0 else None,
            "strike_2": s2 if u2 and s2 > 0 else None,
            "strike_3": s3 if u3 and s3 > 0 else None,
            "strike_4": s4 if u4 and s4 > 0 else None,
            "formato_subyacente": formato_subyacente,
            "cupon_contingente": cupon_contingente / 100,
            "barrera_cupon": barrera_cupon / 100,
            "barrera_capital": barrera_capital / 100,
            "trigger_autocall": trigger_autocall / 100 if trigger_autocall else None,
            "ganancia_maxima": ganancia_maxima or None,
            "plazo_meses": int(plazo_meses),
            "elemento_1_tipo": elemento_1_tipo,
            "elemento_1_leverage": elemento_1_leverage,
            "elemento_1_posicion": elemento_1_posicion,
            "elemento_2_tipo": elemento_2_tipo if elemento_2_tipo != "None" else None,
            "elemento_2_leverage": elemento_2_leverage if elemento_2_tipo != "None" else None,
            "elemento_2_posicion": elemento_2_posicion if elemento_2_tipo != "None" else None,
        }

        for i, d in enumerate(ac_dates):
            record[f"fecha_autocall_{i+1}"] = d.isoformat()

        try:
            insert_product(record)
            st.success(f"Producto '{nombre_producto}' guardado exitosamente.")
            st.session_state["extracted"] = None
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar: {e}")
