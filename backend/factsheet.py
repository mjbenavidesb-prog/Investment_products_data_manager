"""
Factsheet PDF generator — portrait A4, matches Credicorp Capital template layout.

Layout (top to bottom):
  1. Header bar (colored) with badge label + company name
  2. Section label "DETALLE DEL PRODUCTO"
  3. Title: "AUTOCALL / VENCIMIENTO / EJECUTADO – Product Name"
  4. Narrative paragraph
  5. Two columns: CARACTERÍSTICAS GENERALES (table) | DESEMPEÑO DEL PEOR SUBYACENTE (chart)
  6. Full-width summary results table
  7. Section label "EVOLUCIÓN DEL PRODUCTO"
  8. Subyacente info + product return (right-aligned, colored)
  9. Two columns: coupon payment table | evolution chart (worst-of normalized)
  10. Footer note
"""

import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime, date, timedelta

try:
    import yfinance as yf
    YF_OK = True
except ImportError:
    YF_OK = False

from backend.market_data import resolve_ticker

# ── Palette ────────────────────────────────────────────────────────────────────
_WHITE   = "#FFFFFF"
_LIGHT   = "#F5F5F5"
_GRAY    = "#D1D5DB"
_DARK    = "#111827"
_SUBTEXT = "#6B7280"
_LINE_COLORS = ["#1A1A2E", "#DC2626", "#9CA3AF", "#2563EB"]   # dark navy, red, gray, blue

# ── Date helpers ───────────────────────────────────────────────────────────────
_MONTHS_ES = ["Ene","Feb","Mar","Abr","May","Jun",
               "Jul","Ago","Set","Oct","Nov","Dic"]

def _parse_date(s) -> date | None:
    if s is None:
        return None
    try:
        if isinstance(s, (date, datetime)):
            return s if isinstance(s, date) else s.date()
    except Exception:
        pass
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%b-%y", "%d-%b-%Y",
                "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(s).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _fmt_date(d) -> str:
    d = _parse_date(d)
    if not d:
        return "—"
    return f"{d.day:02d}-{_MONTHS_ES[d.month-1]}-{str(d.year)[2:]}"


def _safe_float(v, default=None):
    try:
        f = float(v)
        return default if (f != f) else f   # NaN → default
    except (TypeError, ValueError):
        return default


def _pct(v, decimals=2):
    f = _safe_float(v)
    if f is None:
        return "—"
    if abs(f) <= 1.5:
        f *= 100
    return f"{f:.{decimals}f}%"


def _hex(c: str) -> str:
    if c and c.startswith("#") and len(c) >= 7:
        return c[:7]
    return "#CC2200"


# ── yfinance price history ─────────────────────────────────────────────────────

def _fetch_prices(tickers: list[str], start: date, end: date) -> pd.DataFrame:
    """Return DataFrame of normalized prices (100 = start date) per ticker."""
    if not YF_OK or not tickers or not start:
        return pd.DataFrame()
    yf_map   = {t: resolve_ticker(t) for t in tickers if resolve_ticker(t)}
    inv_map  = {v: k for k, v in yf_map.items()}
    yf_syms  = list(yf_map.values())
    s_str    = str(start - timedelta(days=5))
    e_str    = str((end or date.today()) + timedelta(days=2))
    try:
        if len(yf_syms) == 1:
            raw = yf.download(yf_syms[0], start=s_str, end=e_str,
                              auto_adjust=True, progress=False)
            if raw.empty:
                return pd.DataFrame()
            closes = raw[["Close"]]
            closes.columns = yf_syms
        else:
            raw = yf.download(yf_syms, start=s_str, end=e_str,
                              auto_adjust=True, progress=False)
            if raw.empty:
                return pd.DataFrame()
            closes = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw

        closes.index = pd.to_datetime(closes.index).tz_localize(None)
        closes = closes[closes.index >= pd.Timestamp(start)]
        if closes.empty:
            return pd.DataFrame()

        norm = closes / closes.iloc[0] * 100
        return norm.rename(columns=inv_map)
    except Exception:
        return pd.DataFrame()


