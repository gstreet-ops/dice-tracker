"""
google_shopping.py — Google Shopping scraper via SerpAPI free tier.
Free tier = 100 searches/month. Falls back to direct scrape if no key.
"""
import os
import time
import requests
from .base import BaseScraper

SEARCHES = [
    "50mm gold dice d6 engraved",
    "jumbo gold metal dice premium",
    "2 inch gold dice set engraved pips",
]


class GoogleShoppingScraper(BaseScraper):
    source = "google_shopping"

    def fetch(self) -> list[dict]:
        api_key = os.environ.get("SERPAPI_KEY", "")
        if api_key:
            return self._fetch_serpapi(api_key)
        self.logger.warning("No SERPAPI_KEY — skipping Google Shopping")
        return []

    def _fetch_serpapi(self, api_key: str) -> list[dict]:
        results = []
        seen = set()

        for query in SEARCHES:
            try:
                resp = requests.get(
                    "https://serpapi.com/search",
                    params={
                        "engine": "google_shopping",
                        "q": query,
                        "api_key": api_key,
                        "num": 20,
                        "gl": "us",
                        "hl": "en",
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("shopping_results", []):
                    link = item.get("link", "")
                    if link in seen:
                        continue
                    seen.add(link)

                    price_raw = item.get("price", "")
                    price_usd = self._parse_price(str(price_raw))

                    results.append({
                        "title": item.get("title", ""),
                        "url": link,
                        "image_url": item.get("thumbnail", ""),
                        "price_usd": price_usd,
                        "in_stock": True,
                        "source": "google_shopping",
                    })

                time.sleep(1)

            except Exception as e:
                self.logger.error(f"SerpAPI error '{query}': {e}")

        return results

    def _parse_price(self, text: str) -> float | None:
        import re
        text = text.replace(",", "").replace("$", "").strip()
        m = re.search(r"(\d+(?:\.\d{2})?)", text)
        return float(m.group(1)) if m else None
