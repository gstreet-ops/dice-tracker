"""
base.py — Base scraper class for dice-tracker.
All source scrapers inherit from this.
"""
import os
import time
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(".env.local")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


def get_supabase() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


class BaseScraper:
    source = "unknown"
    delay_seconds = 2  # polite delay between requests

    def __init__(self):
        self.logger = logging.getLogger(self.source)
        self.supabase = get_supabase()
        self.results = []

    def fetch(self) -> list:
        """Override in subclass. Return list of raw result dicts."""
        raise NotImplementedError

    def run(self) -> dict:
        """Run scraper, upsert to Supabase, return summary."""
        import time as t
        start = t.time()
        self.logger.info(f"Starting {self.source} scraper")
        try:
            raw = self.fetch()
        except Exception as e:
            self.logger.error(f"Fetch failed: {e}")
            self._log_run(0, 0, 0, str(e), t.time() - start)
            return {"source": self.source, "error": str(e)}

        new_count = 0
        drop_count = 0
        for item in raw:
            try:
                is_new, is_drop = self._upsert(item)
                if is_new:
                    new_count += 1
                if is_drop:
                    drop_count += 1
                time.sleep(0)
            except Exception as e:
                self.logger.warning(f"Upsert failed for {item.get('url')}: {e}")

        duration = t.time() - start
        self._log_run(len(raw), new_count, drop_count, None, duration)
        self.logger.info(
            f"Done: {len(raw)} found, {new_count} new, {drop_count} drops "
            f"in {duration:.1f}s"
        )
        return {
            "source": self.source,
            "found": len(raw),
            "new": new_count,
            "drops": drop_count,
        }
    def _upsert(self, item: dict) -> tuple[bool, bool]:
        """
        Upsert product + price_history row.
        Returns (is_new, is_price_drop).
        """
        from filters import score_product, infer_size_mm

        url = item.get("url", "")
        title = item.get("title", "")
        price_usd = item.get("price_usd")
        size_mm = item.get("size_mm") or infer_size_mm(title)

        scored = score_product(
            title=title,
            description=item.get("description", ""),
            size_mm=size_mm,
            price_usd=price_usd,
        )

        if scored["excluded"]:
            self.logger.debug(f"Excluded: {title[:60]} — {scored['reason']}")
            return False, False

        # Check if product exists
        existing = (
            self.supabase.table("products")
            .select("id, score")
            .eq("url", url)
            .execute()
        )

        is_new = len(existing.data) == 0

        product_data = {
            "source": self.source,
            "title": title,
            "url": url,
            "image_url": item.get("image_url"),
            "size_mm": size_mm,
            "material": item.get("material"),
            "finish": item.get("finish"),
            "pip_style": item.get("pip_style"),
            "set_count": item.get("set_count"),
            "score": scored["score"],
            "last_seen": datetime.now(timezone.utc).isoformat(),
        }

        if is_new:
            self.supabase.table("products").insert(product_data).execute()
            product_id = (
                self.supabase.table("products")
                .select("id")
                .eq("url", url)
                .single()
                .execute()
                .data["id"]
            )
        else:
            product_id = existing.data[0]["id"]
            self.supabase.table("products").update(product_data).eq(
                "id", product_id
            ).execute()

        # Insert price history row
        if price_usd:
            self.supabase.table("price_history").insert({
                "product_id": product_id,
                "price_usd": price_usd,
                "currency_orig": item.get("currency", "USD"),
                "price_orig": item.get("price_orig", price_usd),
                "in_stock": item.get("in_stock", True),
            }).execute()

        # Check for price drop (compare to last recorded price)
        is_drop = False
        if not is_new and price_usd:
            history = (
                self.supabase.table("price_history")
                .select("price_usd")
                .eq("product_id", product_id)
                .order("scraped_at", desc=True)
                .limit(2)
                .execute()
            )
            if len(history.data) >= 2:
                prev_price = history.data[1]["price_usd"]
                drop_pct = (prev_price - price_usd) / prev_price * 100
                threshold = float(os.environ.get("PRICE_DROP_THRESHOLD_PCT", 5))
                if drop_pct >= threshold:
                    is_drop = True
                    self.logger.info(
                        f"Price drop {drop_pct:.1f}%: {title[:50]} "
                        f"${prev_price} → ${price_usd}"
                    )

        return is_new, is_drop

    def _log_run(self, found, new, drops, errors, duration):
        try:
            self.supabase.table("run_log").insert({
                "source": self.source,
                "results_found": found,
                "new_products": new,
                "price_drops": drops,
                "errors": errors,
                "duration_secs": round(duration, 2),
            }).execute()
        except Exception as e:
            self.logger.warning(f"Could not write run_log: {e}")
