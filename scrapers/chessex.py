"""
chessex.py — Scraper for Chessex 50mm d6 dice.
Target: https://www.chessex.com/50mm-loose-dice-d6-large-pips
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
    )
}

CHESSEX_50MM_URL = "https://www.chessex.com/50mm-loose-dice-d6-large-pips"


class ChessexScraper(BaseScraper):
    source = "chessex"

    def fetch(self) -> list[dict]:
        results = []
        try:
            resp = requests.get(CHESSEX_50MM_URL, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            products = soup.select(".product-item, .product_item, article.product")

            if not products:
                # Fallback: try generic product grid selectors
                products = soup.select("[class*='product']")

            self.logger.info(f"Chessex: found {len(products)} product elements")

            for p in products:
                title_el = p.select_one("h2, h3, .product-title, .product-name, a")
                price_el = p.select_one(".price, .product-price, [class*='price']")
                link_el = p.select_one("a[href]")
                img_el = p.select_one("img")

                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                if not title or len(title) < 3:
                    continue

                price_text = price_el.get_text(strip=True) if price_el else ""
                price_usd = self._parse_price(price_text)

                href = link_el["href"] if link_el else ""
                if href and not href.startswith("http"):
                    href = "https://www.chessex.com" + href

                img_url = img_el.get("src", "") if img_el else ""

                # Chessex 50mm are all solid resin, engraved pips
                results.append({
                    "title": f"Chessex {title} 50mm d6",
                    "url": href or CHESSEX_50MM_URL + "#" + title[:20],
                    "image_url": img_url,
                    "price_usd": price_usd,
                    "size_mm": 50.0,
                    "material": "resin",
                    "pip_style": "engraved",
                    "in_stock": True,
                    "source": "chessex",
                })
                time.sleep(0.5)

        except Exception as e:
            self.logger.error(f"Chessex fetch error: {e}")

        # Always include the known gold variant as a tracked item
        results.append({
            "title": "Chessex Lustrous Gold/Silver 50mm d6",
            "url": "https://www.chessex.com/lustrous-50mm-wpips-goldsilver-d6",
            "image_url": "",
            "price_usd": 19.98,
            "size_mm": 50.0,
            "material": "resin",
            "finish": "gold",
            "pip_style": "engraved",
            "set_count": 1,
            "in_stock": True,
            "source": "chessex",
        })

        return results

    def _parse_price(self, text: str) -> float | None:
        import re
        m = re.search(r"[\$]?\s*(\d+(?:\.\d{2})?)", text.replace(",", ""))
        return float(m.group(1)) if m else None
