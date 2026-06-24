import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
from backend.database import get_all_products
from backend.excel_report import generate_excel_report
import backend.config as cfg

# ── Theme constants ────────────────────────────────────────────────────────────
_BG    = "#0e1117"
_CARD  = "#1c1c2e"
_GRID  = "#2d2d4e"
_TEXT  = "#f0f2f6"
_SUB   = "#a0aec0"


def _rgba(hex_color: str, alpha: float = 1.0) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _layout(height=340, **kwargs) -> dict:
    base = dict(
        template="plotly_dark",
        paper_bgcolor=_CARD,
        plot_bgcolor=_CARD,
        font=dict(color=_TEXT, family="Inter, sans-serif", size=12),
        margin=dict(t=24, b=40, l=10, r=10),
        height=height,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11, color=_SUB)),
    )
    base.update(kwargs)
    return base


def fmt_usd(val):
    if pd.isna(val) or val == 0:
        return "$0"
    if abs(val) >= 1_000_000:
        return f"${val/1_000_000:.2f}M"
    if abs(val) >= 1_000:
        return f"${val/1_000:.0f}K"
    return f"${val:,.0f}"




# ── Chart builders ─────────────────────────────────────────────────────────────

def _bar_h(df, x_col, y_col, primary, title=""):
    palette = cfg.color_sequence()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df[x_col],
        y=df[y_col],
        orientation="h",
        marker=dict(
            color=[palette[i % len(palette)] for i in range(len(df))],
            line=dict(color=_CARD, width=1),
        ),
        text=df[x_col].apply(fmt_usd),
        textposition="outside",
        textfont=dict(color=_TEXT, size=11),
        hovertemplate="<b>%{y}</b><br>%{x:$,.0f}<extra></extra>",
    ))
    fig.update_layout(
        **_layout(height=max(280, len(df) * 42 + 60)),
        title=dict(text=title, font=dict(size=13, color=_TEXT), x=0),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(gridcolor=_GRID, zeroline=False, autorange="reversed",
                   tickfont=dict(size=12)),
        bargap=0.25,
    )
    return fig


def _donut(df, values_col, names_col, title=""):
    palette = cfg.color_sequence() * 4
    total   = df[values_col].sum()
    fig = go.Figure(go.Pie(
        labels=df[names_col],
        values=df[values_col],
        hole=0.58,
        marker=dict(colors=palette[:len(df)], line=dict(color=_CARD, width=2)),
        textinfo="label+percent",
        textfont=dict(size=11, color=_TEXT),
        hovertemplate="<b>%{label}</b><br>%{value:$,.0f}<br>%{percent}<extra></extra>",
        direction="clockwise",
        sort=True,
    ))
    fig.update_layout(
        **_layout(height=320),
        title=dict(text=title, font=dict(size=13, color=_TEXT), x=0),
        annotations=[dict(
            text=fmt_usd(total),
            x=0.5, y=0.5,
            font=dict(size=17, color=_TEXT, family="Inter"),
            showarrow=False,
        )],
    )
    return fig


def _waterfall(df, cat_col, val_col, title=""):
    fig = go.Figure(go.Waterfall(
        x=df[cat_col],
        y=df[val_col],
        measure=["relative"] * len(df),
        text=df[val_col].apply(fmt_usd),
        textposition="outside",
        connector=dict(line=dict(color=_GRID, width=1)),
        increasing=dict(marker_color=cfg.get("primary_color") or "#2563EB"),
        decreasing=dict(marker_color=cfg.get("secondary_color") or "#DC2626"),
    ))
    fig.update_layout(
        **_layout(height=320),
        title=dict(text=title, font=dict(size=13, color=_TEXT), x=0),
        xaxis=dict(gridcolor=_GRID, tickfont=dict(size=11)),
        yaxis=dict(gridcolor=_GRID, zeroline=False, showticklabels=False),
    )
    return fig


# ── Filter helpers ─────────────────────────────────────────────────────────────