def _worst_of(df: pd.DataFrame) -> pd.Series:
    """Return the worst-performing underlying at each date."""
    if df.empty:
        return pd.Series(dtype=float)
    return df.min(axis=1)


# ── Drawing primitives ─────────────────────────────────────────────────────────

def _filled_row(ax, y, h, color):
    ax.add_patch(Rectangle((0, y), 1, h, transform=ax.transAxes,
                            facecolor=color, edgecolor="none", zorder=0, clip_on=False))


def _header_bar(fig, left, bottom, width, height, bg, label, company, badge_right):
    ax = fig.add_axes([left, bottom, width, height])
    ax.set_facecolor(_hex(bg))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.008, 0.5, label, color=_WHITE, fontsize=8.5, fontweight="bold",
            va="center", ha="left")
    ax.text(0.99, 0.5, company, color=_WHITE, fontsize=7, va="center",
            ha="right", alpha=0.8)


def _section_bar(fig, left, bottom, width, height, bg, label):
    ax = fig.add_axes([left, bottom, width, height])
    ax.set_facecolor(_hex(bg))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.008, 0.5, label, color=_WHITE, fontsize=7, fontweight="bold",
            va="center")


def _draw_char_table(ax, rows: list[tuple], primary: str):
    """Two-column key-value table with alternating rows."""
    ax.axis("off")
    n = len(rows)
    if n == 0:
        return
    rh = 1.0 / n
    for i, (k, v) in enumerate(rows):
        y = 1 - (i + 1) * rh
        bg = _LIGHT if i % 2 == 0 else _WHITE
        ax.add_patch(Rectangle((0, y), 1, rh, facecolor=bg,
                                edgecolor=_GRAY, linewidth=0.25))
        ax.text(0.03, y + rh * 0.5, str(k), fontsize=6.5, fontweight="bold",
                va="center", color=_DARK)
        ax.text(0.97, y + rh * 0.5, str(v), fontsize=6.5, va="center",
                ha="right", color=_DARK)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)


def _draw_perf_chart(ax, df: pd.DataFrame, barrier: float | None, primary: str, end_date=None):
    """Line chart of normalized prices with barrier dashed line."""
    if df.empty:
        ax.text(0.5, 0.5, "No price data available", ha="center", va="center",
                transform=ax.transAxes, color=_SUBTEXT, fontsize=8)
        ax.set_facecolor(_WHITE)
        ax.axis("off")
        return

    for i, col in enumerate(df.columns):
        ax.plot(df.index, df[col], color=_LINE_COLORS[i % len(_LINE_COLORS)],
                linewidth=1.3, label=col)

    if barrier is not None:
        b_pct = barrier * 100 if barrier <= 1 else barrier
        ax.axhline(y=b_pct, color="#DC2626", linestyle="--",
                   linewidth=1.0, alpha=0.85)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, fontsize=6, ha="right")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    ax.tick_params(axis="y", labelsize=6.5)
    ax.grid(axis="y", linestyle=":", linewidth=0.5, alpha=0.4, color=_GRAY)
    ax.set_facecolor(_WHITE)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(_GRAY)

    if len(df.columns) > 1:
        handles = [Line2D([0], [0], color=_LINE_COLORS[i % len(_LINE_COLORS)],
                          linewidth=1.2, label=c)
                   for i, c in enumerate(df.columns)]
        ax.legend(handles=handles, fontsize=5.5, loc="upper left",
                  framealpha=0.8, edgecolor=_GRAY)


