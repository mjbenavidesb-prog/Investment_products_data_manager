import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta
from backend.database import get_all_products
import backend.config as cfg

_CARD_BG = "#1c1c2e"
_GRID = "#2d2d4e"
_TEXT = "#f0f2f6"
_SUB = "#a0aec0"


def fmt_usd(val):
    if pd.isna(val) or val == 0:
        return "$0"
    if abs(val) >= 1_000_000:
        return f"${val/1_000_000:.1f}M"
    return f"${val:,.0f}"


def render():
    palette = cfg.color_sequence()
    primary = palette[0]
    secondary = palette[1]
    accent = palette[2]

    st.subheader("Upcoming Maturities & Autocalls")

    df = get_all_products()
    if df.empty:
        st.warning("No products found.")
        return

    active = df[df["status"].isin(["VIGENTE", "POR EJECUTAR", "AUTOCALL"])].copy()
    today = pd.Timestamp.now().normalize()

    active["_fecha_vcto"] = pd.to_datetime(active["fecha_vencimiento"], dayfirst=True, errors="coerce")

    # Horizon & type filters
    col1, col2 = st.columns([2, 2])
    with col1:
        horizon = st.selectbox(
            "Horizon",
            options=[30, 60, 90, 180, 365, 9999],
            format_func=lambda x: "All" if x == 9999 else f"Next {x} days",
            index=2,
        )
    with col2:
        event_type = st.radio("Event Type", ["Both", "Maturities", "Autocalls"], horizontal=True)

    cutoff = today + timedelta(days=horizon)

    # ── Maturities ─────────────────────────────────────────────────────────────
    maturities = active[
        (active["_fecha_vcto"] >= today) & (active["_fecha_vcto"] <= cutoff)
    ].copy()
    maturities["days_to_maturity"] = (maturities["_fecha_vcto"] - today).dt.days
    maturities = maturities.sort_values("days_to_maturity")

    # ── Autocalls ──────────────────────────────────────────────────────────────
    ac_cols = [f"fecha_autocall_{i}" for i in range(1, 11)]
    ac_rows = []
    for _, row in active.iterrows():
        for col in ac_cols:
            dt = pd.to_datetime(row.get(col), dayfirst=True, errors="coerce")
            if pd.notna(dt) and today <= dt <= cutoff:
                ac_rows.append({
                    "nombre_producto": row["nombre_producto"],
                    "status": row["status"],
                    "vehiculo": row["vehiculo"],
                    "monto_total": row["monto_total"],
                    "underlying_1": row.get("underlying_1"),
                    "underlying_2": row.get("underlying_2"),
                    "trigger_autocall": row.get("trigger_autocall"),
                    "autocall_date": dt,
                    "days_to_autocall": (dt - today).days,
                    "contraparte": row.get("contraparte"),
                })
                break

    autocalls = pd.DataFrame(ac_rows).sort_values("days_to_autocall") if ac_rows else pd.DataFrame()

    # ── KPI row ────────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    aum_vcto = maturities["monto_total"].sum() if not maturities.empty else 0
    aum_ac = autocalls["monto_total"].sum() if not autocalls.empty else 0
    k1.metric("Maturities in horizon", len(maturities))
    k2.metric("AUM at maturity", fmt_usd(aum_vcto))
    k3.metric("Autocall obs. in horizon", len(autocalls))
    k4.metric("AUM at autocall obs.", fmt_usd(aum_ac))

    st.markdown("---")

    # ── Monthly AUM bar chart ──────────────────────────────────────────────────
    timeline_rows = []
    if event_type in ("Both", "Maturities") and not maturities.empty:
        for _, r in maturities.iterrows():
            timeline_rows.append({
                "Product": r["nombre_producto"][:30],
                "Date": r["_fecha_vcto"],
                "Type": "Maturity",
                "AUM": r["monto_total"],
                "Vehiculo": r.get("vehiculo", "—"),
            })
    if event_type in ("Both", "Autocalls") and not autocalls.empty:
        for _, r in autocalls.iterrows():
            timeline_rows.append({
                "Product": r["nombre_producto"][:30],
                "Date": r["autocall_date"],
                "Type": "Autocall Obs.",
                "AUM": r["monto_total"],
                "Vehiculo": r.get("vehiculo", "—"),
            })

    if timeline_rows:
        tl_df = pd.DataFrame(timeline_rows).sort_values("Date")
        tl_df["Month"] = tl_df["Date"].dt.to_period("M").astype(str)
        monthly = tl_df.groupby(["Month", "Type"])["AUM"].sum().reset_index()

        months = sorted(monthly["Month"].unique())
        month_labels = [pd.Period(m, "M").strftime("%b") for m in months]
        fig = go.Figure()

        for etype, color in [("Maturity", primary), ("Autocall Obs.", secondary)]:
            sub = monthly[monthly["Type"] == etype]
            if not sub.empty:
                aum_by_month = sub.set_index("Month")["AUM"].reindex(months, fill_value=0)
                fig.add_trace(go.Bar(
                    name=etype,
                    x=month_labels,
                    y=aum_by_month.values,
                    marker=dict(color=color, line=dict(color=_CARD_BG, width=1)),
                    hovertemplate="<b>%{x}</b><br>AUM: $%{y:,.0f}<extra></extra>",
                ))

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=_CARD_BG,
            plot_bgcolor=_CARD_BG,
            font=dict(color=_TEXT, family="Inter, sans-serif", size=12),
            barmode="group",
            bargap=0.25,
            height=300,
            margin=dict(t=30, b=10, l=10, r=10),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=_SUB, size=11), orientation="h", y=1.05),
            xaxis=dict(gridcolor=_GRID, zeroline=False),
            yaxis=dict(gridcolor=_GRID, zeroline=False, tickprefix="$"),
            title=dict(text="AUM Outflows by Month", font=dict(size=13, color=_TEXT), x=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Product timeline by vehicle ────────────────────────────────────────────
    if timeline_rows:
        tl_df_sorted = pd.DataFrame(timeline_rows).sort_values("Date")
        fig2 = go.Figure()
        color_map = {"Maturity": primary, "Autocall Obs.": secondary}
        for etype in tl_df_sorted["Type"].unique():
            sub = tl_df_sorted[tl_df_sorted["Type"] == etype]
            fig2.add_trace(go.Scatter(
                x=sub["Date"],
                y=sub["Vehiculo"],
                mode="markers",
                name=etype,
                marker=dict(
                    size=sub["AUM"].apply(lambda v: max(10, min(40, v / 80_000))),
                    color=color_map.get(etype, accent),
                    line=dict(color=_CARD_BG, width=1),
                    opacity=0.85,
                ),
                customdata=list(zip(sub["Product"], sub["AUM"])),
                hovertemplate="<b>%{customdata[0]}</b><br>%{x|%d %b %Y}<br>AUM: $%{customdata[1]:,.0f}<extra></extra>",
            ))
        n_vehicles = tl_df_sorted["Vehiculo"].nunique()
        fig2.update_layout(
            template="plotly_dark",
            paper_bgcolor=_CARD_BG,
            plot_bgcolor=_CARD_BG,
            font=dict(color=_TEXT, family="Inter, sans-serif", size=11),
            height=max(200, n_vehicles * 60 + 80),
            margin=dict(t=36, b=10, l=10, r=10),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=_SUB, size=11), orientation="h", y=1.08),
            xaxis=dict(gridcolor=_GRID, zeroline=False, title="", dtick="M1", tickformat="%b"),
            yaxis=dict(gridcolor=_GRID, zeroline=False, title="", automargin=True),
            title=dict(text="Product Timeline por Vehículo (bubble size = AUM)", font=dict(size=13, color=_TEXT), x=0),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Tables ─────────────────────────────────────────────────────────────────
    if event_type in ("Both", "Maturities") and not maturities.empty:
        st.markdown(f"### Maturities ({len(maturities)})")
        vcto_display = maturities[[
            "nombre_producto", "status", "vehiculo", "monto_total",
            "_fecha_vcto", "days_to_maturity", "underlying_1", "underlying_2",
            "rendimiento_total", "contraparte",
        ]].rename(columns={
            "nombre_producto": "Product",
            "status": "Status",
            "vehiculo": "Vehicle",
            "monto_total": "AUM (USD)",
            "_fecha_vcto": "Maturity Date",
            "days_to_maturity": "Days Left",
            "underlying_1": "U1",
            "underlying_2": "U2",
            "rendimiento_total": "Return",
            "contraparte": "Counterparty",
        }).copy()
        vcto_display["AUM (USD)"] = vcto_display["AUM (USD)"].apply(
            lambda x: f"${x:,.0f}" if pd.notna(x) else ""
        )
        vcto_display["Return"] = vcto_display["Return"].apply(
            lambda x: f"{x*100:.2f}%" if pd.notna(x) and x != 0 else ""
        )
        st.dataframe(vcto_display, use_container_width=True, hide_index=True)

    if event_type in ("Both", "Autocalls") and not autocalls.empty:
        st.markdown(f"### Upcoming Autocall Observations ({len(autocalls)})")
        ac_display = autocalls[[
            "nombre_producto", "status", "vehiculo", "monto_total",
            "autocall_date", "days_to_autocall",
            "underlying_1", "underlying_2", "trigger_autocall", "contraparte",
        ]].rename(columns={
            "nombre_producto": "Product",
            "status": "Status",
            "vehiculo": "Vehicle",
            "monto_total": "AUM (USD)",
            "autocall_date": "Autocall Date",
            "days_to_autocall": "Days Left",
            "underlying_1": "U1",
            "underlying_2": "U2",
            "trigger_autocall": "Trigger",
            "contraparte": "Counterparty",
        }).copy()
        ac_display["AUM (USD)"] = ac_display["AUM (USD)"].apply(
            lambda x: f"${x:,.0f}" if pd.notna(x) else ""
        )
        ac_display["Trigger"] = ac_display["Trigger"].apply(
            lambda x: f"{x*100:.0f}%" if pd.notna(x) and x != 0 else ""
        )
        st.dataframe(ac_display, use_container_width=True, hide_index=True)
