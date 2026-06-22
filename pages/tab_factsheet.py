import streamlit as st
import pandas as pd
from backend.database import get_all_products
from backend.factsheet import generate_factsheet_pdf
import backend.config as cfg


def render():
    st.subheader("Generate Factsheet")

    df = get_all_products()
    if df.empty:
        st.warning("No products found. Load products first.")
        return

    # ── Filters ────────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([3, 2, 2])

    with col1:
        product_names = df["nombre_producto"].dropna().tolist()
        selected = st.selectbox("Select Product", product_names)

    with col2:
        event_type = st.selectbox(
            "Factsheet Type",
            ["Autocall", "Vencimiento", "Ejecutado"],
            help=(
                "Autocall: product was called early  |  "
                "Vencimiento: product matured normally  |  "
                "Ejecutado: new product marketing sheet"
            ),
        )

    with col3:
        st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
        generate = st.button("Generate Factsheet", type="primary", use_container_width=True)

    if not selected:
        return

    row = df[df["nombre_producto"] == selected].iloc[0]
    product = row.to_dict()

    st.markdown("---")

    # ── Product KPIs ───────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    aum = product.get("monto_total") or 0
    k1.metric("AUM", f"${float(aum):,.0f}" if aum else "—")
    k2.metric("Maturity", str(product.get("fecha_vencimiento") or "—"))

    underlyings = [product.get(f"underlying_{i}") for i in range(1, 5)
                   if product.get(f"underlying_{i}") and
                   str(product.get(f"underlying_{i}")).strip() not in ("", "nan", "None")]
    k3.metric("Underlyings", " / ".join(underlyings) if underlyings else "—")
    k4.metric("Counterparty", str(product.get("contraparte") or "—"))

    rt = product.get("rendimiento_total")
    if rt is not None:
        rt_f = float(rt)
        rt_pct = rt_f * 100 if abs(rt_f) <= 1 else rt_f
        k5.metric("Total Return", f"{rt_pct:.2f}%")
    else:
        k5.metric("Total Return", "—")

    # ── Details expander ──────────────────────────────────────────────────────
    with st.expander("Product data used for factsheet", expanded=False):
        display_fields = [
            "isin", "moneda", "contraparte", "perfil", "asset_class",
            "plazo_meses", "cupon_contingente", "cupon_fijo", "barrera_capital",
            "trigger_autocall", "ganancia_maxima", "cap", "factor_participacion",
            "fecha_inicio", "fecha_strike", "fecha_emision", "fecha_obs_final",
            "fecha_vencimiento", "rendimiento_total",
            "underlying_1", "strike_1", "spot_1",
            "underlying_2", "strike_2", "spot_2",
            "underlying_3", "strike_3", "spot_3",
            "underlying_4", "strike_4", "spot_4",
            "fecha_autocall_1", "fecha_autocall_2", "fecha_autocall_3",
            "fecha_autocall_4", "fecha_autocall_5",
        ]
        available = {k: product.get(k) for k in display_fields if product.get(k) is not None}
        st.json(available)

    # ── Generation ────────────────────────────────────────────────────────────
    if generate:
        company_name = cfg.get("company_name") or "My Company"
        primary = cfg.get("primary_color") or "#2563EB"
        secondary = cfg.get("secondary_color") or "#DC2626"

        with st.spinner(f"Generating {event_type} factsheet — fetching market data..."):
            try:
                pdf_bytes = generate_factsheet_pdf(
                    product=product,
                    event_type=event_type,
                    company_name=company_name,
                    primary=primary,
                    secondary=secondary,
                )
                st.success("Factsheet generated successfully.")

                file_name = f"Factsheet_{event_type}_{selected[:40].replace(' ', '_')}.pdf"
                st.download_button(
                    label=f"Download PDF — {file_name}",
                    data=pdf_bytes,
                    file_name=file_name,
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                )

            except Exception as e:
                st.error(f"Factsheet generation failed: {e}")
                st.exception(e)

    # ── Note about customisation ───────────────────────────────────────────────
    st.markdown("---")
    st.info(
        "**Factsheet types:**\n"
        "- **Autocall** — product was called early on an observation date. "
        "Shows actual return and coupon payments made.\n"
        "- **Vencimiento** — product reached its scheduled maturity. "
        "Shows final performance vs initial levels.\n"
        "- **Ejecutado** — new product being offered. "
        "Shows product structure, payoff, and observation schedule.\n\n"
        "The factsheet uses live price data from yfinance for the performance chart. "
        "Colors follow your company branding configured in ⚙️ Settings."
    )
