import json
import logging
import re
from typing import List, Optional
import urllib.parse
import requests

from src.config import ScraperConfig
from src.models import ImageCandidate
from src.search.base import BaseImageSearcher, SearchProviderException


class BingImageSearcher(BaseImageSearcher):
    """
    Image search provider scraping Bing Images.
    Extracts original high-resolution image URLs without strict CAPTCHA restrictions.
    """

    SEARCH_URL = "https://www.bing.com/images/async"

    def __init__(self, config: ScraperConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger("GoogleImagesScraper")

    def search(self, keyword: str, max_results: int) -> List[ImageCandidate]:
        self.logger.info(f"Querying Bing Images for keyword: '{keyword}' (target: {max_results})")
        candidates: List[ImageCandidate] = []
        encoded_kw = urllib.parse.quote_plus(keyword)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }

        first = 1
        max_limit = max_results * 2  # Ambil cadangan untuk mengantisipasi gambar rusak / format tak cocok

        while len(candidates) < max_limit and first <= 1000:
            url = f"{self.SEARCH_URL}?q={encoded_kw}&first={first}&count=35&mmasync=1"
            try:
                resp = requests.get(url, headers=headers, timeout=self.config.timeout)
                if resp.status_code != 200:
                    raise SearchProviderException(f"Bing returned HTTP {resp.status_code}")

                matches = re.findall(
                    r'&quot;murl&quot;:&quot;(https?://[^\&]+)&quot;.*?&quot;purl&quot;:&quot;(https?://[^\&]+)&quot;',
                    resp.text,
                )

                if not matches:
                    murls = re.findall(r'&quot;murl&quot;:&quot;(https?://[^\&]+)&quot;', resp.text)
                    matches = [(u, "") for u in murls]

                if not matches:
                    break

                prev_len = len(candidates)
                for img_url, source_url in matches:
                    if not any(c.image_url == img_url for c in candidates):
                        candidates.append(
                            ImageCandidate(
                                keyword=keyword,
                                image_url=img_url,
                                source_url=source_url,
                                title=keyword,
                            )
                        )
                        if len(candidates) >= max_limit:
                            break

                if len(candidates) == prev_len:
                    break

                first += 35

            except Exception as e:
                self.logger.error(f"Error querying Bing Images at offset {first}: {e}")
                break

        self.logger.info(f"Bing Images found {len(candidates)} candidates for '{keyword}'.")
        return candidates
