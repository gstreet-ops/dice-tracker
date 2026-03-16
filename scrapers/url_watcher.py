"""
url_watcher.py — Fetches a single product URL and extracts title + price.
Used by run.py to track user-added URL sources.
"""
import re
import requests
from bs4 import BeautifulSoup
from .base import BaseScraper
import logging

logger = logging.getLogger("url_watcher")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


class UrlWatcherScraper(BaseScraper):
    source = "url_watcher"

    def __init__(self, url="", label=""):
        super().__init__()
        self.target_url = url
        self.label = label

    def fetch(self) -> list:
        if not self.target_url:
            return []

        try:
            resp = requests.get(self.target_url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            title = self._extract_title(soup)
            price = self._extract_price(soup)

            if not title:
                title = self.label or self.target_url

            return [{
                "title": title,
                "url": self.target_url,
                "image_url": "",
                "price_usd": price,
                "size_mm": None,
                "material": None,
                "pip_style": None,
                "in_stock": True,
                "source": "url_watcher",
                "score": 50,
                "watchlist_category": self.label or "URL Source",
            }]

        except Exception as e:
            self.logger.error(f"URL watcher fetch error for {self.target_url}: {e}")
            return []

    def _extract_title(self, soup):
        """Try common title selectors."""
        # og:title meta tag
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            return og["content"].strip()

        # h1
        h1 = soup.find("h1")
        if h1:
            text = h1.get_text(strip=True)
            if text:
                return text

        # <title> tag
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)

        return None

    def _extract_price(self, soup):
        """Try common price selectors."""
        selectors = [
            '[itemprop="price"]',
            '[data-price]',
            '.price',
            '.product-price',
            '[class*="price"]',
        ]

        for sel in selectors:
            el = soup.select_one(sel)
            if not el:
                continue

            # Check content attribute first (structured data)
            content = el.get("content") or el.get("data-price")
            if content:
                try:
                    return float(content)
                except ValueError:
                    pass

            # Parse text
            text = el.get_text(strip=True)
            m = re.search(r"[\$\£\€]?\s*(\d+(?:[,\.]\d{2,3})*(?:\.\d{2})?)", text)
            if m:
                price_str = m.group(1).replace(",", "")
                try:
                    return float(price_str)
                except ValueError:
                    pass

        return None
