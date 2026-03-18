"""
roadmap_generate.py - Generates a static roadmap.html page.
Called from scrapers/run.py alongside generate_dashboard().
Hardcoded phases and items - no database needed.
"""
import os
from datetime import datetime
import logging

logger = logging.getLogger("roadmap")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "roadmap.html")

PHASES = [
    {
        "title": "Phase 1 \u2014 Foundation",
        "desc": "Core features \u2014 all shipped",
        "items": [
            ("Dashboard with Results, Watchlist, Settings tabs", "done"),
            ("Run search now button with GitHub PAT", "done"),
            ("Email alerts managed from Settings", "done"),
            ("Chessex + Dice Shop scrapers", "done"),
            ("Watchlist item edit button", "done"),
            ("eBay official API", "done"),
            ("Auto-generated Analytics page", "done"),
            ("Auto-generated Roadmap page", "done"),
        ],
    },
    {
        "title": "Phase 2 \u2014 Data & sources",
        "desc": "More data sources and richer product info",
        "items": [
            ("URL watcher \u2014 paste any product URL to track directly", "soon"),
            ("Product photos \u2014 show thumbnail images from listings", "soon"),
            ("Header search indicator with live status", "soon"),
            ("GitHub Actions usage monitor in dashboard footer", "soon"),
            ("Price history sparkline on each product", "soon"),
        ],
    },
    {
        "title": "Phase 3 \u2014 Analytics",
        "desc": "Price intelligence and stock tracking",
        "items": [
            ("Price change indicator vs 7 days ago", "planned"),
            ("Price drop email alerts with target price", "planned"),
            ("Stock availability history percentage", "planned"),
            ("Best price comparison across sources", "planned"),
        ],
    },
    {
        "title": "Phase 4 \u2014 Website integration",
        "desc": "Connect to mahjbox.com for staff sourcing",
        "items": [
            ("Mahj Box staff sourcing page on mahjbox.com", "planned"),
            ("Save / Skip curation buttons on products", "planned"),
            ("Squarespace embed component", "planned"),
            ("Seasonal price trend analysis", "planned"),
        ],
    },
]

STATUS_STYLES = {
    "done": ("Done", "background:#e8f5e9;color:#27ae60"),
    "active": ("Active", "background:#e3f2fd;color:#1976d2"),
    "soon": ("Soon", "background:#fff8e1;color:#f39c12"),
    "planned": ("Planned", "background:#f0f0f0;color:#888"),
}


def generate_roadmap():
    html = _render()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info("Roadmap page written")


def _render():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    phases_html = ""
    for phase in PHASES:
        items_html = ""
        for name, status in phase["items"]:
            label, style = STATUS_STYLES.get(status, ("Planned", "background:#f0f0f0;color:#888"))
            items_html += (
                '<div style="display:flex;align-items:center;gap:12px;padding:10px 14px;'
                'background:#fff;border:1px solid #e5e5e5;border-radius:8px;margin-bottom:8px">'
                f'<div style="flex:1;font-size:14px">{name}</div>'
                f'<span style="font-size:11px;padding:2px 8px;border-radius:999px;font-weight:500;{style}">{label}</span>'
                '</div>'
            )
        phases_html += (
            '<div style="margin-bottom:32px">'
            f'<div style="font-size:16px;font-weight:600;margin-bottom:4px">{phase["title"]}</div>'
            f'<div style="font-size:12px;color:#888;margin-bottom:14px">{phase["desc"]}</div>'
            f'{items_html}'
            '</div>'
        )

    CSS = """*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f7f7f7;color:#1a1a1a}
.header{background:#fff;border-bottom:1px solid #e5e5e5;padding:0 24px;display:flex;align-items:center;gap:24px}
.header h1{font-size:18px;font-weight:600;padding:16px 0}
.header a{font-size:13px;color:#888;text-decoration:none;margin-left:auto}
.header a:hover{color:#1a1a1a}
.content{max-width:720px;margin:0 auto;padding:28px 24px}
.meta{color:#999;font-size:13px;margin-bottom:20px}"""

    return (
        '<!DOCTYPE html><html lang="en"><head>'
        '<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<title>Product Tracker - Roadmap</title>'
        f'<style>{CSS}</style></head><body>'
        '<div class="header"><h1>Roadmap</h1><a href="index.html">&larr; Back to dashboard</a></div>'
        '<div class="content">'
        f'<p class="meta">Generated: {now}</p>'
        f'{phases_html}'
        '</div></body></html>'
    )


if __name__ == "__main__":
    generate_roadmap()