_COUNTRY_COLS = {
    "Peru":     "monto_peru",
    "Chile":    "monto_chile",
    "Colombia": "monto_colombia",
    "USA":      "monto_usa",
}

_SEGMENT_COLS = {
    "BP Peru":    "monto_bp_peru",
    "BP Chile":   "monto_bp_chile",
    "BP Colombia":"monto_bp_colombia",
    "BP US":      "monto_bp_us",
    "RIA":        "monto_ria",
    "W9":         "monto_w9",
    "Enalta":     "monto_enalta",
    "BEX":        "monto_bex",
    "Consumo":    "monto_consumo",
    "Jurídicos":  "monto_juridicos",
    "MFO":        "monto_mfo",
    "TYBA":       "monto_tyba",
}

_FILTER_OPTIONS = {
    "País":         list(_COUNTRY_COLS.keys()),
    "Status":       None,   # derived from data
    "Vehículo":     None,
    "Asset Class":  None,
    "Contraparte":  None,
    "Perfil":       None,
}

_VIEW_OPTIONS = [
    "AUM por País",
    "AUM por Segmento",
    "AUM por Asset Class",
    "AUM por Vehículo",
    "AUM por Estrategia",
    "AUM por Perfil de riesgo",
    "AUM por Contraparte",
    "Portfolio Completo",
]


def _apply_filter(df: pd.DataFrame, filter_by: str, selected) -> pd.DataFrame:
    if not selected or filter_by == "Todos":
        return df.copy()
    if filter_by == "País":
        mask = pd.Series(False, index=df.index)
        for country in selected:
            col = _COUNTRY_COLS.get(country)
            if col and col in df.columns:
                mask |= (pd.to_numeric(df[col], errors="coerce").fillna(0) > 0)
        return df[mask].copy()
    if filter_by == "Status":
        return df[df["status"].isin(selected)].copy()
    if filter_by == "Vehículo":
        return df[df["vehiculo"].isin(selected)].copy()
    if filter_by == "Asset Class":
        return df[df["asset_class"].isin(selected)].copy()
    if filter_by == "Contraparte":
        return df[df["contraparte"].isin(selected)].copy()
    if filter_by == "Perfil":
        return df[df["perfil"].isin(selected)].copy()
    return df.copy()


# ── View builders ──────────────────────────────────────────────────────────────

def _view_country(filtered, primary):
    data = {k: pd.to_numeric(filtered[v], errors="coerce").sum()
            for k, v in _COUNTRY_COLS.items() if v in filtered.columns}
    total = sum(data.values()) or 1
    report_df = pd.DataFrame([
        {"País": k, "AUM (USD)": v, "% del Total": round(v / total * 100, 2)}
        for k, v in data.items() if v > 0
    ])
    if report_df.empty:
        st.info("Sin datos para el filtro seleccionado.")
        return pd.DataFrame()
    report_df = report_df.sort_values("AUM (USD)", ascending=False)

    c1, c2 = st.columns([3, 2])
    with c1:
        st.plotly_chart(_donut(report_df, "AUM (USD)", "País", "AUM por País"),
                        use_container_width=True)
    with c2:
        st.dataframe(
            report_df.style.format({"AUM (USD)": "${:,.0f}", "% del Total": "{:.1f}%"}),
            use_container_width=True, hide_index=True, height=250,
        )
    return report_df


def _view_segment(filtered, primary):
    data = {k: pd.to_numeric(filtered[v], errors="coerce").sum()
            for k, v in _SEGMENT_COLS.items() if v in filtered.columns}
    total = sum(data.values()) or 1
    report_df = pd.DataFrame([
        {"Segmento": k, "AUM (USD)": v, "% del Total": round(v / total * 100, 2)}
        for k, v in data.items() if v > 0
    ])
    if report_df.empty:
        st.info("Sin datos de segmento para el filtro seleccionado.")
        return pd.DataFrame()
    report_df = report_df.sort_values("AUM (USD)", ascending=False)

    c1, c2 = st.columns([3, 2])
    with c1:
        st.plotly_chart(_bar_h(report_df, "AUM (USD)", "Segmento", primary, "AUM por Segmento"),
                        use_container_width=True)
    with c2:
        st.dataframe(
            report_df.style.format({"AUM (USD)": "${:,.0f}", "% del Total": "{:.1f}%"}),
            use_container_width=True, hide_index=True,
        )
    return report_df


