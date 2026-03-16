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
    TheDiceShopScraper,
    UrlWatcherScraper,
)
from alerts.email import send_alert
from dashboard.generate import generate_dashboard
from dashboard.analytics_generate import generate_analytics
from dashboard.roadmap_generate import generate_roadmap
from scrapers.base import get_supabase
import logging

logger = logging.getLogger("run")


def _fetch_watchlist_items(sb):
    """Fetch active watchlist items from Supabase."""
    try:
        result = (
            sb.table("watchlist")
            .select("id, name, keywords, max_price, is_active")
            .eq("is_active", True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.warning(f"Could not fetch watchlist: {e}")
        return []


def _fetch_url_sources(sb):
    """Fetch active URL sources from Supabase."""
    try:
        result = (
            sb.table("url_sources")
            .select("id, label, url, is_active")
            .eq("is_active", True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.warning(f"Could not fetch url_sources: {e}")
        return []


def run_all():
    logger.info("=== dice-tracker run starting ===")

    # --- Default dice search ---
    scrapers = [
        ChessexScraper(),
        EbayScraper(),
        AliExpressScraper(),
        GoogleShoppingScraper(),
        TheDiceShopScraper(),
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

    # --- Watchlist searches ---
    sb = get_supabase()
    watchlist_items = _fetch_watchlist_items(sb)
    for item in watchlist_items:
        keywords = [k.strip() for k in item["keywords"].split("\n") if k.strip()]
        if not keywords:
            continue
        category_name = item["name"]
        max_price = float(item["max_price"]) if item.get("max_price") else None
        logger.info(f"Running watchlist search: {category_name} ({len(keywords)} keywords)")

        for scraper_cls in [EbayScraper, GoogleShoppingScraper]:
            try:
                scraper = scraper_cls()
                scraper.watchlist_category = category_name
                scraper.watchlist_max_price = max_price
                scraper.override_keywords = keywords
                result = scraper.run()
                new = result.get("new", 0)
                drops = result.get("drops", 0)
                total_new += new
                total_drops += drops
                if new > 0 or drops > 0:
                    alert_items.append(result)
            except Exception as e:
                logger.warning(f"Watchlist scraper failed for {category_name}/{scraper_cls.source}: {e}")

    # --- URL source watches ---
    url_sources = _fetch_url_sources(sb)
    for src in url_sources:
        try:
            logger.info(f"Running URL watcher: {src['label']} ({src['url'][:60]})")
            scraper = UrlWatcherScraper(url=src["url"], label=src["label"])
            result = scraper.run()
            new = result.get("new", 0)
            drops = result.get("drops", 0)
            total_new += new
            total_drops += drops
            if new > 0 or drops > 0:
                alert_items.append(result)
        except Exception as e:
            logger.warning(f"URL watcher failed for {src['label']}: {e}")

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

    # Regenerate dashboard + static pages
    generate_dashboard()
    generate_analytics()
    generate_roadmap()
    logger.info("Dashboard + analytics + roadmap regenerated")

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
