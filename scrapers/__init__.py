# scrapers/__init__.py
from .chessex import ChessexScraper
from .ebay import EbayScraper
from .aliexpress import AliExpressScraper
from .google_shopping import GoogleShoppingScraper
from .thediceshoponline import TheDiceShopScraper
from .url_watcher import UrlWatcherScraper

__all__ = [
    "ChessexScraper",
    "EbayScraper",
    "AliExpressScraper",
    "GoogleShoppingScraper",
    "TheDiceShopScraper",
    "UrlWatcherScraper",
]