def _view_by_col(filtered, col, label, primary, chart="bar"):
    if col not in filtered.columns:
        st.warning(f"Columna '{col}' no disponible.")
        return pd.DataFrame()
    grp = (
        filtered.groupby(col)["monto_total"]
        .sum()
        .reset_index()
        .rename(columns={col: label, "monto_total": "AUM (USD)"})
    )
    grp = grp[pd.to_numeric(grp["AUM (USD)"], errors="coerce") > 0].copy()
    grp["AUM (USD)"] = pd.to_numeric(grp["AUM (USD)"], errors="coerce")
    total = grp["AUM (USD)"].sum() or 1
    grp["% del Total"] = (grp["AUM (USD)"] / total * 100).round(2)
    grp = grp.sort_values("AUM (USD)", ascending=False)

    if grp.empty:
        st.info("Sin datos para el filtro seleccionado.")
        return pd.DataFrame()

    c1, c2 = st.columns([3, 2])
    with c1:
        if chart == "donut" or len(grp) <= 5:
            fig = _donut(grp, "AUM (USD)", label, f"AUM por {label}")
        else:
            fig = _bar_h(grp, "AUM (USD)", label, primary, f"AUM por {label}")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.dataframe(
            grp.style.format({"AUM (USD)": "${:,.0f}", "% del Total": "{:.1f}%"}),
            use_container_width=True, hide_index=True,
        )
    return grp


def _view_full(filtered):
    cols = [
        "nombre_producto", "tipo", "status", "vehiculo", "entidad",
        "monto_total", "monto_peru", "monto_chile", "monto_colombia", "monto_usa",
        "moneda", "asset_class", "perfil", "contraparte",
        "underlying_1", "underlying_2", "underlying_3",
        "fecha_inicio", "fecha_vencimiento",
        "cupon_contingente", "barrera_capital", "trigger_autocall",
        "rendimiento_total",
    ]
    available = [c for c in cols if c in filtered.columns]
    st.dataframe(filtered[available], use_container_width=True, height=480, hide_index=True)
    return filtered[available]


# ── Main render ────────────────────────────────────────────────────────────────

