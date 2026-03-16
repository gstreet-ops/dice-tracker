"""
ebay.py — eBay worldwide scraper for premium 50mm gold dice.
Uses eBay's public search (no API key required).
"""
import time
import requests
from bs4 import BeautifulSoup
from .base import BaseScraper

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

EBAY_SEARCHES = [
    "50mm gold dice d6 engraved",
    "jumbo gold metal dice 2 inch",
    "brass gold dice 50mm",
    "large gold dice premium engraved pips",
    "gold dice set d6 heavy metal",
    "oversized gold dice solid",
    "luxury gold dice set",
    "50mm dice gold",
]

EBAY_BASE = "https://www.ebay.com/sch/i.html"


class EbayScraper(BaseScraper):
    source = "ebay"

    def fetch(self) -> list[dict]:
        results = []
        seen_urls = set()

        for query in EBAY_SEARCHES:
            try:
                params = {
                    "_nkw": query,
                    "_sacat": 0,
                    "LH_BIN": 1,        # Buy It Now only
                    "_sop": 12,          # Sort: best match
                    "LH_ItemCondition": 1000,  # New
                }
                resp = requests.get(
                    EBAY_BASE, params=params, headers=HEADERS, timeout=15
                )
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")

                listings = soup.select(".s-item")
                self.logger.info(
                    f"eBay '{query}': {len(listings)} listings"
                )

                for item in listings[:20]:
                    title_el = item.select_one(".s-item__title")
                    price_el = item.select_one(".s-item__price")
                    link_el = item.select_one("a.s-item__link")
                    img_el = item.select_one("img.s-item__image-img")

                    if not title_el or not link_el:
                        continue

                    title = title_el.get_text(strip=True)
                    if title.lower() == "shop on ebay":
                        continue

                    url = link_el.get("href", "").split("?")[0]
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    price_text = price_el.get_text(strip=True) if price_el else ""
                    price_usd = self._parse_price(price_text)
                    img_url = img_el.get("src", "") if img_el else ""

                    results.append({
                        "title": title,
                        "url": url,
                        "image_url": img_url,
                        "price_usd": price_usd,
                        "size_mm": None,
                        "in_stock": True,
                        "source": "ebay",
                    })

                time.sleep(self.delay_seconds)

            except Exception as e:
                self.logger.error(f"eBay fetch error for '{query}': {e}")

        return results

    def _parse_price(self, text: str) -> float | None:
        import re
        text = text.replace(",", "").replace("$", "").strip()
        m = re.search(r"(\d+(?:\.\d{2})?)", text)
        return float(m.group(1)) if m else None
