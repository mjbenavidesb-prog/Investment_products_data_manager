import anthropic
import base64
import json
import re
from pathlib import Path

EXTRACTION_PROMPT = """You are a senior derivatives structurer at a Latin American wealth manager with deep expertise in structured investment products and financial engineering.

Read this termsheet in full and extract all available fields. Return a single JSON object.

CRITICAL RULES:
- Bloomberg tickers: SHORT form only. For ETFs like "XLK UP Equity" use "XLK". For indices: SPX, RTY, NDX, INDU, SX5E, NKY, STOXX50E, etc.
- Dates: DD/MM/YYYY (e.g. "04/06/2026").
- Percentages as decimals: 75% → 0.75, 11% → 0.11. Never store as 75 or 11.
- Leverage as decimal: 1.33, not 133%.
- Numeric amounts: plain number (925000, not "USD 925,000").
- null if a field is truly absent. Never invent values.

FIELDS TO EXTRACT:
{
  "nombre_producto": "Descriptive commercial name max 60 chars. Build it as: [Issuer short name] [Product type] [Underlyings joined by /] [Key barrier or buffer %] [Maturity MonYY]. Examples: 'BNP Twin Win SPX/RTY 83.75% Jun27', 'Nomura Range Accrual XLK/XLU/XLP 75% Dec28', 'CACIB Airbag SPY/RSP/QQQ 87% Mar27'. If the termsheet already has a short commercial name (e.g. printed at the top as product title or in a 'Product Name' field), use that verbatim. Otherwise construct it from the fields above.",
  "tipo": "Certificate | Note | Warrant | Bond",
  "isin": "ISIN code — scan the ENTIRE document including headers, footers, tables, and fine print. An ISIN is exactly 12 characters: 2 uppercase letters (country code) + 10 alphanumeric chars. Common prefixes: XS (Euroclear), US (United States), DE (Germany), FR (France), CH (Switzerland), GB (UK). Look near ANY of these labels: 'ISIN', 'ISIN Code', 'Securities Code', 'Security Code', 'Product Code', 'Valor No.', 'WKN', 'Common Code', 'Security Identification Number', 'Identification Number', 'Identification', 'Code'. IMPORTANT: US ISINs (starting with 'US') are often found next to or just after the CUSIP (9-char code) — if you see a CUSIP, the 12-char code nearby is the ISIN. Return the ISIN exactly as printed. Return null ONLY if after reading the entire document you find no 12-character alphanumeric code matching the ISIN pattern.",
  "cusip": "CUSIP (9-char alphanumeric) if present and no ISIN, else null",
  "moneda": "USD | EUR | GBP | PEN | CLP | COP",
  "contraparte": "Guarantor bank short name (e.g. 'Nomura Holdings')",
  "garante": "Guarantor full legal name or null",
  "emisor": "Issuer entity full name (e.g. 'Nomura International Funding Pte. Ltd.')",

  "fecha_inicio": "Trade Date DD/MM/YYYY",
  "fecha_emision": "Issue Date DD/MM/YYYY",
  "fecha_strike": "Strike/Fixing Date DD/MM/YYYY (same as trade date if not separate)",
  "fecha_obs_final": "Final Valuation/Observation Date DD/MM/YYYY",
  "fecha_vencimiento": "Maturity/Redemption/Settlement Date DD/MM/YYYY",
  "plazo_meses": integer months from trade date to maturity (e.g. 36),

  "formato_subyacente": "Worst of | Individual | Basket",
  "underlying_1": "Bloomberg ticker of first underlying",
  "underlying_2": "Bloomberg ticker of second underlying or null",
  "underlying_3": "Bloomberg ticker of third underlying or null",
  "underlying_4": "Bloomberg ticker of fourth underlying or null",
  "strike_1": numeric initial/strike level of U1 or null,
  "strike_2": numeric initial/strike level of U2 or null,
  "strike_3": numeric initial/strike level of U3 or null,
  "strike_4": numeric initial/strike level of U4 or null,
  "peso_1": weight of U1 as decimal or null if equal-weighted/not stated,
  "peso_2": weight of U2 or null,
  "peso_3": weight of U3 or null,
  "peso_4": weight of U4 or null,

  "asset_class": "Renta Variable | Commodities | Renta Fija",
  "estrategia": "Opportunity | Capital Protegido",
  "tipo_estructura": "Distribucion | Participacion | Hibrido",
  "perfil": "Muy Conservador | Conservador | Moderado | Agresivo",

  "cupon_fijo": annual fixed coupon as decimal or null,
  "cupon_contingente": annual contingent/range accrual coupon as decimal (0.11 for 11% p.a.) or null,
  "barrera_cupon": coupon observation barrier as decimal (0.75 for 75%) or null. SET TO NULL for participation products (Airbag, Call Spread / Buffered Note, Capital Protected Participation, Dual Directional) — these have no coupon barrier.,
  "barrera_capital": capital protection / knock-in / floor barrier as decimal or null,
  "tipo_caida": "Knock In | Low Strike | Put Spread | None",
  "cap": cap level as decimal or null,
  "factor_participacion": participation rate as decimal or null,
  "trigger_autocall": autocall/knock-out trigger as decimal (1.0 for 100%) or null,
  "fecha_sin_autocall": "Non-call / lock-out end date DD/MM/YYYY or null",
  "ganancia_maxima": "Maximum gain as a string — read it directly from the termsheet. Examples: '33%', '16.25%', 'Ilimitada', 'Unlimited'. For coupon products multiply annual coupon rate by years ONLY if no cap or explicit max is stated. For capped products use the cap. For unlimited participation products use 'Ilimitada'.",

  "fecha_autocall_1": "First knock-out/autocall observation date DD/MM/YYYY or null",
  "fecha_autocall_2": "Second or null",
  "fecha_autocall_3": "Third or null",
  "fecha_autocall_4": "Fourth or null",
  "fecha_autocall_5": "Fifth or null",
  "fecha_autocall_6": "Sixth or null",
  "fecha_autocall_7": "Seventh or null",
  "fecha_autocall_8": "Eighth or null",
  "fecha_autocall_9": "Ninth or null",
  "fecha_autocall_10": "Tenth or null",

  "contraparte_derivado": "Swap counterparty if different from issuer or null",
  "prima_pct": issue price as decimal if discounted/warrant (e.g. 0.9645) or null,
  "formato": "Separable | No Separable",

  "elemento_1_tipo": "Primary element type — see ENGINEERING GUIDE",
  "elemento_1_leverage": numeric leverage of element 1 (e.g. 1.00),
  "elemento_1_posicion": "Long | Short",
  "elemento_2_tipo": "Secondary element type — see ENGINEERING GUIDE, or null",
  "elemento_2_leverage": numeric leverage of element 2 or null,
  "elemento_2_posicion": "Long | Short or null",
  "elemento_3_tipo": "Third element type if present or null",
  "elemento_3_leverage": numeric leverage or null,
  "elemento_3_posicion": "Long | Short or null"
}

CLASSIFICATION HINTS:
- Knock-in barrier + conditional coupons → tipo_caida = "Knock In", estrategia = "Opportunity"
- Capital 100% protected regardless of performance → estrategia = "Capital Protegido", tipo_caida = "None"
- perfil: Capital Protegido → "Conservador"; barrier 70-80% → "Moderado"; barrier ≤ 65% → "Agresivo"
- For autocall dates: extract the Knock-Out Determination Days (observation dates), NOT the coupon payment dates
- For Range Accrual: barrera_cupon = coupon barrier; barrera_capital = knock-in/capital barrier (may be same value)
- tipo_estructura — use exactly one of these values:
  "Distribucion" → product pays periodic income (coupons/accrual): elemento_1_tipo ∈ {Daily Range Accrual, Phoenix Autocall, Phoenix with Memory, Athena Autocall, Fixed Coupon, Digital Coupon}
  "Participacion" → capital return depends on underlying performance at maturity, no periodic coupon: elemento_1_tipo ∈ {Long Call (ATM), Long Call (ITM), Capital Protected Participation}
  "Hibrido" → product explicitly combines periodic coupons AND performance-linked capital at maturity

ENGINEERING GUIDE — Decompose the product into its derivative building blocks:

ELEMENT 1 (primary return generator — investor is typically LONG):
- "Daily Range Accrual": coupon paid proportional to fraction of trading days where each underlying closes >= coupon barrier. Key signal: "Relevant Accrual Fraction" or daily observation of basket.
- "Phoenix Autocall": conditional coupon at periodic observation dates if worst-of >= coupon barrier; autocalls if >= trigger.
- "Phoenix with Memory": Phoenix where missed coupons accumulate and are all paid when barrier is next observed.
- "Athena Autocall": always pays coupon on autocall dates (no separate coupon barrier).
- "Fixed Coupon": fixed rate regardless of performance.
- "Digital Coupon": binary — full coupon if above barrier, zero otherwise. Typically one large payment.
- "Capital Protected Participation": 100% capital floor + participation in upside (100% of initial guaranteed at maturity no matter what).
- "Long Call (ATM)": investor is LONG a call struck at 100% of initial. For Dual Directional / Twin Win structures, element 1 is always a Long Call (ATM) — the "dual directional" nature comes from element 2 (KO Put ATM) + element 3 (Short Put ATM), not element 1. Key signals for Dual Directional overall: "twin win", "dual directional", "buffer", absolute return participation.
- "Long Call (ATM)": investor is LONG a call struck at 100% of initial. Standard upside participation. Used in Airbag notes for the growth component. Leverage = participation rate (e.g., 1.50 for 150%).
- "Long Call (ITM)": investor is LONG a call struck BELOW 100% of initial (e.g., 90% floor/buffer level). Creates 1:1 participation starting from the buffer level; combined with Short Call OTM to cap upside. Used in Call Spread / Buffered Note structures. The strike IS the floor/buffer. Leverage = 1.00 typically.

ELEMENT 2 (secondary derivative block):
- "Low Strike Put": put struck BELOW 100% of initial price. Investor bears loss when worst-of < strike at maturity. Leverage = 1/strike_pct (e.g. strike=75% → 1/0.75 = 1.333). European observation (final valuation date only). Position: Short.
- "KI Put (European)": put activated only if worst-of <= KI price on the FINAL valuation date. Usually struck at 100%. Position: Short.
- "KI Put (American)": put activated if worst-of <= KI price on ANY trading day. Higher risk than European. Position: Short.
- "KO Put (ATM)": ATM put that KNOCKS OUT when worst-of <= barrier. Provides twin-win benefit within buffer zone. Used in Dual Directional structures. Position: Long.
- "Short Put (ATM)": short put struck at 100% (ATM at inception), no barrier. Used in Dual Directional to offset the cost of the Long KO Put ATM. Position: Short.
- "Low Strike Call": investor is LONG a call with strike below 100%; leveraged upside. Leverage = 1/strike. Position: Long.
- "Short Call (OTM)": investor SHORT a call above 100%, caps the maximum gain. Strike = 100% + max_gain/participation_rate. Used to cap upside in Call Spread and Airbag structures. Leverage = same as element 1. Position: Short.

ELEMENT 3 (third block — used when product has three derivative components):
- "KO Put (ATM)": same as element 2. Position: Long.
- "Short Put (ATM)": Short put at 100% (ATM) that offsets the Long KO Put ATM cost. Used in Dual Directional / Twin Win. Position: Short.
- "Short Call (OTM)": cap on levered element when element 1 is the main upside and element 2 is also upside. Position: Short.
- "Short Put (OTM)": investor SHORT a put BELOW 100% (at airbag/buffer level). Below this level investor bears losses 1:1. Above this level, if element 1 is a Long Call ATM, the buffer zone between put strike and 100% gives full capital return ("airbag" effect). Position: Short. Key signal: "Airbag", "buffer zone", protection between barrier and 100%.
- null: only two elements needed.

LEVERAGE CALCULATION GUIDE:
- Range Accrual / Phoenix coupon component: 1.00
- Low Strike Put: leverage = 1.0 / strike_as_decimal (e.g. 75% strike → 1.333)
- KI Put at 100% strike: 1.00
- Long Call (ATM) / Long Call (ITM): the stated participation rate (e.g. 1.50 for 150%). Default 1.00.
- Short Call (OTM): SAME leverage as the Long Call element it caps (e.g. if element 1 is 1.50x Long Call ATM, element 2 is 1.50x Short Call OTM).
- Short Put (OTM): 1.00 (airbag put absorbs losses 1:1 below barrier).
- Dual Directional / twin win call: 1.00
- If leverage for an element is not explicitly stated and cannot be calculated, use 1.00

CAP FIELD: Store as the TOTAL redemption level factor (e.g. 1.332 for a 33.2% max gain, 1.263 for 26.3%). If the termsheet states "Maximum Return = 33.20%", cap = 1.3320.
BARRERA_CAPITAL for participation products: store the barrier/floor/buffer level as decimal (e.g. 0.90 for 10% buffer, 0.87 for 13% airbag level).

EXAMPLE 1 — Nomura 36M Callable Daily Range Accrual (Strike=75%, KI=75%, European final obs):
{
  "elemento_1_tipo": "Daily Range Accrual",
  "elemento_1_leverage": 1.00,
  "elemento_1_posicion": "Long",
  "elemento_2_tipo": "Low Strike Put",
  "elemento_2_leverage": 1.333,
  "elemento_2_posicion": "Short",
  "elemento_3_tipo": null,
  "elemento_3_leverage": null,
  "elemento_3_posicion": null,
  "ganancia_maxima": "33.0%"
}
Reasoning: leverage = 1/0.75 = 1.333; KI observed only at final valuation → European → Low Strike Put. Max gain = 11% × 3 years = 33%.

EXAMPLE 2 — BNP Paribas Twin Win / Dual Directional (buffer 16.25%, barrier 83.75%, participation 1.00x, no cap):
{
  "elemento_1_tipo": "Long Call (ATM)",
  "elemento_1_leverage": 1.00,
  "elemento_1_posicion": "Long",
  "elemento_2_tipo": "KO Put (ATM)",
  "elemento_2_leverage": 2.00,
  "elemento_2_posicion": "Long",
  "elemento_3_tipo": "Short Put (ATM)",
  "elemento_3_leverage": 1.00,
  "elemento_3_posicion": "Short",
  "ganancia_maxima": "Ilimitada",
  "barrera_capital": 0.8375
}
Reasoning: Long Call ATM (1x) gives upside. Long KO Put ATM (2x, KO at 83.75%) gives twin-win benefit within buffer. Short Put ATM (1x) offsets the cost. Investor gains above AND below initial level within the 16.25% buffer. No upside cap → ganancia_maxima = "Ilimitada".

EXAMPLE 3 — BNP Paribas Call Spread / Buffered Note (Nokia, floor 90%, max return 33.20%, participation 100%):
{
  "elemento_1_tipo": "Long Call (ITM)",
  "elemento_1_leverage": 1.00,
  "elemento_1_posicion": "Long",
  "elemento_2_tipo": "Short Call (OTM)",
  "elemento_2_leverage": 1.00,
  "elemento_2_posicion": "Short",
  "elemento_3_tipo": null,
  "elemento_3_leverage": null,
  "elemento_3_posicion": null,
  "ganancia_maxima": "33.20%",
  "barrera_capital": 0.90,
  "cap": 1.3320
}
Reasoning: ZCB (90%) + Long Call struck at 90% (ITM since market starts at 100%) + Short Call struck at 133.2% (OTM). Investor participates 1:1 upside up to 33.2% gain; loses 1:1 in moderate downside; hard floor at 90% (max loss 10%). Key signal: "Maximum Return", partial principal protection at 90%.

EXAMPLE 4 — Crédit Agricole Airbag Note (worst-of SPY/RSP/QQQ, barrier 87%, participation 150%, cap 26.325%):
{
  "elemento_1_tipo": "Long Call (ATM)",
  "elemento_1_leverage": 1.50,
  "elemento_1_posicion": "Long",
  "elemento_2_tipo": "Short Call (OTM)",
  "elemento_2_leverage": 1.50,
  "elemento_2_posicion": "Short",
  "elemento_3_tipo": "Short Put (OTM)",
  "elemento_3_leverage": 1.00,
  "elemento_3_posicion": "Short",
  "ganancia_maxima": "26.33%",
  "barrera_capital": 0.87,
  "cap": 1.26325,
  "factor_participacion": 1.50
}
Reasoning: Long Call ATM (1.5x) caps with Short Call OTM (1.5x at ~117.5%) = levered capped upside. Short Put OTM at 87% = investor bears losses below 87% only. Between 87% and 100% the investor gets 100% back ("airbag" zone). Key signals: "Airbag", "Moderate Scenario = 100%", buffer below strike pays back full capital.

Return ONLY the JSON object. No markdown, no explanation, no code fences.
"""


