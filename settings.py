"""
settings.py — Reads tracker settings from Supabase settings table.
Falls back to defaults if table doesn't exist or setting is missing.
"""
import os

DEFAULTS = {
    "search_keywords": "50mm gold dice d6 engraved,jumbo gold metal dice 2 inch,brass gold dice 50mm",
    "max_price_usd": "150",
    "min_size_mm": "50",
    "run_frequency_hours": "6",
}


def get_settings(sb) -> dict:
    """Fetch all settings from Supabase. Returns dict with string values."""
    try:
        result = sb.table("settings").select("key, value").execute()
        settings = dict(DEFAULTS)
        for row in (result.data or []):
            settings[row["key"]] = row["value"]
        return settings
    except Exception:
        return dict(DEFAULTS)


def get_keywords(sb) -> list:
    """Return search keywords as a list."""
    settings = get_settings(sb)
    raw = settings.get("search_keywords", DEFAULTS["search_keywords"])
    return [k.strip() for k in raw.split(",") if k.strip()]


def get_max_price(sb) -> float:
    settings = get_settings(sb)
    try:
        return float(settings.get("max_price_usd", 150))
    except ValueError:
        return 150.0


def get_min_size_mm(sb) -> float:
    settings = get_settings(sb)
    try:
        return float(settings.get("min_size_mm", 50))
    except ValueError:
        return 50.0