def _draw_summary_table(ax, headers: list, values: list, primary: str):
    """Full-width multi-column results summary."""
    ax.axis("off")
    n = len(headers)
    if n == 0:
        return
    cw = 1.0 / n

    # header row
    for i, h in enumerate(headers):
        x = i * cw
        ax.add_patch(Rectangle((x, 0.5), cw, 0.5, facecolor=_hex(primary),
                                edgecolor=_WHITE, linewidth=0.5))
        ax.text(x + cw / 2, 0.75, h, fontsize=5.5, fontweight="bold",
                color=_WHITE, ha="center", va="center")

    # values row
    for i, v in enumerate(values):
        x = i * cw
        ax.add_patch(Rectangle((x, 0), cw, 0.5, facecolor=_LIGHT,
                                edgecolor=_WHITE, linewidth=0.5))
        ax.text(x + cw / 2, 0.25, str(v), fontsize=5.5, color=_DARK,
                ha="center", va="center")

    ax.set_xlim(0, 1); ax.set_ylim(0, 1)


def _draw_coupon_table(ax, dates: list, amounts: list, total: float):
    """Numbered coupon payment schedule."""
    ax.axis("off")
    headers = ["N° de Pago", "Fecha de Pago", "Cupón"]
    col_x   = [0.12, 0.52, 0.88]

    n_rows  = len(dates) + 2   # header + data + total
    rh      = 1.0 / n_rows

    # header row
    y_hdr = 1 - rh
    ax.add_patch(Rectangle((0, y_hdr), 1, rh, facecolor=_GRAY,
                            edgecolor=_WHITE, linewidth=0.3))
    for cx, h in zip(col_x, headers):
        ax.text(cx, y_hdr + rh * 0.5, h, fontsize=6, fontweight="bold",
                color=_DARK, ha="center", va="center")

    # data rows
    for i, (d, amt) in enumerate(zip(dates, amounts)):
        y = 1 - (i + 2) * rh
        bg = _LIGHT if i % 2 == 0 else _WHITE
        ax.add_patch(Rectangle((0, y), 1, rh, facecolor=bg,
                                edgecolor=_WHITE, linewidth=0.25))
        for cx, val in zip(col_x, [str(i + 1), _fmt_date(d), f"{amt:.3f}%"]):
            ax.text(cx, y + rh * 0.5, val, fontsize=6,
                    color=_DARK, ha="center", va="center")

    # total row
    y_tot = 1 - (len(dates) + 2) * rh
    ax.add_patch(Rectangle((0, y_tot), 1, rh, facecolor="#E5E7EB",
                            edgecolor=_WHITE, linewidth=0.3))
    ax.text(col_x[1], y_tot + rh * 0.5, "Total pagado", fontsize=6.5,
            fontweight="bold", color=_DARK, ha="center", va="center")
    ax.text(col_x[2], y_tot + rh * 0.5, f"{total:.3f}%", fontsize=6.5,
            fontweight="bold", color=_DARK, ha="center", va="center")

    ax.set_xlim(0, 1); ax.set_ylim(0, 1)


# ── Main entry point ───────────────────────────────────────────────────────────

