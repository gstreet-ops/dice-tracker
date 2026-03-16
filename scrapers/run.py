"""
run.py — Main entry point. Runs all scrapers and triggers alerts.
Usage: python scrapers/run.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers import (
    ChessexScraper,
    EbayScraper,
    AliExpressScraper,
    GoogleShoppingScraper,
)
from alerts.email import send_alert
from dashboard.generate import generate_dashboard
from scrapers.base import get_supabase
import logging

logger = logging.getLogger("run")


def run_all():
    logger.info("=== dice-tracker run starting ===")

    scrapers = [
        ChessexScraper(),
        EbayScraper(),
        AliExpressScraper(),
        GoogleShoppingScraper(),
    ]

    total_new = 0
    total_drops = 0
    alert_items = []

    for scraper in scrapers:
        result = scraper.run()
        new = result.get("new", 0)
        drops = result.get("drops", 0)
        total_new += new
        total_drops += drops

        if new > 0 or drops > 0:
            alert_items.append(result)

    logger.info(
        f"=== Run complete: {total_new} new products, "
        f"{total_drops} price drops ==="
    )

    # Send alert email if anything interesting found
    if alert_items:
        top_products = _get_top_products()
        send_alert(
            new_count=total_new,
            drop_count=total_drops,
            top_products=top_products,
        )

    # Regenerate dashboard
    generate_dashboard()
    logger.info("Dashboard regenerated")

    # Ping keepalive
    _ping_keepalive()


def _get_top_products(limit: int = 10) -> list[dict]:
    try:
        sb = get_supabase()
        result = (
            sb.table("products")
            .select(
                "id, title, url, source, score, size_mm, "
                "finish, material, pip_style, last_seen"
            )
            .eq("is_excluded", False)
            .order("score", desc=True)
            .limit(limit)
            .execute()
        )
        products = result.data or []

        # Attach latest price to each product
        for p in products:
            price_row = (
                sb.table("price_history")
                .select("price_usd, scraped_at, in_stock")
                .eq("product_id", p["id"])
                .order("scraped_at", desc=True)
                .limit(1)
                .execute()
            )
            if price_row.data:
                p["price_usd"] = price_row.data[0]["price_usd"]
                p["in_stock"] = price_row.data[0]["in_stock"]
            else:
                p["price_usd"] = None
                p["in_stock"] = None

        return products
    except Exception as e:
        logger.error(f"Could not fetch top products: {e}")
        return []


def _ping_keepalive():
    try:
        sb = get_supabase()
        sb.table("keepalive").update({"pinged_at": "now()"}).eq("id", 1).execute()
        logger.info("Keepalive pinged")
    except Exception as e:
        logger.warning(f"Keepalive ping failed: {e}")


if __name__ == "__main__":
    run_all()
