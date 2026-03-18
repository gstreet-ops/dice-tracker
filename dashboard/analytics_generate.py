"""
analytics_generate.py - Analytics is now a static HTML page that reads
directly from Supabase. This module exists for backwards compatibility
with scrapers/run.py — it simply ensures analytics.html is in place.
"""
import os
import shutil
import logging

logger = logging.getLogger("analytics")

STATIC_PATH = os.path.join(os.path.dirname(__file__), "analytics.html")


def generate_analytics():
    if os.path.exists(STATIC_PATH):
        logger.info("analytics.html is static — nothing to generate")
    else:
        logger.warning("analytics.html not found in dashboard/")
