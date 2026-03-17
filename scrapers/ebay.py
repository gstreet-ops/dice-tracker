"""
ebay.py — eBay worldwide scraper using the official Browse API.
Uses Client Credentials (OAuth 2.0) for application-level access.
"""
import os
import time
import base64
import logging
import requests
from .base import BaseScraper

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

CURRENCY_TO_USD = {
    "USD": 1.0,
    "GBP": 1.27,
    "EUR": 1.09,
    "AUD": 0.65,
    "CAD": 0.74,
}

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"


class EbayScraper(BaseScraper):
    source = "ebay"

    def __init__(self):
        super().__init__()
        self._token = None
        self._client_id = os.environ.get("EBAY_CLIENT_ID", "")
        self._client_secret = os.environ.get("EBAY_CLIENT_SECRET", "")

    def _get_token(self) -> str:
        """Get OAuth token, using cached value if available."""
        if self._token:
            return self._token

        if not self._client_id or not self._client_secret:
            raise RuntimeError("EBAY_CLIENT_ID and EBAY_CLIENT_SECRET must be set")

        credentials = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode()
        ).decode()

        resp = requests.post(
            TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {credentials}",
            },
            data={
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope",
            },
            timeout=15,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def fetch(self) -> list[dict]:
        results = []
        seen_urls = set()

        try:
            token = self._get_token()
        except Exception as e:
            self.logger.warning(f"eBay API auth failed: {e}")
            return []

        searches = getattr(self, "override_keywords", None) or EBAY_SEARCHES
        for query in searches:
            try:
                resp = requests.get(
                    SEARCH_URL,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
                    },
                    params={
                        "q": query,
                        "limit": 50,
                        "filter": "buyingOptions:{FIXED_PRICE}",
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                items = data.get("itemSummaries", [])
                self.logger.info(f"eBay '{query}': {len(items)} results")

                for item in items:
                    url = item.get("itemWebUrl", "")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)

                    title = item.get("title", "")
                    price_info = item.get("price", {})
                    currency = price_info.get("currency", "USD")
                    price_raw = float(price_info.get("value", 0)) if price_info.get("value") else None

                    price_usd = None
                    if price_raw is not None:
                        rate = CURRENCY_TO_USD.get(currency, 1.0)
                        price_usd = round(price_raw * rate, 2)

                    image = item.get("image", {})
                    img_url = image.get("imageUrl", "") if image else ""

                    results.append({
                        "title": title,
                        "url": url,
                        "image_url": img_url,
                        "price_usd": price_usd,
                        "price_orig": price_raw,
                        "currency": currency,
                        "size_mm": None,
                        "in_stock": True,
                        "source": "ebay",
                    })

                time.sleep(self.delay_seconds)

            except Exception as e:
                self.logger.warning(f"eBay API error for '{query}': {e}")

        return results
