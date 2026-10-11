import logging
from typing import Optional

from src.config import ScraperConfig
from src.search.base import BaseImageSearcher, SearchProviderException
from src.search.bing_searcher import BingImageSearcher
from src.search.browser_searcher import GoogleImagesBrowserSearcher
from src.search.google_api import GoogleCustomSearchApiSearcher
from src.search.open_commons import WikimediaCommonsSearcher


def create_searcher(
    config: ScraperConfig,
    logger: Optional[logging.Logger] = None,
) -> BaseImageSearcher:
    """
    Factory function instantiating the requested image search provider.

    Options:
    - 'google_browser': Playwright automated browser for Google Images (Default for browser scraping)
    - 'google_api': Official Google Custom Search JSON API (Recommended for production & zero-CAPTCHA stability)
    - 'bing': High-res search engine scraper (Works reliably without IP CAPTCHA bans)
    - 'commons': Wikimedia Commons Open Image API (Fallback/Testing)
    """
    engine_name = config.engine.lower().strip()

    if engine_name in ("google", "google_browser"):
        return GoogleImagesBrowserSearcher(config, logger)
    elif engine_name == "google_api":
        return GoogleCustomSearchApiSearcher(config, logger)
    elif engine_name == "bing":
        return BingImageSearcher(config, logger)
    elif engine_name in ("commons", "wikimedia"):
        return WikimediaCommonsSearcher(config, logger)
    else:
        raise SearchProviderException(
            f"Unsupported engine '{config.engine}'. Available choices: 'google_browser', 'google_api', 'bing', 'commons'"
        )
