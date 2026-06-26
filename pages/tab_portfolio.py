import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from backend.database import get_all_products, update_spots, save_aum_snapshot, get_aum_history
from backend.market_data import refresh_product_spots
import backend.config as cfg

_DARK_BG = "#0e1117"
_CARD_BG = "#1c1c2e"
_GRID = "#2d2d4e"
_TEXT = "#f0f2f6"
_SUB = "#a0aec0"


def _rgba(hex_color: str, alpha: float = 1.0) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def fmt_usd(val):
    if pd.isna(val) or val == 0:
        return "$0"
    if abs(val) >= 1_000_000:
        return f"${val/1_000_000:.1f}M"
    if abs(val) >= 1_000:
        return f"${val/1_000:.0f}K"
    return f"${val:,.0f}"


def _dark_layout(**kwargs) -> dict:
    base = dict(
        template="plotly_dark",
        paper_bgcolor=_CARD_BG,
        plot_bgcolor=_CARD_BG,
        font=dict(color=_TEXT, family="Inter, sans-serif", size=12),
        margin=dict(t=30, b=10, l=10, r=10),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=_SUB, size=11),
        ),
    )
    base.update(kwargs)
    return base


def render():
    palette = cfg.color_sequence()
    primary = palette[0]
    secondary = palette[1]

    st.subheader("Portfolio Overview")

    df = get_all_products()
    if df.empty:
        st.warning("No products found. Load products first.")
        return

    all_statuses = sorted(df["status"].dropna().unique().tolist())
    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    with col_f1:
        selected_statuses = st.multiselect(
            "Filter by Status",
            options=all_statuses,
            default=[s for s in ["VIGENTE", "POR EJECUTAR"] if s in all_statuses],
        )
    with col_f2:
        selected_vehicle = st.multiselect(
            "Filter by Vehicle",
            options=sorted(df["vehiculo"].dropna().unique().tolist()),
        )
    with col_f3:
        if st.button("Refresh Prices", use_container_width=True, type="primary"):
            with st.spinner("Fetching live prices..."):
                updates = refresh_product_spots(df)
                update_spots(updates)
                save_aum_snapshot()
                st.success(f"Updated {len(updates)} products")
                st.rerun()

    filtered = df.copy()
    if selected_statuses:
        filtered = filtered[filtered["status"].isin(selected_statuses)]
    if selected_vehicle:
        filtered = filtered[filtered["vehiculo"].isin(selected_vehicle)]

    # Active = only still-running products (AUTOCALL/VENCIDO are past events)
    active = filtered[filtered["status"].isin(["VIGENTE", "POR EJECUTAR"])]

    # ── KPI row ────────────────────────────────────────────────────────────────
    st.markdown("---")
    k1, k2, k3, k4, k5 = st.columns(5)
    total_aum = active["monto_total"].sum()
    k1.metric("Total AUM", fmt_usd(total_aum))
    k2.metric("Active Products", len(active))
    k3.metric("Pending Execution", len(active[active["status"] == "POR EJECUTAR"]))
    k4.metric("Already Autocalled", len(filtered[filtered["status"] == "AUTOCALL"]))
    k5.metric("Maturing ≤30d", len(
        active[pd.to_datetime(active["fecha_vencimiento"], dayfirst=True, errors="coerce") <=
               pd.Timestamp.now() + pd.Timedelta(days=30)]
    ))

    st.markdown("---")

    def _donut(labels, values, title):
        total = sum(values)
        fig = go.Figure(go.Pie(
            labels=labels, values=values,
            hole=0.60,
            marker=dict(
                colors=(palette * 4)[:len(labels)],
                line=dict(color=_CARD_BG, width=3),
            ),
            textinfo="label+percent",
            textfont=dict(size=11, color=_TEXT),
            hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>",
            direction="clockwise", sort=True,
        ))
        fig.update_layout(**_dark_layout(
            height=340,
            margin=dict(t=36, b=10, l=10, r=10),
            title=dict(text=title, font=dict(size=13, color=_TEXT), x=0, pad=dict(l=0)),
            annotations=[dict(
                text=fmt_usd(total),
                x=0.5, y=0.5,
                font=dict(size=18, color=_TEXT, family="Inter, sans-serif"),
                showarrow=False,
            )],
        ))
        return fig

    def _bar_h(y_vals, x_vals, title):
        colors = (palette * 4)[:len(y_vals)]
        fig = go.Figure(go.Bar(
            x=x_vals, y=y_vals,
            orientation="h",
            marker=dict(color=colors, line=dict(color=_CARD_BG, width=1)),
            text=[fmt_usd(v) for v in x_vals],
            textposition="outside",
            textfont=dict(color=_TEXT, size=11),
            hovertemplate="<b>%{y}</b><br>$%{x:,.0f}<extra></extra>",
        ))
        fig.update_layout(**_dark_layout(
            height=max(300, len(y_vals) * 44 + 60),
            margin=dict(t=36, b=10, l=10, r=80),
            title=dict(text=title, font=dict(size=13, color=_TEXT), x=0, pad=dict(l=0)),
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(gridcolor=_GRID, zeroline=False, autorange="reversed",
                       tickfont=dict(size=12)),
            bargap=0.28,
        ))
        return fig

    # ── Row 1: Status donut | Country donut ───────────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        status_df = (
            filtered.groupby("status")["monto_total"].sum().reset_index()
        )
        status_df["monto_total"] = pd.to_numeric(status_df["monto_total"], errors="coerce").fillna(0)
        status_df = status_df[status_df["monto_total"] > 0]
        if not status_df.empty:
            st.plotly_chart(
                _donut(status_df["status"].tolist(), status_df["monto_total"].tolist(),
                       "AUM por Status"),
                use_container_width=True,
            )

    with c2:
        country_data = {
            "Peru":     pd.to_numeric(active.get("monto_peru",     pd.Series(dtype=float)), errors="coerce").sum(),
            "Chile":    pd.to_numeric(active.get("monto_chile",    pd.Series(dtype=float)), errors="coerce").sum(),
            "Colombia": pd.to_numeric(active.get("monto_colombia", pd.Series(dtype=float)), errors="coerce").sum(),
            "USA":      pd.to_numeric(active.get("monto_usa",      pd.Series(dtype=float)), errors="coerce").sum(),
        }
        country_df = pd.DataFrame(
            [(k, v) for k, v in country_data.items() if v > 0],
            columns=["Country", "AUM"],
        ).sort_values("AUM", ascending=False)
        if not country_df.empty:
            st.plotly_chart(
                _donut(country_df["Country"].tolist(), country_df["AUM"].tolist(),
                       "AUM por País"),
                use_container_width=True,
            )

    # ── Row 2: Vehicle bar | Segment bar ──────────────────────────────────────
    c3, c4 = st.columns(2)

    with c3:
        veh_df = (
            active.groupby("vehiculo")["monto_total"].sum().reset_index()
        )
        veh_df["monto_total"] = pd.to_numeric(veh_df["monto_total"], errors="coerce").fillna(0)
        veh_df = veh_df[veh_df["monto_total"] > 0].sort_values("monto_total")
        if not veh_df.empty:
            st.plotly_chart(
                _bar_h(veh_df["vehiculo"].tolist(), veh_df["monto_total"].tolist(),
                       "AUM por Vehículo"),
                use_container_width=True,
            )

    with c4:
        segment_cols = {
            "BP Peru": "monto_bp_peru", "BP Chile": "monto_bp_chile",
            "BP Colombia": "monto_bp_colombia", "BP US": "monto_bp_us",
            "RIA": "monto_ria", "W9": "monto_w9",
            "Enalta": "monto_enalta", "BEX": "monto_bex",
            "Consumo": "monto_consumo", "Jurídicos": "monto_juridicos",
            "MFO": "monto_mfo", "TYBA": "monto_tyba",
        }
        seg_data = {
            k: pd.to_numeric(active[v], errors="coerce").sum()
            for k, v in segment_cols.items() if v in active.columns
        }
        seg_df = pd.DataFrame(
            [(k, v) for k, v in seg_data.items() if v > 0],
            columns=["Segment", "AUM"],
        ).sort_values("AUM")
        if not seg_df.empty:
            st.plotly_chart(
                _bar_h(seg_df["Segment"].tolist(), seg_df["AUM"].tolist(),
                       "AUM por Segmento"),
                use_container_width=True,
            )

    # ── AUM Historical Evolution ────────────────────────────────────────────────
    history = get_aum_history()
    if not history.empty and len(history) > 1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=history["fecha"],
            y=history["monto_total"],
            mode="lines+markers",
            name="Total AUM",
            line=dict(color=primary, width=2.5),
            marker=dict(size=6, color=primary, line=dict(color=_CARD_BG, width=2)),
            fill="tozeroy",
            fillcolor=_rgba(primary, 0.12),
            hovertemplate="%{x|%d %b %Y}<br><b>$%{y:,.0f}</b><extra></extra>",
        ))
        fig.update_layout(**_dark_layout(
            height=240,
            margin=dict(t=36, b=10, l=10, r=10),
            title=dict(text="Evolución AUM", font=dict(size=13, color=_TEXT), x=0),
            xaxis=dict(gridcolor=_GRID, zeroline=False, showline=False,
                       tickfont=dict(size=11)),
            yaxis=dict(gridcolor=_GRID, zeroline=False, showline=False,
                       tickprefix="$", tickfont=dict(size=11)),
        ))
        st.plotly_chart(fig, use_container_width=True)

    # ── Product table ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**Product List**")

    display_cols = {
        "nombre_producto": "Product Name",
        "tipo_estructura": "Category",
        "status": "Status",
        "vehiculo": "Vehicle",
        "monto_total": "Total AUM",
        "moneda": "Ccy",
        "underlying_1": "U1",
        "underlying_2": "U2",
        "spot_1": "Spot 1",
        "spot_2": "Spot 2",
        "rendimiento_total": "Return",
        "fecha_vencimiento": "Maturity",
        "proximo_autocall": "Next Autocall",
        "plazo_remanente_dias": "Days Left",
        "contraparte": "Counterparty",
        "perfil": "Profile",
    }

    available = {k: v for k, v in display_cols.items() if k in filtered.columns}
    tbl = filtered[list(available.keys())].rename(columns=available).copy()
    tbl["Total AUM"] = pd.to_numeric(tbl["Total AUM"], errors="coerce").apply(
        lambda x: fmt_usd(x) if pd.notna(x) else ""
    )
    if "Return" in tbl.columns:
        tbl["Return"] = pd.to_numeric(tbl["Return"], errors="coerce").apply(
            lambda x: f"{x*100:.2f}%" if pd.notna(x) and x != 0 else ""
        )

    st.dataframe(tbl, use_container_width=True, height=420, hide_index=True)