def render():
    primary   = cfg.get("primary_color")   or "#2563EB"
    secondary = cfg.get("secondary_color") or "#DC2626"

    st.subheader("Reports")

    df = get_all_products()
    if df.empty:
        st.warning("No products found.")
        return

    # Ensure numeric
    for col in ["monto_total", *_COUNTRY_COLS.values(), *_SEGMENT_COLS.values()]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # ── Status filter (always visible at top) ─────────────────────────────────
    st.markdown("#### Filtros")
    all_statuses = sorted(df["status"].dropna().unique().tolist())
    status_filter = st.multiselect(
        "Status",
        options=all_statuses,
        default=[s for s in ["VIGENTE", "POR EJECUTAR"] if s in all_statuses],
    )
    if status_filter:
        df = df[df["status"].isin(status_filter)].copy()

    c1, c2 = st.columns([2, 3])

    with c1:
        filter_by = st.selectbox(
            "Filtrar por",
            ["Todos", "País", "Status", "Vehículo", "Asset Class", "Contraparte", "Perfil"],
        )

    # Dynamic options for chosen filter dimension
    with c2:
        if filter_by == "Todos":
            selected_values = []
            st.caption("Mostrando todo el portfolio.")

        elif filter_by == "País":
            selected_values = st.multiselect(
                "Selecciona países",
                options=list(_COUNTRY_COLS.keys()),
                default=list(_COUNTRY_COLS.keys()),
            )

        elif filter_by == "Status":
            opts = sorted(df["status"].dropna().unique().tolist())
            selected_values = st.multiselect(
                "Selecciona status",
                options=opts,
                default=[s for s in ["VIGENTE", "POR EJECUTAR"] if s in opts],
            )

        elif filter_by == "Vehículo":
            opts = sorted(df["vehiculo"].dropna().unique().tolist())
            selected_values = st.multiselect("Selecciona vehículo", options=opts)

        elif filter_by == "Asset Class":
            opts = sorted(df["asset_class"].dropna().unique().tolist())
            selected_values = st.multiselect("Selecciona asset class", options=opts)

        elif filter_by == "Contraparte":
            opts = sorted(df["contraparte"].dropna().unique().tolist())
            selected_values = st.multiselect("Selecciona contraparte", options=opts)

        elif filter_by == "Perfil":
            opts = ["Muy Conservador", "Conservador", "Moderado", "Agresivo"]
            opts = [o for o in opts if o in df["perfil"].unique()] or \
                   sorted(df["perfil"].dropna().unique().tolist())
            selected_values = st.multiselect("Selecciona perfil", options=opts)

        else:
            selected_values = []

    filtered = _apply_filter(df, filter_by, selected_values)

    # ── KPI summary ───────────────────────────────────────────────────────────
    total_aum  = filtered["monto_total"].sum()
    n_products = len(filtered)
    st.markdown(
        f"<div style='padding:10px 0 4px 0;color:{_SUB};font-size:0.85rem'>"
        f"<b style='color:{_TEXT};font-size:1.1rem'>{fmt_usd(total_aum)}</b> AUM total &nbsp;·&nbsp; "
        f"<b style='color:{_TEXT}'>{n_products}</b> productos en el filtro"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ── Row 2: view selector ──────────────────────────────────────────────────
    view = st.selectbox("Ver", _VIEW_OPTIONS)

    st.markdown("")

    report_df = pd.DataFrame()

    if view == "AUM por País":
        report_df = _view_country(filtered, primary)

    elif view == "AUM por Segmento":
        report_df = _view_segment(filtered, primary)

    elif view == "AUM por Asset Class":
        report_df = _view_by_col(filtered, "asset_class", "Asset Class", primary, "donut")

    elif view == "AUM por Vehículo":
        report_df = _view_by_col(filtered, "vehiculo", "Vehículo", primary, "bar")

    elif view == "AUM por Estrategia":
        if "estrategia" in filtered.columns and filtered["estrategia"].notna().any():
            col = "estrategia"
        elif "tipo_estructura" in filtered.columns and filtered["tipo_estructura"].notna().any():
            col = "tipo_estructura"
        else:
            col = "tipo"
        report_df = _view_by_col(filtered, col, "Estrategia", primary, "donut")

    elif view == "AUM por Perfil de riesgo":
        report_df = _view_by_col(filtered, "perfil", "Perfil", primary, "bar")

    elif view == "AUM por Contraparte":
        report_df = _view_by_col(filtered, "contraparte", "Contraparte", primary, "bar")

    elif view == "Portfolio Completo":
        report_df = _view_full(filtered)

    # ── Download ──────────────────────────────────────────────────────────────
    st.markdown("---")
    filter_label = (
        f"{filter_by}: {', '.join(str(v) for v in selected_values)}"
        if selected_values and filter_by != "Todos"
        else ""
    )
    with st.spinner("Preparando Excel..."):
        try:
            excel_data = generate_excel_report(
                df=filtered,
                view=view,
                primary_hex=primary,
                secondary_hex=secondary,
                filter_label=filter_label,
            )
            st.download_button(
                label="Descargar Excel",
                data=excel_data,
                file_name=f"reporte_{view.lower().replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Error generando Excel: {e}")
            st.exception(e)
