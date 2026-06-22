"""
Load Product tab.

Workflow:
  Step 1 — Upload termsheet PDF → Claude extracts all financial fields.
  Step 2 — User fills in ONLY what isn't in the termsheet:
            product name, status, vehicle/entity, and amount breakdown.
  Step 3 — Save to DB.
"""

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
        return default if (v != v) else v   # NaN check
    except (TypeError, ValueError):
        return default


def _pct_to_decimal(val) -> float:
    """Convert percentage input (e.g. 80.0) to decimal (0.80). If already ≤1, keep as-is."""
    v = _safe_float(val)
    return v / 100 if v > 1 else v


def render():
    st.subheader("Load Product")

    # ── Step 1: Upload & Extract ──────────────────────────────────────────────
    st.markdown("### Step 1 — Upload Termsheet PDF")
    api_key = cfg.get("claude_api_key") or ""

    if not api_key:
        st.warning("Claude API key not set — go to ⚙️ Settings to add it.")

    uploaded = st.file_uploader("Drop termsheet PDF here", type=["pdf"])

    if "extracted" not in st.session_state:
        st.session_state["extracted"] = None

    col_btn, col_clear = st.columns([2, 1])
    with col_btn:
        if uploaded and api_key:
            if st.button("Extract with Claude AI", type="primary"):
                with st.spinner("Reading termsheet..."):
                    try:
                        result = extract_termsheet(uploaded.read(), api_key)
                        st.session_state["extracted"] = result
                        st.success("Extraction complete — review the pre-filled fields below.")
                    except Exception as e:
                        st.error(f"Extraction failed: {e}")
    with col_clear:
        if st.session_state.get("extracted"):
            if st.button("Clear", use_container_width=True):
                st.session_state["extracted"] = None
                st.rerun()

    ex = st.session_state.get("extracted") or {}

    if ex:
        with st.expander("Extracted fields from termsheet", expanded=False):
            st.json(ex)

    st.markdown("---")

    # ── Step 2: Form ──────────────────────────────────────────────────────────
    st.markdown("### Step 2 — Product Information")
    st.caption(
        "Fields marked **auto-filled** come from the termsheet. "
        "You only need to fill in **Product Name**, **Status**, and the **amount breakdown**."
    )

    existing_names = get_all_products()["nombre_producto"].dropna().tolist()

    with st.form("product_form", border=True):

        # ── A: Identity (manual + auto) ───────────────────────────────────────
        st.markdown("#### A · Identity")
        col1, col2, col3 = st.columns(3)
        with col1:
            nombre_producto = st.text_input(
                "Product Name *",
                value=ex.get("nombre_producto", ""),
                help="Internal commercial name (e.g. 'Phoenix WO RTY-SPX 80% Jun26')",
            )
        with col2:
            status_options = ["POR EJECUTAR", "VIGENTE", "AUTOCALL",
                              "VENCIDO", "EJECUTADO", "CANCELADO"]
            status = st.selectbox("Status *", status_options, index=0)
        with col3:
            moneda_opts = ["USD", "EUR", "GBP", "PEN", "CLP", "COP"]
            mon_default = ex.get("moneda", "USD")
            moneda = st.selectbox(
                "Currency (auto-filled)",
                moneda_opts,
                index=moneda_opts.index(mon_default) if mon_default in moneda_opts else 0,
            )

        # ── B: Classification (manual) ────────────────────────────────────────
        st.markdown("#### B · Internal Classification")
        col4, col5, col6 = st.columns(3)
        with col4:
            vehicle_opts = cfg.get("vehicles") or cfg.DEFAULTS["vehicles"]
            vehiculo = st.selectbox("Vehicle", vehicle_opts)
        with col5:
            entity_opts = cfg.get("entities") or cfg.DEFAULTS["entities"]
            entidad = st.selectbox("Entity", entity_opts)
        with col6:
            juris_opts = cfg.get("jurisdictions") or cfg.DEFAULTS["jurisdictions"]
            jurisdiccion = st.selectbox("Jurisdiction", juris_opts)

        col7, col8 = st.columns(2)
        with col7:
            profile_opts = cfg.get("profiles") or cfg.DEFAULTS["profiles"]
            p_default = ex.get("perfil", profile_opts[0])
            perfil = st.selectbox(
                "Risk Profile (auto-filled)",
                profile_opts,
                index=profile_opts.index(p_default) if p_default in profile_opts else 0,
            )
        with col8:
            client_opts = cfg.get("client_types") or cfg.DEFAULTS["client_types"]
            tipo_cliente = st.selectbox("Client Type", client_opts)

        # ── C: Amounts (manual — not in termsheet) ────────────────────────────
        st.markdown("#### C · Amount Breakdown (USD)")
        st.caption(
            "The termsheet issue amount is shown for reference. "
            "Enter the actual amounts per country/segment."
        )
        issue_amt = _safe_float(ex.get("monto_total"))
        if issue_amt:
            st.info(f"Termsheet issue amount: **{ex.get('moneda','USD')} {issue_amt:,.0f}**")

        ca, cb, cc, cd = st.columns(4)
        with ca:
            monto_peru = st.number_input("Peru", value=0.0, min_value=0.0, step=10_000.0, format="%.0f")
        with cb:
            monto_chile = st.number_input("Chile", value=0.0, min_value=0.0, step=10_000.0, format="%.0f")
        with cc:
            monto_colombia = st.number_input("Colombia", value=0.0, min_value=0.0, step=10_000.0, format="%.0f")
        with cd:
            monto_usa = st.number_input("USA", value=0.0, min_value=0.0, step=10_000.0, format="%.0f")

        with st.expander("Segment breakdown (optional)"):
            s1, s2, s3, s4 = st.columns(4)
            with s1:
                monto_bp_peru = st.number_input("BP Peru", value=0.0, min_value=0.0, step=10_000.0, format="%.0f")
                monto_bp_chile = st.number_input("BP Chile", value=0.0, min_value=0.0, step=10_000.0, format="%.0f")
            with s2:
                monto_bp_colombia = st.number_input("BP Colombia", value=0.0, min_value=0.0, step=10_000.0, format="%.0f")
                monto_bp_us = st.number_input("BP US", value=0.0, min_value=0.0, step=10_000.0, format="%.0f")
            with s3:
                monto_ria = st.number_input("RIA", value=0.0, min_value=0.0, step=10_000.0, format="%.0f")
                monto_w9 = st.number_input("W9", value=0.0, min_value=0.0, step=10_000.0, format="%.0f")
                monto_enalta = st.number_input("Enalta", value=0.0, min_value=0.0, step=10_000.0, format="%.0f")
            with s4:
                monto_bex = st.number_input("BEX", value=0.0, min_value=0.0, step=10_000.0, format="%.0f")
                monto_mfo = st.number_input("MFO", value=0.0, min_value=0.0, step=10_000.0, format="%.0f")
                monto_tyba = st.number_input("TYBA", value=0.0, min_value=0.0, step=10_000.0, format="%.0f")

        # ── D: Auto-filled financial data (review only) ───────────────────────
        st.markdown("#### D · Financial Data (auto-filled from termsheet)")
        st.caption("These fields are pre-populated from the termsheet extraction. Edit if needed.")

        d1, d2, d3, d4 = st.columns(4)
        with d1:
            isin = st.text_input("ISIN", value=ex.get("isin") or ex.get("cusip") or "")
            contraparte = st.text_input(
                "Counterparty (Guarantor)",
                value=ex.get("garante") or ex.get("contraparte") or "",
            )
            contraparte_derivado = st.text_input(
                "Issuer Entity",
                value=ex.get("contraparte") or "",
            )
        with d2:
            ac_opts = cfg.get("asset_classes") or cfg.DEFAULTS["asset_classes"]
            ac_default = ex.get("asset_class", ac_opts[0])
            asset_class = st.selectbox(
                "Asset Class",
                ac_opts,
                index=ac_opts.index(ac_default) if ac_default in ac_opts else 0,
            )
            plazo_meses = st.number_input(
                "Term (months)", value=int(_safe_float(ex.get("plazo_meses"))),
                min_value=0, step=1,
            )
        with d3:
            cupon_contingente_raw = _safe_float(ex.get("cupon_contingente"))
            if cupon_contingente_raw > 1:
                cupon_contingente_raw /= 100
            cupon_contingente = st.number_input(
                "Contingent Coupon (% p.a.)",
                value=round(cupon_contingente_raw * 100, 4),
                min_value=0.0, max_value=100.0, step=0.01,
            )
            barrera_raw = _safe_float(ex.get("barrera_capital"))
            if barrera_raw > 1:
                barrera_raw /= 100
            barrera_capital = st.number_input(
                "Capital Barrier (%)",
                value=round(barrera_raw * 100, 2) or 70.0,
                min_value=0.0, max_value=150.0, step=1.0,
            )
        with d4:
            trigger_raw = _safe_float(ex.get("trigger_autocall"), 1.0)
            if trigger_raw > 1:
                trigger_raw /= 100
            trigger_autocall = st.number_input(
                "Autocall Trigger (%)",
                value=round(trigger_raw * 100, 2) or 100.0,
                min_value=0.0, max_value=200.0, step=1.0,
            )
            ganancia_maxima = st.text_input(
                "Max Gain", value=ex.get("ganancia_maxima") or ""
            )

        # Dates
        fd1, fd2, fd3 = st.columns(3)
        with fd1:
            fecha_inicio = st.date_input(
                "Trade / Strike Date",
                value=_to_date(ex.get("fecha_inicio") or ex.get("fecha_strike")),
            )
        with fd2:
            fecha_obs_final = st.date_input(
                "Final Observation Date",
                value=_to_date(ex.get("fecha_obs_final")),
            )
        with fd3:
            fecha_vencimiento = st.date_input(
                "Maturity / Settlement Date",
                value=_to_date(ex.get("fecha_vencimiento")),
            )

        dias_habiles_pago = st.number_input(
            "Business Days to Client Payment",
            value=int(_safe_float(ex.get("dias_habiles_pago"),
                                  cfg.get("business_days_payment") or 3)),
            min_value=0, max_value=30, step=1,
        )

        # Underlyings (auto-filled)
        st.markdown("**Underlyings (Bloomberg tickers & initial levels)**")
        u1c, u2c, u3c, u4c = st.columns(4)
        with u1c:
            u1 = st.text_input("U1 Ticker", value=ex.get("underlying_1", "") or "")
            s1 = st.number_input("U1 Initial Level", value=_safe_float(ex.get("strike_1")), min_value=0.0, step=1.0)
        with u2c:
            u2 = st.text_input("U2 Ticker", value=ex.get("underlying_2", "") or "")
            s2 = st.number_input("U2 Initial Level", value=_safe_float(ex.get("strike_2")), min_value=0.0, step=1.0)
        with u3c:
            u3 = st.text_input("U3 Ticker", value=ex.get("underlying_3", "") or "")
            s3 = st.number_input("U3 Initial Level", value=_safe_float(ex.get("strike_3")), min_value=0.0, step=1.0)
        with u4c:
            u4 = st.text_input("U4 Ticker", value=ex.get("underlying_4", "") or "")
            s4 = st.number_input("U4 Initial Level", value=_safe_float(ex.get("strike_4")), min_value=0.0, step=1.0)

        fmt_opts = ["Worst of", "Individual", "Basket"]
        fmt_default = ex.get("formato_subyacente", "Worst of")
        formato_subyacente = st.selectbox(
            "Underlying Structure",
            fmt_opts,
            index=fmt_opts.index(fmt_default) if fmt_default in fmt_opts else 0,
        )

        # Autocall dates (auto-filled from termsheet)
        st.markdown("**Autocall Observation Dates (auto-filled)**")
        n_ac_extracted = sum(1 for i in range(1, 11) if ex.get(f"fecha_autocall_{i}"))
        n_autocalls = st.number_input(
            "Number of autocall dates",
            min_value=0, max_value=10,
            value=n_ac_extracted, step=1,
        )
        ac_dates = []
        if n_autocalls > 0:
            cols = st.columns(min(int(n_autocalls), 5))
            for i in range(int(n_autocalls)):
                with cols[i % 5]:
                    d = st.date_input(
                        f"AC {i+1}",
                        value=_to_date(ex.get(f"fecha_autocall_{i+1}")),
                        key=f"ac_{i}",
                    )
                    ac_dates.append(d)

        submitted = st.form_submit_button(
            "Save Product to Database", type="primary", use_container_width=True
        )

    # ── Save ──────────────────────────────────────────────────────────────────
    if submitted:
        if not nombre_producto.strip():
            st.error("Product Name is required.")
            return
        if nombre_producto.strip() in existing_names:
            st.error(f"Product '{nombre_producto}' already exists.")
            return

        monto_total = monto_peru + monto_chile + monto_colombia + monto_usa

        record = {
            "nombre_producto": nombre_producto.strip(),
            "isin": isin or None,
            "tipo": ex.get("tipo") or "Note",
            "status": status,
            "contraparte": contraparte or None,
            "contraparte_derivado": contraparte_derivado or None,
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
            "barrera_capital": barrera_capital / 100,
            "trigger_autocall": trigger_autocall / 100,
            "ganancia_maxima": ganancia_maxima or None,
            "plazo_meses": int(plazo_meses),
        }

        for i, d in enumerate(ac_dates):
            record[f"fecha_autocall_{i+1}"] = d.isoformat()

        try:
            insert_product(record)
            st.success(f"Product '{nombre_producto}' saved successfully!")
            st.session_state["extracted"] = None
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save: {e}")
