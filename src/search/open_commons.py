import logging
import math
from typing import List, Optional
import requests

from src.config import ScraperConfig
from src.models import ImageCandidate
from src.search.base import BaseImageSearcher, SearchProviderException


class WikimediaCommonsSearcher(BaseImageSearcher):
    """
    Open Wikimedia Commons image search provider.
    Enables instant offline/local testing and demonstration of the download,
    validation, deduplication, and metadata pipeline without requiring API keys
    or encountering CAPTCHA hurdles.
    """

    ENDPOINT = "https://commons.wikimedia.org/w/api.php"

    def __init__(self, config: ScraperConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger("GoogleImagesScraper")

    def search(self, keyword: str, max_results: int) -> List[ImageCandidate]:
        """Query Wikimedia Commons API for images."""
        self.logger.info(f"Querying Wikimedia Commons for keyword: '{keyword}' (target: {max_results})")
        candidates: List[ImageCandidate] = []
        batch_size = min(max_results, 50)

        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": keyword,
            "gsrnamespace": 6,  # File namespace
            "gsrlimit": batch_size,
            "prop": "imageinfo",
            "iiprop": "url|size|mime",
            "iiurlwidth": 1280,
            "format": "json",
        }
        headers = {
            "User-Agent": "GoogleImagesDatasetScraper/1.0 (research-dataset@example.com)",
        }

        try:
            resp = requests.get(self.ENDPOINT, params=params, headers=headers, timeout=self.config.timeout)
            if resp.status_code != 200:
                raise SearchProviderException(f"Wikimedia API returned HTTP {resp.status_code}")

            data = resp.json()
            pages = data.get("query", {}).get("pages", {})

            for page_id, page in pages.items():
                imageinfo_list = page.get("imageinfo", [])
                if not imageinfo_list:
                    continue
                info = imageinfo_list[0]
                img_url = info.get("thumburl") or info.get("url")
                if not img_url:
                    continue

                candidates.append(
                    ImageCandidate(
                        keyword=keyword,
                        image_url=img_url,
                        source_url=info.get("descriptionurl", f"https://commons.wikimedia.org/?curid={page_id}"),
                        title=page.get("title", ""),
                        estimated_width=info.get("width"),
                        estimated_height=info.get("height"),
                        format_hint=info.get("mime", ""),
                    )
                )

                if len(candidates) >= max_results:
                    break

        except requests.exceptions.RequestException as e:
            raise SearchProviderException(f"Network error querying Wikimedia API: {e}")

        self.logger.info(f"Wikimedia Commons returned {len(candidates)} candidates for '{keyword}'.")
        return candidates
