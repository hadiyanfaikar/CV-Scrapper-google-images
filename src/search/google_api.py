import logging
import math
from typing import List, Optional
import requests

from src.config import ScraperConfig
from src.models import ImageCandidate
from src.search.base import BaseImageSearcher, SearchProviderException


class GoogleCustomSearchApiSearcher(BaseImageSearcher):
    """
    Search provider using the official Google Custom Search JSON API.
    Provides 100% stable, compliant, and rich image metadata without CAPTCHA or DOM fragility.
    """

    ENDPOINT = "https://customsearch.googleapis.com/v1"

    def __init__(self, config: ScraperConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger("GoogleImagesScraper")

        if not self.config.google_api_key or not self.config.google_cx:
            raise SearchProviderException(
                "Google Custom Search API requires both 'google_api_key' and 'google_cx' (Search Engine ID).\n"
                "Please configure them in config.yaml, via CLI arguments (--api-key and --cx), "
                "or environment variables GOOGLE_API_KEY and GOOGLE_CX."
            )

    def search(self, keyword: str, max_results: int) -> List[ImageCandidate]:
        """
        Query the Google Custom Search API in batches of 10 results.
        """
        self.logger.info(f"Querying Google Custom Search API for keyword: '{keyword}' (target: {max_results})")
        candidates: List[ImageCandidate] = []
        page_size = 10
        total_pages = math.ceil(max_results / page_size)

        for page_idx in range(total_pages):
            start_index = (page_idx * page_size) + 1
            if start_index > 91:  # Google Custom Search API caps at 100 results per query
                self.logger.warning("Google Custom Search API supports up to 100 results per keyword query.")
                break

            params = {
                "key": self.config.google_api_key,
                "cx": self.config.google_cx,
                "q": keyword,
                "searchType": "image",
                "num": min(page_size, max_results - len(candidates)),
                "start": start_index,
            }

            try:
                resp = requests.get(self.ENDPOINT, params=params, timeout=self.config.timeout)
                if resp.status_code != 200:
                    err_msg = resp.text
                    try:
                        err_json = resp.json()
                        err_msg = err_json.get("error", {}).get("message", err_msg)
                    except Exception:
                        pass
                    raise SearchProviderException(f"Google API Error HTTP {resp.status_code}: {err_msg}")

                data = resp.json()
                items = data.get("items", [])
                if not items:
                    self.logger.info(f"No further results returned for keyword '{keyword}'.")
                    break

                for item in items:
                    img_data = item.get("image", {})
                    candidates.append(
                        ImageCandidate(
                            keyword=keyword,
                            image_url=item.get("link", ""),
                            source_url=img_data.get("contextLink", ""),
                            title=item.get("title", ""),
                            thumbnail_url=img_data.get("thumbnailLink", ""),
                            estimated_width=img_data.get("width"),
                            estimated_height=img_data.get("height"),
                            format_hint=item.get("fileFormat", ""),
                        )
                    )
                    if len(candidates) >= max_results:
                        break

            except requests.exceptions.RequestException as e:
                raise SearchProviderException(f"Network error querying Google Custom Search API: {e}")

        self.logger.info(f"Google API returned {len(candidates)} image candidates for '{keyword}'.")
        return candidates