_ISIN_RESCUE_PROMPT = """Read this document and find the ISIN code.

An ISIN is exactly 12 characters: 2 uppercase country-code letters + 10 alphanumeric characters.
Common prefixes: XS, US, DE, FR, CH, GB, LU, NL, IT, ES, JP, AU.
US ISINs (starting "US") are often printed next to or just after a 9-char CUSIP code.
Scan every page, every table cell, every header, every footer.

Reply with ONLY the ISIN code (e.g. US09664K6Q16) or the word null. Nothing else."""

_ISIN_RE = re.compile(r'\b([A-Z]{2}[A-Z0-9]{10})\b')


def _rescue_isin(pdf_b64: str, client) -> str | None:
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=32,
        messages=[{
            "role": "user",
            "content": [
                {"type": "document", "source": {
                    "type": "base64", "media_type": "application/pdf", "data": pdf_b64}},
                {"type": "text", "text": _ISIN_RESCUE_PROMPT},
            ],
        }],
    )
    text = msg.content[0].text.strip()
    m = _ISIN_RE.search(text)
    return m.group(1) if m else None


def extract_termsheet(pdf_bytes: bytes, api_key: str, filename: str = "") -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": EXTRACTION_PROMPT,
                    },
                ],
            }
        ],
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    result = json.loads(raw)

    if not result.get("isin"):
        rescued = _rescue_isin(pdf_b64, client)
        if rescued:
            result["isin"] = rescued

    if not result.get("isin") and filename:
        m = _ISIN_RE.search(filename)
        if m:
            result["isin"] = m.group(1)

    return result


def extract_termsheet_from_path(pdf_path: str, api_key: str) -> dict:
    with open(pdf_path, "rb") as f:
        return extract_termsheet(f.read(), api_key)
