"""
aliexpress.py — AliExpress scraper for premium gold dice.
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

SEARCHES = [
    "50mm gold metal dice d6",
    "jumbo gold dice engraved pips",
    "large brass zinc alloy dice",
]


class AliExpressScraper(BaseScraper):
    source = "aliexpress"

    def fetch(self) -> list[dict]:
        results = []
        seen = set()

        for query in SEARCHES:
            try:
                url = (
                    f"https://www.aliexpress.com/wholesale"
                    f"?SearchText={query.replace(' ', '+')}"
                    f"&SortType=total_tranpro_desc"
                )
                resp = requests.get(url, headers=HEADERS, timeout=20)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")

                items = soup.select(
                    "[class*='manhattan--container'],"
                    "[class*='product-snippet'],"
                    "div[ae_object_value]"
                )
                self.logger.info(f"AliExpress '{query}': {len(items)} items")

                for item in items[:15]:
                    title_el = item.select_one(
                        "[class*='title'], h3, [class*='product-title']"
                    )
                    price_el = item.select_one(
                        "[class*='price'], [class*='Price']"
                    )
                    link_el = item.select_one("a[href]")

                    if not title_el or not link_el:
                        continue

                    title = title_el.get_text(strip=True)
                    href = link_el.get("href", "")
                    if not href.startswith("http"):
                        href = "https:" + href
                    href = href.split("?")[0]

                    if href in seen:
                        continue
                    seen.add(href)

                    price_text = price_el.get_text(strip=True) if price_el else ""
                    price_usd = self._parse_price(price_text)

                    results.append({
                        "title": title,
                        "url": href,
                        "price_usd": price_usd,
                        "in_stock": True,
                        "source": "aliexpress",
                    })

                time.sleep(self.delay_seconds)

            except Exception as e:
                self.logger.error(f"AliExpress error '{query}': {e}")

        return results

    def _parse_price(self, text: str) -> float | None:
        import re
        text = text.replace(",", "").strip()
        m = re.search(r"[\$US]?\s*(\d+(?:\.\d{2})?)", text)
        return float(m.group(1)) if m else None
