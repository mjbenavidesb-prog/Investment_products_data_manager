"""
Factsheet generator for structured investment products.
Generates a PDF using matplotlib.
Supports 3 event types: Autocall, Vencimiento, Ejecutado.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch, Rectangle
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime, date, timedelta

try:
    import yfinance as yf
    YF_OK = True
except ImportError:
    YF_OK = False

from backend.market_data import TICKER_MAP, resolve_ticker


# ── Colours ────────────────────────────────────────────────────────────────────

_CHART_COLORS = ["#2563EB", "#DC2626", "#F59E0B", "#10B981"]
_LIGHT_GRAY = "#F3F4F6"
_MID_GRAY = "#D1D5DB"
_TEXT = "#111827"
_SUBTEXT = "#6B7280"
_WHITE = "#FFFFFF"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_date(s) -> date | None:
    if not s or (isinstance(s, float) and np.isnan(s)):
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%b-%y", "%d-%b-%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(s).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _pct(val, decimals=2):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    if abs(val) <= 1.5:
        val *= 100
    return f"{val:.{decimals}f}%"


def _fmt_date(d: date | None) -> str:
    if not d:
        return "—"
    months_es = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                 "Jul", "Ago", "Set", "Oct", "Nov", "Dic"]
    return f"{d.day:02d}-{months_es[d.month-1]}-{str(d.year)[2:]}"


def _hex(color: str):
    """Ensure color is a valid hex string, fallback to default."""
    if color and color.startswith("#") and len(color) in (7, 9):
        return color[:7]
    return "#2563EB"


def _add_header_bar(fig, text: str, primary: str, company_name: str):
    """Draw the top red/colored header bar with product type label."""
    ax = fig.add_axes([0, 0.957, 1, 0.043])
    ax.set_facecolor(_hex(primary))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.012, 0.45, text.upper(), fontsize=10, fontweight="bold",
            color=_WHITE, va="center", ha="left")
    ax.text(0.988, 0.45, company_name, fontsize=8, color=_WHITE,
            va="center", ha="right", alpha=0.85)


def _add_title(fig, title: str, primary: str, top: float):
    ax = fig.add_axes([0.012, top, 0.976, 0.052])
    ax.axis("off")
    ax.text(0, 0.5, title, fontsize=14, fontweight="bold",
            color=_hex(primary), va="center")


def _add_section_label(fig, label: str, primary: str, top: float):
    ax = fig.add_axes([0, top, 1, 0.026])
    ax.set_facecolor(_hex(primary))
    ax.axis("off")
    ax.text(0.012, 0.45, label, fontsize=8, fontweight="bold",
            color=_WHITE, va="center")


def _draw_table(ax, rows, col_widths=None, header_color="#2563EB"):
    """Draw a two-column key-value table on ax."""
    ax.axis("off")
    n = len(rows)
    if n == 0:
        return
    row_h = 1.0 / n
    for i, (k, v) in enumerate(rows):
        y = 1 - (i + 0.5) * row_h
        bg = _LIGHT_GRAY if i % 2 == 0 else _WHITE
        ax.add_patch(Rectangle((0, 1 - (i + 1) * row_h), 1, row_h,
                                facecolor=bg, edgecolor=_MID_GRAY, linewidth=0.3))
        ax.text(0.02, y, str(k), fontsize=7.5, fontweight="bold",
                va="center", color=_TEXT)
        ax.text(0.98, y, str(v), fontsize=7.5, va="center",
                ha="right", color=_TEXT)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)


def _performance_chart(ax, tickers, start_date, end_date, barrier_pct, primary):
    """Plot normalized performance chart."""
    if not YF_OK or not tickers or not start_date:
        ax.text(0.5, 0.5, "Price data unavailable", ha="center", va="center",
                transform=ax.transAxes, color=_SUBTEXT, fontsize=9)
        ax.axis("off")
        return

    end = end_date or date.today()
    start_str = str(start_date - timedelta(days=3))
    end_str = str(end + timedelta(days=1))

    yf_syms = [resolve_ticker(t) for t in tickers if resolve_ticker(t)]
    orig_map = {resolve_ticker(t): t for t in tickers if resolve_ticker(t)}

    try:
        if len(yf_syms) == 1:
            raw = yf.download(yf_syms[0], start=start_str, end=end_str,
                              auto_adjust=True, progress=False)
            if not raw.empty:
                closes = raw[["Close"]]
                closes.columns = yf_syms
        else:
            raw = yf.download(yf_syms, start=start_str, end=end_str,
                              auto_adjust=True, progress=False)
            closes = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw

        if raw.empty:
            raise ValueError("empty")

        # Align to start date
        closes.index = pd.to_datetime(closes.index).tz_localize(None)
        start_ts = pd.Timestamp(start_date)
        closes = closes[closes.index >= start_ts]
        if closes.empty:
            raise ValueError("empty after filter")

        normalized = closes / closes.iloc[0] * 100

        for i, sym in enumerate(yf_syms):
            if sym in normalized.columns:
                label = orig_map.get(sym, sym)
                color = _CHART_COLORS[i % len(_CHART_COLORS)]
                ax.plot(normalized.index, normalized[sym], label=label,
                        color=color, linewidth=1.5)

    except Exception:
        ax.text(0.5, 0.5, "Chart data not available", ha="center", va="center",
                transform=ax.transAxes, color=_SUBTEXT, fontsize=9)

    # Barrier line
    if barrier_pct and barrier_pct > 1:
        barrier_val = barrier_pct
    elif barrier_pct:
        barrier_val = barrier_pct * 100
    else:
        barrier_val = None

    if barrier_val:
        ax.axhline(y=barrier_val, color="#DC2626", linestyle="--",
                   linewidth=1, alpha=0.8, label=f"Barrier {barrier_val:.0f}%")

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, fontsize=6.5)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    ax.tick_params(axis="y", labelsize=7)
    ax.grid(axis="y", linestyle=":", alpha=0.4, color=_MID_GRAY)
    ax.set_facecolor(_WHITE)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(_MID_GRAY)
    if ax.get_lines():
        ax.legend(fontsize=6.5, loc="upper left", framealpha=0.7,
                  edgecolor=_MID_GRAY, facecolor=_WHITE)


def _draw_coupon_table(ax, dates, amount_pct, total_pct, paid_dates_cutoff=None):
    """Draw the coupon schedule table."""
    ax.axis("off")
    headers = ["N°", "Payment Date", "Coupon"]
    col_x = [0.08, 0.55, 0.92]
    col_align = ["center", "center", "center"]

    # header
    for j, h in enumerate(headers):
        ax.text(col_x[j], 0.96, h, fontsize=7, fontweight="bold",
                color=_TEXT, ha=col_align[j], va="top", transform=ax.transAxes)

    ax.axhline(y=0.93, xmin=0, xmax=1, color=_MID_GRAY, linewidth=0.5,
               transform=ax.transAxes)

    n = len(dates)
    row_h = 0.88 / (n + 1) if n > 0 else 0.1

    for i, (d, amt) in enumerate(zip(dates, amount_pct)):
        y = 0.90 - i * row_h
        bg = _LIGHT_GRAY if i % 2 == 0 else _WHITE
        ax.add_patch(Rectangle((0, y - row_h * 0.85), 1, row_h * 0.85,
                                facecolor=bg, edgecolor="none",
                                transform=ax.transAxes, clip_on=True))
        paid = paid_dates_cutoff and d <= paid_dates_cutoff
        color = _TEXT if paid else _SUBTEXT
        ax.text(col_x[0], y - row_h * 0.4, str(i + 1), fontsize=7,
                ha="center", va="center", transform=ax.transAxes, color=color)
        ax.text(col_x[1], y - row_h * 0.4, _fmt_date(d), fontsize=7,
                ha="center", va="center", transform=ax.transAxes, color=color)
        ax.text(col_x[2], y - row_h * 0.4, f"{amt:.3f}%", fontsize=7,
                ha="center", va="center", transform=ax.transAxes, color=color)

    # Total row
    y_total = 0.90 - n * row_h
    ax.add_patch(Rectangle((0, y_total - row_h * 0.85), 1, row_h * 0.85,
                            facecolor=_hex(_CHART_COLORS[0]) + "22",
                            edgecolor=_MID_GRAY, linewidth=0.3,
                            transform=ax.transAxes, clip_on=True))
    ax.text(col_x[1], y_total - row_h * 0.4, "Total paid", fontsize=7.5,
            ha="center", va="center", transform=ax.transAxes, fontweight="bold",
            color=_TEXT)
    ax.text(col_x[2], y_total - row_h * 0.4, f"{total_pct:.3f}%", fontsize=7.5,
            ha="center", va="center", transform=ax.transAxes, fontweight="bold",
            color=_TEXT)


def _draw_summary_table(ax, rows, primary):
    """Draw summary results table (bottom of factsheet)."""
    ax.axis("off")
    n_cols = len(rows[0]) if rows else 0
    n_rows = len(rows)
    col_w = 1.0 / n_cols if n_cols else 1

    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            x = c * col_w + col_w / 2
            y = 1 - r * 0.5 - 0.25
            bg = _hex(primary) if r == 0 else (_LIGHT_GRAY if r % 2 == 1 else _WHITE)
            text_color = _WHITE if r == 0 else _TEXT
            ax.add_patch(Rectangle((c * col_w, 1 - (r + 1) * 0.5), col_w, 0.5,
                                    facecolor=bg, edgecolor=_WHITE, linewidth=1))
            ax.text(x, y, str(cell), fontsize=6.5, ha="center", va="center",
                    color=text_color, fontweight="bold" if r == 0 else "normal",
                    wrap=True)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, n_rows * 0.5)


# ── Main generator ─────────────────────────────────────────────────────────────

def generate_factsheet_pdf(product, event_type: str, company_name: str = "My Company",
                           primary: str = "#2563EB", secondary: str = "#DC2626") -> BytesIO:
    """
    Generate a PDF factsheet for a structured product.

    event_type: "Autocall" | "Vencimiento" | "Ejecutado"
    Returns BytesIO containing the PDF.
    """
    p = primary if primary else "#2563EB"

    nombre = str(product.get("nombre_producto") or "Structured Product")
    isin = str(product.get("isin") or "—")
    moneda = str(product.get("moneda") or "USD")
    contraparte = str(product.get("contraparte") or "—")
    perfil = str(product.get("perfil") or "—")
    plazo_meses = product.get("plazo_meses")
    barrera_capital = product.get("barrera_capital")
    cupon_contingente = product.get("cupon_contingente")
    cupon_fijo = product.get("cupon_fijo")
    trigger_autocall = product.get("trigger_autocall")
    ganancia_maxima = product.get("ganancia_maxima")
    rendimiento_total = product.get("rendimiento_total")
    cap = product.get("cap")
    factor_participacion = product.get("factor_participacion")

    # Underlyings
    underlyings = []
    strikes = []
    spots = []
    for i in range(1, 5):
        u = product.get(f"underlying_{i}")
        s = product.get(f"strike_{i}")
        sp = product.get(f"spot_{i}")
        if u and str(u).strip() not in ("", "nan", "None"):
            underlyings.append(str(u).strip())
            strikes.append(s)
            spots.append(sp)

    # Dates
    start_date = _parse_date(product.get("fecha_inicio") or product.get("fecha_strike"))
    obs_final = _parse_date(product.get("fecha_obs_final"))
    maturity = _parse_date(product.get("fecha_vencimiento"))
    end_date = obs_final or maturity or date.today()

    # Autocall dates
    ac_dates = []
    for i in range(1, 11):
        d = _parse_date(product.get(f"fecha_autocall_{i}"))
        if d:
            ac_dates.append(d)

    # Autocall date (for Autocall type)
    autocall_actual = _parse_date(product.get("proximo_autocall")) if event_type == "Autocall" else None
    if not autocall_actual and event_type == "Autocall" and ac_dates:
        # Use the first past autocall date
        today = date.today()
        past = [d for d in ac_dates if d <= today]
        autocall_actual = past[-1] if past else ac_dates[0]

    # Build barrier display value
    barrier_display = None
    if barrera_capital is not None and not np.isnan(float(barrera_capital)):
        b = float(barrera_capital)
        barrier_pct = b * 100 if b <= 1 else b
        barrier_display = f"{(100 - barrier_pct):.0f}%"
        barrier_for_chart = barrier_pct
    else:
        barrier_for_chart = None

    # ── CARACTERÍSTICAS table rows ─────────────────────────────────────────────
    underlying_str = " / ".join(underlyings) if underlyings else "—"

    char_rows = []
    char_rows.append(("Asset Class", str(product.get("asset_class") or "Equity")))
    char_rows.append(("Risk Profile", perfil))
    char_rows.append(("Underlying(s)", underlying_str))
    char_rows.append(("Currency", moneda))
    if plazo_meses:
        char_rows.append(("Term", f"{plazo_meses} months"))
    char_rows.append(("Issuer / Counterparty", contraparte))
    if cupon_contingente and float(cupon_contingente) > 0:
        char_rows.append(("Annual Contingent Coupon", _pct(cupon_contingente)))
    if cupon_fijo and float(cupon_fijo) > 0:
        char_rows.append(("Annual Fixed Coupon", _pct(cupon_fijo)))
    if ganancia_maxima:
        gm = str(ganancia_maxima)
        char_rows.append(("Maximum Gain", gm if "%" in gm else _pct(ganancia_maxima)))
    if barrier_display:
        char_rows.append(("Barrier (downside)", barrier_display))
    if trigger_autocall and float(trigger_autocall) > 0:
        char_rows.append(("Autocall Trigger", _pct(trigger_autocall)))
    if cap and float(cap) > 0:
        char_rows.append(("Cap", _pct(cap)))
    if factor_participacion and float(factor_participacion) > 0:
        char_rows.append(("Participation Factor", f"{float(factor_participacion):.2f}x"))

    # Initial and final levels
    for i, (u, s, sp) in enumerate(zip(underlyings, strikes, spots)):
        if s and not np.isnan(float(s)):
            char_rows.append((f"Initial Level ({u})", f"{float(s):,.2f}"))
    for i, (u, s, sp) in enumerate(zip(underlyings, strikes, spots)):
        if sp and not np.isnan(float(sp)):
            char_rows.append((f"Final Level ({u})", f"{float(sp):,.2f}"))

    char_rows.append(("ISIN", isin))

    # ── Coupon schedule ────────────────────────────────────────────────────────
    coupon_dates = []
    coupon_amts = []

    if ac_dates and cupon_contingente and float(cupon_contingente) > 0:
        coupon_pct = float(cupon_contingente)
        if coupon_pct <= 1:
            coupon_pct *= 100
        n_per_year = 4  # default quarterly
        if len(ac_dates) >= 2:
            delta_days = (ac_dates[1] - ac_dates[0]).days
            if delta_days > 150:
                n_per_year = 2
            elif delta_days > 80:
                n_per_year = 4
            elif delta_days > 20:
                n_per_year = 12
        period_coupon = coupon_pct / n_per_year

        cutoff = autocall_actual or end_date
        for d in ac_dates:
            if d <= cutoff:
                coupon_dates.append(d)
                coupon_amts.append(period_coupon)

    total_paid = rendimiento_total
    if total_paid is None and coupon_amts:
        total_paid = sum(coupon_amts)
    elif total_paid is not None:
        if abs(float(total_paid)) <= 1:
            total_paid = float(total_paid) * 100

    # ── Build figure ────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(11.69, 8.27), facecolor=_WHITE, dpi=150)

    _add_header_bar(fig, event_type, p, company_name)
    _add_title(fig, f"{event_type.upper()} — {nombre}", p, top=0.895)
    _add_section_label(fig, "  PRODUCT DETAILS", p, top=0.868)

    # ── Narrative text (Detalle del producto) ──────────────────────────────────
    ax_text = fig.add_axes([0.012, 0.810, 0.976, 0.055])
    ax_text.axis("off")
    narrative = _build_narrative(
        nombre, event_type, underlyings, start_date, end_date,
        autocall_actual, cupon_contingente, barrera_capital,
        rendimiento_total, ganancia_maxima, factor_participacion,
        cap, cupon_fijo,
    )
    ax_text.text(0, 0.95, narrative, fontsize=7.5, va="top", wrap=True,
                 color=_TEXT, multialignment="left")

    # ── Two-column layout: table | chart ──────────────────────────────────────
    _add_section_label(fig, "  GENERAL CHARACTERISTICS", p, top=0.778)

    n_char_rows = max(len(char_rows), 8)
    ax_table = fig.add_axes([0.012, 0.460, 0.44, 0.315])
    _draw_table(ax_table, char_rows, header_color=p)

    ax_chart = fig.add_axes([0.47, 0.460, 0.518, 0.315])
    ax_chart.set_title("Underlying Performance", fontsize=8, color=_TEXT, pad=4)
    _performance_chart(ax_chart, underlyings, start_date, end_date,
                       barrier_for_chart, p)

    # ── Summary table ──────────────────────────────────────────────────────────
    _add_section_label(fig, "  SUMMARY", p, top=0.432)
    ax_summary = fig.add_axes([0.012, 0.355, 0.976, 0.075])

    if event_type == "Autocall":
        sum_headers = ["Product", "Start Date", "Maturity Date",
                       "Autocall Date", "Product Return", "Ann. Return"]
        ann = None
        if rendimiento_total and start_date and autocall_actual:
            days = (autocall_actual - start_date).days
            rt = float(rendimiento_total)
            if abs(rt) <= 1:
                rt *= 100
            ann = rt / (days / 365) if days > 0 else None
        sum_vals = [
            nombre[:30],
            _fmt_date(start_date),
            _fmt_date(maturity),
            _fmt_date(autocall_actual),
            f"{float(rendimiento_total)*100:.2f}%" if rendimiento_total and abs(float(rendimiento_total)) <= 1 else (f"{float(rendimiento_total):.2f}%" if rendimiento_total else "—"),
            f"{ann:.2f}%" if ann else "—",
        ]
    elif event_type == "Vencimiento":
        sum_headers = ["Product", "Start Date", "Final Obs. Date",
                       "Maturity Date", "Product Return", "Ann. Return"]
        ann = None
        if rendimiento_total and start_date and end_date:
            days = (end_date - start_date).days
            rt = float(rendimiento_total)
            if abs(rt) <= 1:
                rt *= 100
            ann = rt / (days / 365) if days > 0 else None
        rt_display = f"{float(rendimiento_total)*100:.2f}%" if rendimiento_total and abs(float(rendimiento_total)) <= 1 else (f"{float(rendimiento_total):.2f}%" if rendimiento_total else "—")
        sum_vals = [nombre[:30], _fmt_date(start_date), _fmt_date(obs_final),
                    _fmt_date(maturity), rt_display,
                    f"{ann:.2f}%" if ann else "—"]
    else:  # Ejecutado
        sum_headers = ["Product", "Start Date", "Final Obs. Date",
                       "Maturity Date", "Max. Gain", "ISIN"]
        gm_str = str(ganancia_maxima) if ganancia_maxima else "—"
        sum_vals = [nombre[:30], _fmt_date(start_date), _fmt_date(obs_final),
                    _fmt_date(maturity), gm_str, isin]

    _draw_summary_table(ax_summary, [sum_headers, sum_vals], p)

    # ── EVOLUCIÓN DEL PRODUCTO ─────────────────────────────────────────────────
    _add_section_label(fig, "  PRODUCT EVOLUTION", p, top=0.325)

    if coupon_dates:
        ax_cpn_hdr = fig.add_axes([0.012, 0.295, 0.44, 0.028])
        ax_cpn_hdr.axis("off")
        rend_sub = _fmt_underlying_returns(underlyings, strikes, spots)
        ax_cpn_hdr.text(0, 0.5, f"Underlying(s): {underlying_str}",
                        fontsize=7, color=_TEXT, va="center")
        if rendimiento_total is not None:
            rt = float(rendimiento_total)
            rt_pct = rt * 100 if abs(rt) <= 1 else rt
            ax_cpn_hdr.text(0.99, 0.5, f"Product Return: {rt_pct:.2f}%",
                            fontsize=8, fontweight="bold", color=_hex(secondary),
                            ha="right", va="center")

        ax_cpn = fig.add_axes([0.012, 0.075, 0.42, 0.218])
        _draw_coupon_table(ax_cpn, coupon_dates, coupon_amts,
                           total_paid or sum(coupon_amts),
                           paid_dates_cutoff=autocall_actual or end_date)
    else:
        ax_no_cpn = fig.add_axes([0.012, 0.075, 0.42, 0.248])
        ax_no_cpn.axis("off")
        ax_no_cpn.text(0.5, 0.5, "Coupon schedule not applicable\n(Return at maturity)",
                       ha="center", va="center", fontsize=9, color=_SUBTEXT,
                       style="italic")

    # Evolution chart (worst-of performance)
    ax_evo = fig.add_axes([0.47, 0.075, 0.518, 0.248])
    ax_evo.set_title("Worst-of Underlying Performance", fontsize=8, color=_TEXT, pad=4)
    _performance_chart(ax_evo, underlyings, start_date,
                       autocall_actual or end_date, barrier_for_chart, p)

    # ── Footer ─────────────────────────────────────────────────────────────────
    ax_footer = fig.add_axes([0.012, 0.005, 0.976, 0.065])
    ax_footer.axis("off")
    disclaimer = (
        "This document is for informational purposes only and does not constitute investment advice. "
        "Past performance is not indicative of future results. "
        f"Structured products involve risks including loss of principal. Issued by {contraparte}. "
        "Generated by Structured Products Manager."
    )
    ax_footer.text(0, 0.8, disclaimer, fontsize=5.5, color=_SUBTEXT,
                   va="top", wrap=True)

    # ── Save ───────────────────────────────────────────────────────────────────
    buf = BytesIO()
    fig.savefig(buf, format="pdf", bbox_inches="tight", dpi=150, facecolor=_WHITE)
    plt.close(fig)
    buf.seek(0)
    return buf


# ── Narrative text builder ─────────────────────────────────────────────────────

def _fmt_underlying_returns(underlyings, strikes, spots):
    parts = []
    for u, s, sp in zip(underlyings, strikes, spots):
        if s and sp and not np.isnan(float(s)) and not np.isnan(float(sp)):
            ret = (float(sp) / float(s) - 1) * 100
            parts.append(f"{u}: {ret:+.2f}%")
    return " / ".join(parts) if parts else ""


def _build_narrative(nombre, event_type, underlyings, start_date, end_date,
                     autocall_date, cupon, barrera, rendimiento,
                     ganancia_maxima, factor_part, cap, cupon_fijo):
    sub_str = " and ".join(underlyings) if underlyings else "the underlying asset"
    start_str = _fmt_date(start_date)
    end_str = _fmt_date(end_date)

    if event_type == "Autocall":
        autocall_str = _fmt_date(autocall_date)
        rt = float(rendimiento) if rendimiento else None
        rt_pct = (rt * 100 if abs(rt) <= 1 else rt) if rt else None
        rt_str = f"{rt_pct:.2f}%" if rt_pct else "—"
        return (
            f"The {nombre} was called early on {autocall_str}, achieving a return of {rt_str} "
            f"for the period from {start_str} to {autocall_str}. "
            f"The product offered a contingent annual coupon of {_pct(cupon)} provided the underlying(s) ({sub_str}) "
            f"remained above {_pct(barrera)} of their initial level on each observation date."
        )
    elif event_type == "Vencimiento":
        rt = float(rendimiento) if rendimiento else None
        rt_pct = (rt * 100 if abs(rt) <= 1 else rt) if rt else None
        rt_str = f"{rt_pct:.2f}%" if rt_pct else "—"
        return (
            f"The {nombre} reached its scheduled maturity on {end_str}, delivering a return of {rt_str} "
            f"for the period from {start_str} to {end_str}. "
            f"The product offered a contingent annual coupon of {_pct(cupon)} provided the underlying(s) ({sub_str}) "
            f"remained above {_pct(barrera)} of their initial level."
        )
    else:  # Ejecutado
        gm = str(ganancia_maxima) if ganancia_maxima else _pct(cupon)
        return (
            f"The {nombre} offers investors exposure to {sub_str} over a period from {start_str} to {end_str}. "
            f"The product provides a maximum potential gain of {gm}. "
            f"Capital protection is subject to the issuer's credit risk and the performance of the underlying(s)."
        )
