import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from pathlib import Path
import time
from typing import List, Optional
import urllib.parse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config import ScraperConfig
from src.metadata.manager import MetadataManager
from src.models import DownloadResult, ImageCandidate
from src.utils.helpers import ensure_directory, generate_filename, sanitize_keyword
from src.validator.image_validator import ImageDeduplicator, ImageValidator


class ImageDownloader:
    """
    Concurrent, resilient image downloader with:
    - Bounded thread pool concurrency
    - HTTP connection pooling & retries with exponential backoff
    - Content validation via Pillow
    - Content-hash deduplication
    - Structured directory & filename storage
    - Real-time metadata logging
    """

    def __init__(
        self,
        config: ScraperConfig,
        validator: ImageValidator,
        deduplicator: ImageDeduplicator,
        metadata_manager: MetadataManager,
        logger: Optional[logging.Logger] = None,
    ):
        self.config = config
        self.validator = validator
        self.deduplicator = deduplicator
        self.metadata_manager = metadata_manager
        self.logger = logger or logging.getLogger("GoogleImagesScraper")
        self.session = self._create_resilient_session()

    def _create_resilient_session(self) -> requests.Session:
        """Create a requests session with connection pooling and retry strategy."""
        session = requests.Session()
        retries = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(
            max_retries=retries,
            pool_connections=self.config.max_workers * 2,
            pool_maxsize=self.config.max_workers * 2,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({
            "User-Agent": (
                "GoogleImagesDatasetScraper/1.0 (Mozilla/5.0 Windows NT 10.0; Win64; x64; "
                "dataset-collector@domain.local)"
            ),
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        })
        return session

    def download_keyword_candidates(
        self,
        keyword: str,
        candidates: List[ImageCandidate],
    ) -> List[DownloadResult]:
        """
        Download up to max_images_per_keyword candidates for a keyword using a thread pool.
        """
        clean_kw = sanitize_keyword(keyword)
        kw_images_dir = Path(self.config.output_dir) / "images" / clean_kw
        ensure_directory(kw_images_dir)

        results: List[DownloadResult] = []
        success_count = 0
        target_count = self.config.max_images_per_keyword

        self.logger.info(
            f"Starting download for keyword '{keyword}' (Found {len(candidates)} candidates, target: {target_count})"
        )

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_index = {
                executor.submit(
                    self._download_single_candidate,
                    candidate,
                    idx + 1,
                    kw_images_dir,
                ): idx
                for idx, candidate in enumerate(candidates)
            }

            for future in as_completed(future_to_index):
                try:
                    res = future.result()
                    results.append(res)
                    self.metadata_manager.record_result(res)

                    if res.download_status == "success":
                        success_count += 1
                        self.logger.info(
                            f"[{keyword}] [{success_count}/{target_count}] Downloaded: {res.filename} "
                            f"({res.width}x{res.height}, {res.format}, {res.file_size} bytes)"
                        )

                    if success_count >= target_count:
                        self.logger.info(
                            f"Reached target image count ({target_count}) for keyword '{keyword}'. Cancelling remaining downloads."
                        )
                        # Cancel remaining futures
                        for pending in future_to_index:
                            pending.cancel()
                        break

                except Exception as e:
                    self.logger.error(f"Unexpected error in download worker: {e}", exc_info=True)

        self.logger.info(
            f"Completed keyword '{keyword}': {success_count}/{target_count} successfully downloaded."
        )
        return results

    def _download_single_candidate(
        self,
        candidate: ImageCandidate,
        index: int,
        target_dir: Path,
    ) -> DownloadResult:
        """
        Download, validate, deduplicate, and persist a single candidate.
        """
        url = candidate.image_url.strip()
        raw_bytes: Optional[bytes] = None
        error_msg: Optional[str] = None
        status: str = "failed"

        # Check for empty URL
        if not url:
            return DownloadResult(
                filename="",
                keyword=candidate.keyword,
                image_url=url,
                source_url=candidate.source_url,
                download_status="failed_empty_url",
                error_message="Empty image URL",
            )

        # Handle data: URLs (base64 encoded images)
        if url.startswith("data:image/"):
            try:
                header, b64_data = url.split(",", 1)
                raw_bytes = base64.b64decode(b64_data)
            except Exception as e:
                return DownloadResult(
                    filename="",
                    keyword=candidate.keyword,
                    image_url=url[:50] + "...",
                    source_url=candidate.source_url,
                    download_status="failed_data_url_decode",
                    error_message=str(e),
                )
        else:
            # Handle standard HTTP/HTTPS URLs
            try:
                parsed = urllib.parse.urlparse(url)
                if not parsed.scheme or not parsed.netloc:
                    return DownloadResult(
                        filename="",
                        keyword=candidate.keyword,
                        image_url=url,
                        source_url=candidate.source_url,
                        download_status="failed_invalid_url",
                        error_message="Malformed URL scheme or netloc",
                    )

                headers = {}
                if candidate.source_url:
                    headers["Referer"] = candidate.source_url

                resp = self.session.get(
                    url,
                    headers=headers,
                    timeout=self.config.timeout,
                    stream=True,
                )

                if resp.status_code != 200:
                    return DownloadResult(
                        filename="",
                        keyword=candidate.keyword,
                        image_url=url,
                        source_url=candidate.source_url,
                        download_status=f"failed_http_{resp.status_code}",
                        error_message=f"HTTP {resp.status_code}: {resp.reason}",
                    )

                raw_bytes = resp.content

            except requests.exceptions.Timeout as e:
                return DownloadResult(
                    filename="",
                    keyword=candidate.keyword,
                    image_url=url,
                    source_url=candidate.source_url,
                    download_status="failed_timeout",
                    error_message=str(e),
                )
            except requests.exceptions.RequestException as e:
                return DownloadResult(
                    filename="",
                    keyword=candidate.keyword,
                    image_url=url,
                    source_url=candidate.source_url,
                    download_status="failed_network_error",
                    error_message=str(e),
                )
            except Exception as e:
                return DownloadResult(
                    filename="",
                    keyword=candidate.keyword,
                    image_url=url,
                    source_url=candidate.source_url,
                    download_status="failed_download",
                    error_message=str(e),
                )

        # Validate image content
        val = self.validator.validate(raw_bytes)
        if not val.is_valid:
            status_code = f"failed_validation_{val.error_reason.split(':')[0].strip()}"
            return DownloadResult(
                filename="",
                keyword=candidate.keyword,
                image_url=url,
                source_url=candidate.source_url,
                width=val.width or None,
                height=val.height or None,
                format=val.format,
                file_size=val.file_size or None,
                download_status=status_code,
                error_message=val.error_reason,
            )

        # Check deduplication
        is_new = self.deduplicator.register(val.content_hash)
        if not is_new:
            self.logger.debug(
                f"Skipping duplicate image (hash {val.content_hash[:8]}) from {url}"
            )
            return DownloadResult(
                filename="",
                keyword=candidate.keyword,
                image_url=url,
                source_url=candidate.source_url,
                width=val.width,
                height=val.height,
                format=val.format,
                file_size=val.file_size,
                download_status="skipped_duplicate",
                error_message="Duplicate content hash detected",
            )

        # Generate unique structured filename
        ext = val.format.lower()
        if ext == "jpeg":
            ext = "jpg"
        filename = generate_filename(
            keyword=candidate.keyword,
            index=index,
            content_hash=val.content_hash,
            ext=ext,
        )
        local_path = target_dir / filename

        # Save to disk
        try:
            with open(local_path, "wb") as f:
                f.write(raw_bytes)

            return DownloadResult(
                filename=filename,
                keyword=candidate.keyword,
                image_url=url,
                source_url=candidate.source_url,
                width=val.width,
                height=val.height,
                format=val.format,
                file_size=val.file_size,
                download_status="success",
                local_path=str(local_path),
            )
        except Exception as e:
            return DownloadResult(
                filename=filename,
                keyword=candidate.keyword,
                image_url=url,
                source_url=candidate.source_url,
                width=val.width,
                height=val.height,
                format=val.format,
                file_size=val.file_size,
                download_status="failed_disk_write",
                error_message=str(e),
            )
