# StructureAI — Structured Products Data Manager

AI-powered lifecycle management platform for structured investment products: automated termsheet extraction, factsheet generation, and portfolio analytics with live market data.

## Demo Video

[Ver demo en Google Drive](https://drive.google.com/file/d/1Mo_ApYgqyuPxnMVQZuEbPxQ4hkY_fLdT/view?usp=sharing)

## Live App

[structured-funds-data-manager.streamlit.app](https://structured-funds-data-manager.streamlit.app)

**Demo credentials:** `admin` / `demo2024`

## Features

- **AI Termsheet Extraction** — Claude API reads any PDF termsheet and extracts 50+ structured fields automatically
- **Portfolio Dashboard** — AUM by asset class, strategy, counterparty and country with Plotly charts
- **Event Calendar** — upcoming autocalls, maturities and coupon payments
- **Factsheet Generation** — branded A4 PPTX reports (Autocall, Vencimiento, Ejecutado) with live market data from yfinance
- **Excel Reports** — portfolio export with full product detail
- **crewAI Agents** — multi-agent pipeline for termsheet validation and enrichment

## Tech Stack

Python · Streamlit · SQLite · Claude API (Anthropic) · crewAI · python-pptx · yfinance · matplotlib · openpyxl

## Course Tools Used (Data Science con Python 2026-I — UP)

| Tool | Usage |
|------|-------|
| Claude AI / Document AI (Lectura 14) | PDF termsheet extraction — 50+ fields |
| crewAI Agents (Lecturas 10-11) | Validation and enrichment pipeline |
| Streamlit (Lecturas 3-7) | Full frontend and deployment |

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Set `ANTHROPIC_API_KEY` as an environment variable or in `.env`.
