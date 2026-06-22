import streamlit as st
import pandas as pd
from datetime import date
from backend.database import get_all_products
from backend.factsheet import generate_factsheet_pdf
import backend.config as cfg

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


def _has_termsheet(p: dict) -> bool:
    """True if the product has enough termsheet data to generate a factsheet."""
    has_underlying = any(
        p.get(f"underlying_{i}") and
        str(p.get(f"underlying_{i}")).strip() not in ("", "nan", "None")
        for i in range(1, 5)
    )
    has_dates = bool(p.get("fecha_inicio") or p.get("fecha_strike"))
    return has_underlying and has_dates


def _validate(ftype: str, p: dict) -> tuple[bool, str]:
    """
    Returns (is_valid, reason_if_invalid).
    ftype: "Autocall" | "Vencimiento" | "Ejecutado"
    """
    status = str(p.get("status") or "").upper()

    if ftype == "Autocall":
        if status != "AUTOCALL":
            return False, (
                f"El producto tiene status **{status}**, no AUTOCALL. "
                "Solo se puede generar el factsheet Autocall cuando el producto "
                "ya fue llamado anticipadamente."
            )
        return True, ""

    if ftype == "Vencimiento":
        # Allow if status=VENCIDO or fecha_vencimiento is in the past
        if status == "VENCIDO":
            return True, ""
        vcto = p.get("fecha_vencimiento")
        if vcto:
            try:
                d = pd.to_datetime(str(vcto), dayfirst=True, errors="coerce")
                if pd.notna(d) and d.date() <= date.today():
                    return True, ""
            except Exception:
                pass
        return False, (
            f"El producto tiene status **{status}** y su fecha de vencimiento "
            "aún no ha llegado. Solo se puede generar el factsheet Vencimiento "
            "cuando el producto ya venció."
        )

    if ftype == "Ejecutado":
        if status == "POR EJECUTAR":
            return False, (
                "El producto está **POR EJECUTAR** — aún no se ha tradeado y "
                "no tiene termsheet. No se puede generar un factsheet Ejecutado."
            )
        if not _has_termsheet(p):
            return False, (
                "El producto no tiene datos de termsheet (subyacentes, fechas). "
                "Carga primero el termsheet desde el tab de Load Product."
            )
        return True, ""

    return False, "Tipo de factsheet desconocido."


def render():
    st.subheader("Generate Factsheet")

    df = get_all_products()
    if df.empty:
        st.warning("No products found. Load products first.")
        return

    # ── Selectors ─────────────────────────────────────────────────────────────
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

    # ── Status badge ──────────────────────────────────────────────────────────
    st.markdown(_badge(status), unsafe_allow_html=True)

    # ── Validation ───────────────────────────────────────────────────────────
    valid, reason = _validate(ftype, product)
    if not valid:
        st.error(f"**No se puede generar factsheet {ftype}:** {reason}")

    # ── Product KPIs ──────────────────────────────────────────────────────────
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

        company_name = cfg.get("company_name") or "My Company"
        primary      = cfg.get("primary_color") or "#CC2200"

        # Override status temporarily so factsheet uses the chosen type
        product_copy = dict(product)
        _STATUS_OVERRIDE = {
            "Autocall":   "AUTOCALL",
            "Vencimiento": "VENCIDO",
            "Ejecutado":  "VIGENTE",
        }
        product_copy["status"] = _STATUS_OVERRIDE[ftype]

        with st.spinner(f"Generating {ftype} factsheet — fetching market data..."):
            try:
                pdf_bytes = generate_factsheet_pdf(
                    product=product_copy,
                    company_name=company_name,
                    primary=primary,
                )
                st.success(f"Factsheet **{ftype}** generado correctamente.")

                file_name = (
                    f"Factsheet_{ftype}_{selected[:40].replace(' ', '_')}.pdf"
                )
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

    # ── Legend ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.caption(
        "**Validación de tipos:**  "
        "Autocall — solo si status=AUTOCALL  |  "
        "Vencimiento — solo si status=VENCIDO o fecha de vencimiento ya pasó  |  "
        "Ejecutado — solo si tiene termsheet y no es POR EJECUTAR"
    )