def generate_factsheet_pdf(product: dict,
                           event_type: str = "Ejecutado",
                           company_name: str = "My Company",
                           primary: str = "#CC2200") -> BytesIO:
    """
    Generate portrait A4 PDF factsheet.
    event_type: "Autocall" | "Vencimiento" | "Ejecutado"  (chosen by the user in the UI)
    """
    px    = _hex(primary)
    label = event_type   # e.g. "Autocall"

    # ── Pull fields ────────────────────────────────────────────────────────────
    nombre   = str(product.get("nombre_producto") or "Structured Product")
    moneda   = str(product.get("moneda") or "USD")
    cpty     = str(product.get("contraparte") or "—")
    perfil   = str(product.get("perfil") or "—")
    isin     = str(product.get("isin") or "—")
    plazo    = _safe_float(product.get("plazo_meses"))
    cc       = _safe_float(product.get("cupon_contingente"))   # decimal
    cf       = _safe_float(product.get("cupon_fijo"))
    bk       = _safe_float(product.get("barrera_capital"))     # decimal KI level
    trig     = _safe_float(product.get("trigger_autocall"))
    gm       = product.get("ganancia_maxima")
    cap      = _safe_float(product.get("cap"))
    fpart    = _safe_float(product.get("factor_participacion"))
    rend     = _safe_float(product.get("rendimiento_total"))
    asset_cl = str(product.get("asset_class") or "Renta Variable")
    fmt_sub  = str(product.get("formato_subyacente") or "Worst of")

    # underlyings
    unds   = [product.get(f"underlying_{i}") for i in range(1, 5)]
    unds   = [str(u).strip() for u in unds if u and str(u).strip() not in ("", "nan", "None")]
    strikes = [_safe_float(product.get(f"strike_{i}")) for i in range(1, len(unds) + 1)]
    spots   = [_safe_float(product.get(f"spot_{i}"))   for i in range(1, len(unds) + 1)]

    # dates
    d_inicio   = _parse_date(product.get("fecha_inicio") or product.get("fecha_strike"))
    d_obs_fin  = _parse_date(product.get("fecha_obs_final"))
    d_vcto     = _parse_date(product.get("fecha_vencimiento"))
    end_date   = d_obs_fin or d_vcto or date.today()

    # autocall dates (= coupon observation/payment dates)
    ac_dates = [_parse_date(product.get(f"fecha_autocall_{i}")) for i in range(1, 11)]
    ac_dates = [d for d in ac_dates if d]

    # For Autocall factsheet: last past observation date = when the product was called
    actual_ac_date = None
    if label == "Autocall" and ac_dates:
        past = [d for d in ac_dates if d <= date.today()]
        actual_ac_date = past[-1] if past else ac_dates[0]
    chart_end = actual_ac_date or end_date

    # ── Barrier display ────────────────────────────────────────────────────────
    # barrera_capital stored as decimal downside buffer (0.25 = 25% protection,
    # meaning the KI level is at 75% of initial).
    barrier_for_chart = None   # normalized price level where KI triggers
    barrier_display   = "—"
    if bk is not None:
        bk_dec = bk if bk <= 1 else bk / 100          # downside buffer as decimal
        barrier_for_chart = (1 - bk_dec) * 100        # KI level as % (e.g. 75%)
        barrier_display = f"{bk_dec * 100:.0f}%"      # display downside buffer (e.g. "25%")

    # ── Cupon per period ───────────────────────────────────────────────────────
    coupon_dates = []
    coupon_amts  = []
    total_paid   = None

    if ac_dates:
        # infer frequency
        n_per_year = 4
        if len(ac_dates) >= 2:
            delta = (ac_dates[1] - ac_dates[0]).days
            if delta > 150:
                n_per_year = 2
            elif delta > 80:
                n_per_year = 4

        # coupon per period (annualised → period)
        cc_pct = 0.0
        if cc is not None:
            cc_pct = cc * 100 if cc <= 1 else cc
        elif cf is not None:
            cc_pct = cf * 100 if cf <= 1 else cf

        period_coupon = cc_pct / n_per_year if cc_pct else 0.0

        cutoff = actual_ac_date or chart_end
        for d in ac_dates:
            if d <= cutoff:
                coupon_dates.append(d)
                coupon_amts.append(period_coupon)

    if rend is not None:
        total_paid = rend * 100 if abs(rend) <= 1 else rend
    elif coupon_amts:
        total_paid = sum(coupon_amts)

    # ── Characteristics table ──────────────────────────────────────────────────
    sub_str  = " / ".join(unds) if unds else "—"
    sub_full = (
        f"Worst of: {', '.join(unds)}" if fmt_sub.lower().startswith("worst") and len(unds) > 1
        else sub_str
    )

    char_rows = [
        ("Tipo de producto",        "Opportunity" if bk else "Nota Estructurada"),
        ("Clasificación",           f"{asset_cl} – EEUU"),
        ("Subyacente",              sub_full),
        ("Moneda",                  "Dólares Americanos" if moneda == "USD" else moneda),
    ]
    if plazo:
        char_rows.append(("Plazo", f"{int(plazo)} meses"))
    if ac_dates:   # product has autocall observation schedule
        char_rows.append(("Período sin Autocall", "1er Trimestre"))
        char_rows.append(("Observación Autocall", "Trimestral"))
        char_rows.append(("Observación Cupón",    "Trimestral"))
    char_rows.append(("Riesgo del emisor",         cpty))
    if cc:
        cc_display = cc * 100 if cc <= 1 else cc
        char_rows.append(("Cupón anual contingente", f"{cc_display:.2f}%"))
    if gm:
        char_rows.append(("Ganancia Máxima", str(gm) if "%" in str(gm) else f"{gm}"))
    if barrier_display != "—":
        char_rows.append(("Barrera", barrier_display))

    # initial & final levels
    nivel_inicial_parts = []
    nivel_final_parts   = []
    for u, s, sp in zip(unds, strikes, spots):
        if s is not None:
            nivel_inicial_parts.append(f"{u}: {s:,.2f}")
        if sp is not None:
            nivel_final_parts.append(f"{u}: {sp:,.2f}")
    if nivel_inicial_parts:
        char_rows.append(("Nivel Inicial", " / ".join(nivel_inicial_parts)))
    if nivel_final_parts:
        char_rows.append(("Nivel Final",   " / ".join(nivel_final_parts)))
    if isin != "—":
        char_rows.append(("ISIN / Código", isin))

    # ── Narrative ──────────────────────────────────────────────────────────────
    cc_pct_str = f"{(cc*100 if cc and cc<=1 else cc or 0):.2f}%"
    # barrier_ki = KI level (e.g. 75%), barrier_display = downside buffer (e.g. 25%)
    bk_dec_narr = (bk if bk and bk <= 1 else (bk / 100 if bk else 0))
    barrier_ki  = f"{(1 - bk_dec_narr) * 100:.0f}%"   # KI level for narrative text

    if label == "Autocall":
        rend_str = f"{total_paid:.3f}%" if total_paid else "—"
        narrative = (
            f"El {nombre} fue llamado anticipadamente en la {_ordinal(len(coupon_dates))} "
            f"fecha de observación de autocall y alcanzó una rentabilidad de {rend_str} para el "
            f"período comprendido entre el {_fmt_date(d_inicio)} y el {_fmt_date(actual_ac_date)}. "
            f"El producto brindaba la posibilidad de obtener un cupón anual contingente de {cc_pct_str} "
            f"si en las observaciones el subyacente estaba por encima del {barrier_ki} de su nivel inicial.\n"
            f"Si a vencimiento el subyacente se encontraba por debajo del {barrier_ki} de su nivel inicial, "
            f"el inversionista habría estado expuesto en un 133% al rendimiento negativo del subyacente."
        )
    elif label == "Vencimiento":
        rend_str = f"{total_paid:.3f}%" if total_paid else "—"
        narrative = (
            f"El {nombre} fue llamado a su fecha de vencimiento y alcanzó una rentabilidad de {rend_str} "
            f"para el período comprendido entre el {_fmt_date(d_inicio)} y el {_fmt_date(d_vcto)}. "
            f"El producto brindaba la posibilidad de obtener un cupón anual contingente de {cc_pct_str} "
            f"si en las observaciones el subyacente estaba por encima del {barrier_ki} de su nivel inicial."
        )
    else:
        narrative = (
            f"El {nombre} brinda la posibilidad al inversionista de obtener un cupón contingente "
            f"de {cc_pct_str} por año, sujeto al comportamiento de los subyacentes seleccionados."
        )

    # ── Summary table ──────────────────────────────────────────────────────────
    if label == "Autocall":
        sum_hdrs = ["Producto", "Fecha Inicio", "Fecha\nVencimiento",
                    "Fecha de\nAutocall", "Pago cupón",
                    "Rend. subyacente", "Rend. del Producto", "Rend. Anualizado"]
        # compute annualized
        ann = "—"
        if total_paid and d_inicio and actual_ac_date:
            days = (actual_ac_date - d_inicio).days
            if days > 0:
                ann = f"{total_paid / (days / 365):.2f}%"
        sub_rets = [
            f"{u}: {((sp/s-1)*100 if s and sp and s > 0 else 0):+.2f}%"
            for u, s, sp in zip(unds, strikes, spots)
            if s and sp
        ]
        sub_ret_str = "\n".join(sub_rets) if sub_rets else "—"
        coupon_label = _fmt_date(coupon_dates[-1]) if coupon_dates else "—"
        sum_vals = [
            nombre[:28],
            _fmt_date(d_inicio),
            _fmt_date(d_vcto),
            _fmt_date(actual_ac_date),
            f"{coupon_amts[-1]:.3f}%" if coupon_amts else "—",
            sub_ret_str,
            f"{total_paid:.3f}%" if total_paid else "—",
            ann,
        ]
    elif label == "Vencimiento":
        sum_hdrs = ["Producto", "Fecha Inicio", "Fecha Obs.\nFinal",
                    "Fecha\nVencimiento", "Pago cupón",
                    "Rend. subyacente", "Rend. del Producto", "Rend. Anualizado"]
        ann = "—"
        if total_paid and d_inicio and (d_obs_fin or d_vcto):
            days = ((d_obs_fin or d_vcto) - d_inicio).days
            if days > 0:
                ann = f"{total_paid / (days / 365):.2f}%"
        sub_rets = [
            f"{u}: {((sp/s-1)*100 if s and sp and s > 0 else 0):+.2f}%"
            for u, s, sp in zip(unds, strikes, spots) if s and sp
        ]
        sum_vals = [
            nombre[:28],
            _fmt_date(d_inicio),
            _fmt_date(d_obs_fin),
            _fmt_date(d_vcto),
            f"{coupon_amts[-1]:.3f}%" if coupon_amts else "—",
            "\n".join(sub_rets) if sub_rets else "—",
            f"{total_paid:.3f}%" if total_paid else "—",
            ann,
        ]
    else:  # Ejecutado
        sum_hdrs = ["Producto", "Fecha Inicio", "Fecha Obs.\nFinal",
                    "Fecha\nVencimiento", "Ganancia Máx.", "ISIN"]
        sum_vals = [nombre[:28], _fmt_date(d_inicio), _fmt_date(d_obs_fin),
                    _fmt_date(d_vcto), str(gm) if gm else "—", isin]

    # ── Fetch price data ───────────────────────────────────────────────────────
    price_df = _fetch_prices(unds, d_inicio, chart_end) if d_inicio else pd.DataFrame()
    worst_df = _worst_of(price_df) if not price_df.empty else pd.Series(dtype=float)

    # ── Build figure (A4 portrait: 8.27 × 11.69 in) ──────────────────────────
    fig = plt.figure(figsize=(8.27, 11.69), facecolor=_WHITE, dpi=150)

    # Fixed row heights (inches from top):
    # 0.00–0.30  header bar
    # 0.30–0.55  section bar "DETALLE"
    # 0.55–0.85  title
    # 0.85–1.45  narrative text
    # 1.45–1.70  section bar "CARACTERÍSTICAS"
    # 1.70–5.40  two-column: table | chart  (3.70 in)
    # 5.40–6.00  summary table
    # 6.00–6.25  section bar "EVOLUCIÓN"
    # 6.25–6.55  sub-header (subyacente name + product return)
    # 6.55–9.75  two-column: coupon table | evolution chart (3.20 in)
    # 9.75–11.40 footer

    H = 11.69   # total figure height

    def _ax(bottom_in, top_in, left_pct=0.0, width_pct=1.0):
        """
        Create axes positioned by inches-from-top-of-page.
        bottom_in: distance from top of page to the BOTTOM edge of the region
        top_in:    distance from top of page to the TOP edge (smaller = higher)
        """
        b = 1 - bottom_in / H          # figure-coord of the bottom edge
        h = (bottom_in - top_in) / H   # height in figure coords
        return fig.add_axes([left_pct, b, width_pct, h])

    # 1. Header bar
    ax_hdr = _ax(0.30, 0.00)
    ax_hdr.set_facecolor(px)
    ax_hdr.axis("off")
    ax_hdr.set_xlim(0, 1); ax_hdr.set_ylim(0, 1)
    ax_hdr.text(0.01, 0.5, label.upper(), color=_WHITE,
                fontsize=9, fontweight="bold", va="center")
    ax_hdr.text(0.99, 0.5, company_name, color=_WHITE,
                fontsize=7, va="center", ha="right", alpha=0.85)

    # 2. Section bar "DETALLE"
    ax_det = _ax(0.55, 0.30)
    ax_det.set_facecolor(px)
    ax_det.axis("off")
    ax_det.set_xlim(0, 1); ax_det.set_ylim(0, 1)
    ax_det.text(0.01, 0.5, "DETALLE DEL PRODUCTO",
                color=_WHITE, fontsize=7.5, fontweight="bold", va="center")

    # 3. Title
    ax_ttl = _ax(0.85, 0.55, left_pct=0.01, width_pct=0.98)
    ax_ttl.axis("off")
    ax_ttl.set_xlim(0, 1); ax_ttl.set_ylim(0, 1)
    ax_ttl.text(0, 0.5, f"{label.upper()} — {nombre}",
                color=px, fontsize=11, fontweight="bold", va="center")

    # 4. Narrative
    ax_narr = _ax(1.45, 0.85, left_pct=0.01, width_pct=0.98)
    ax_narr.axis("off")
    ax_narr.set_xlim(0, 1); ax_narr.set_ylim(0, 1)
    wrapped = textwrap.fill(narrative, width=120)
    ax_narr.text(0, 1.0, wrapped, fontsize=6.8, va="top", color=_DARK,
                 multialignment="left", transform=ax_narr.transAxes)

    # 5. Section bar "CARACTERÍSTICAS | DESEMPEÑO"
    ax_csec = _ax(1.70, 1.45, left_pct=0.01, width_pct=0.45)
    ax_csec.set_facecolor(px)
    ax_csec.axis("off")
    ax_csec.set_xlim(0, 1); ax_csec.set_ylim(0, 1)
    ax_csec.text(0.02, 0.5, "CARACTERÍSTICAS GENERALES",
                 color=_WHITE, fontsize=6.5, fontweight="bold", va="center")

    ax_dsec = _ax(1.70, 1.45, left_pct=0.48, width_pct=0.51)
    ax_dsec.set_facecolor(px)
    ax_dsec.axis("off")
    ax_dsec.set_xlim(0, 1); ax_dsec.set_ylim(0, 1)
    ax_dsec.text(0.02, 0.5, "DESEMPEÑO DEL PEOR SUBYACENTE",
                 color=_WHITE, fontsize=6.5, fontweight="bold", va="center")

    # 6a. Characteristics table
    ax_ctbl = _ax(5.40, 1.70, left_pct=0.01, width_pct=0.45)
    _draw_char_table(ax_ctbl, char_rows, px)

    # 6b. Performance chart (all underlyings)
    ax_perf = _ax(5.40, 1.70, left_pct=0.48, width_pct=0.51)
    _draw_perf_chart(ax_perf, price_df, barrier_for_chart, px)

    # 7. Summary table
    ax_sum = _ax(6.00, 5.40, left_pct=0.01, width_pct=0.98)
    _draw_summary_table(ax_sum, sum_hdrs, sum_vals, px)

    # 8. Section bar "EVOLUCIÓN"
    ax_esec = _ax(6.25, 6.00)
    ax_esec.set_facecolor(px)
    ax_esec.axis("off")
    ax_esec.set_xlim(0, 1); ax_esec.set_ylim(0, 1)
    ax_esec.text(0.01, 0.5, "EVOLUCIÓN DEL PRODUCTO",
                 color=_WHITE, fontsize=7.5, fontweight="bold", va="center")

    # 9. Sub-header: subyacente name + product return
    ax_subhdr = _ax(6.55, 6.25, left_pct=0.01, width_pct=0.98)
    ax_subhdr.axis("off")
    ax_subhdr.set_xlim(0, 1); ax_subhdr.set_ylim(0, 1)
    ax_subhdr.text(0, 0.5,
                   f"Subyacente: {sub_full}",
                   fontsize=6.5, color=_DARK, va="center", fontweight="bold")
    if total_paid is not None:
        ax_subhdr.text(0.99, 0.7,
                       f"Rendimiento producto*: {total_paid:.3f}%",
                       fontsize=7, color=px, va="center", ha="right",
                       fontweight="bold")
        # worst-of return
        if unds and strikes and spots:
            wo_rets = [(sp / s - 1) * 100 if s and sp and s > 0 else None
                       for s, sp in zip(strikes, spots)]
            wo_rets_clean = [r for r in wo_rets if r is not None]
            if wo_rets_clean:
                worst_ret = min(wo_rets_clean)
                ax_subhdr.text(0.99, 0.3,
                               f"Rendimiento subyacente: {worst_ret:.2f}%",
                               fontsize=6.5, color=_SUBTEXT, va="center", ha="right")

    # 10a. Coupon table
    ax_cpn = _ax(9.75, 6.55, left_pct=0.01, width_pct=0.42)
    if coupon_dates:
        _draw_coupon_table(ax_cpn, coupon_dates, coupon_amts, total_paid or 0)
    else:
        ax_cpn.axis("off")
        ax_cpn.text(0.5, 0.5, "No coupon schedule\n(return at maturity)",
                    ha="center", va="center", fontsize=8, color=_SUBTEXT,
                    style="italic", transform=ax_cpn.transAxes)

    # 10b. Evolution chart (worst-of only)
    ax_evo = _ax(9.75, 6.55, left_pct=0.45, width_pct=0.54)
    if not worst_df.empty:
        _draw_perf_chart(ax_evo,
                         worst_df.rename("Worst-of").to_frame(),
                         barrier_for_chart, px)
    else:
        _draw_perf_chart(ax_evo, price_df, barrier_for_chart, px)

    # 11. Footer
    ax_foot = _ax(11.60, 9.75, left_pct=0.01, width_pct=0.98)
    ax_foot.axis("off")
    ax_foot.set_xlim(0, 1); ax_foot.set_ylim(0, 1)
    ax_foot.text(0, 0.98,
                 "*Rentabilidad que se obtendría si el producto venciese en cada día observado.",
                 fontsize=5, color=_SUBTEXT, va="top", style="italic")
    disclaimer = (
        f"La rentabilidad esperada no incluye el efecto del impuesto a la renta. "
        f"El riesgo y rendimiento de los valores reflejan el riesgo y rendimiento de los activos subyacentes. "
        f"Emisor de la nota: {cpty}. Generado por Structured Products Manager."
    )
    ax_foot.text(0, 0.70, disclaimer, fontsize=5, color=_SUBTEXT, va="top", wrap=True)

    # ── Save to bytes ──────────────────────────────────────────────────────────
    buf = BytesIO()
    fig.savefig(buf, format="pdf", dpi=150, facecolor=_WHITE,
                bbox_inches=None)
    plt.close(fig)
    buf.seek(0)
    return buf


def _ordinal(n: int) -> str:
    ordinals = {1:"primera",2:"segunda",3:"tercera",4:"cuarta",5:"quinta",
                6:"sexta",7:"séptima",8:"octava",9:"novena",10:"décima"}
    return ordinals.get(n, f"{n}a")
