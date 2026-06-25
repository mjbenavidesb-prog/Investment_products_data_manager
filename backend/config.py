from backend.database import get_config, set_config

DEFAULTS = {
    "company_name": "",
    "primary_color": "#2563EB",
    "secondary_color": "#DC2626",
    "accent_color_1": "#F59E0B",
    "accent_color_2": "#10B981",
    "accent_color_3": "#8B5CF6",
    "neutral_color": "#6B7280",
    "vehicles": [
        "Mutual Fund",
        "Securitised Bond Portfolio",
        "Segregated Portfolio",
        "Note Sub-Distribution",
        "Collective Investment Fund",
        "VEST Portfolio",
    ],
    "segments": [
        "BP Peru", "BP Chile", "BP Colombia", "BP US",
        "Mandate RIA", "W9", "Enalta", "BEX",
        "Consumer", "Legal Entities", "MFO", "Vicctus", "TYBA", "Other",
    ],
    "countries": ["Peru", "Chile", "Colombia", "United States", "Panama"],
    "client_types": ["Institutional", "Retail", "Mandate RIA", "W9"],
    "entities": [
        "Entity A", "Entity B", "Entity C",
        "Entity D", "Entity E", "Entity F", "Entity G",
    ],
    "profiles": ["Very Conservative", "Conservative", "Moderate", "Aggressive"],
    "asset_classes": ["Equity", "Commodities", "Fixed Income"],
    "jurisdictions": ["Peru", "Panama", "Colombia", "United States", "Chile"],
    "business_days_payment": 3,
    "custom_fields": [],
}


def get(key: str):
    val = get_config(key)
    if val is None:
        return DEFAULTS.get(key)
    return val


def save(key: str, value):
    set_config(key, value)


def get_all() -> dict:
    result = {}
    for key in DEFAULTS:
        result[key] = get(key)
    return result


def color_sequence() -> list[str]:
    """Return the full ordered palette for charts."""
    return [
        get("primary_color") or DEFAULTS["primary_color"],
        get("secondary_color") or DEFAULTS["secondary_color"],
        get("accent_color_1") or DEFAULTS["accent_color_1"],
        get("accent_color_2") or DEFAULTS["accent_color_2"],
        get("accent_color_3") or DEFAULTS["accent_color_3"],
        get("neutral_color") or DEFAULTS["neutral_color"],
    ]
