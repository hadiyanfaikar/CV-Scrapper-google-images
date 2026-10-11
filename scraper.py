#!/usr/bin/env python3
"""
Google Images Scraper CLI
A modular, production-grade tool to search, collect, and download images for ML datasets.

Usage:
    python scraper.py --keywords "car,truck,motorcycle" --max-images 100
    python scraper.py --config config.yaml
    python scraper.py --keywords "kucing anggora" --engine google_api --api-key KEY --cx CX
"""

import sys
import time
from pathlib import Path
from typing import List

from src.config import ScraperConfig, get_arg_parser
from src.downloader.image_downloader import ImageDownloader
from src.metadata.manager import MetadataManager
from src.models import DownloadResult
from src.search.base import GoogleAntiBotException, SearchProviderException
from src.search.factory import create_searcher
from src.utils.logger import setup_logger
from src.validator.image_validator import ImageDeduplicator, ImageValidator


def main():
    parser = get_arg_parser()
    args = parser.parse_args()

    try:
        config = ScraperConfig.from_cli_args(args)
    except Exception as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)

    logger = setup_logger(output_dir=config.output_dir)
    logger.info("=" * 60)
    logger.info("Google Images Scraper v1.0.0 Started")
    logger.info(f"Target Keywords     : {config.keywords}")
    logger.info(f"Max Images / Keyword: {config.max_images_per_keyword}")
    logger.info(f"Search Engine       : {config.engine}")
    logger.info(f"Output Directory    : {Path(config.output_dir).resolve()}")
    logger.info(f"Min Dimensions      : {config.min_width}x{config.min_height}")
    logger.info(f"Allowed Formats     : {config.allowed_formats}")
    logger.info(f"Concurrency Workers : {config.max_workers}")
    logger.info("=" * 60)

    # Initialize Components
    validator = ImageValidator(
        min_width=config.min_width,
        min_height=config.min_height,
        allowed_formats=config.allowed_formats,
    )
    deduplicator = ImageDeduplicator()
    metadata_mgr = MetadataManager(output_dir=config.output_dir)

    try:
        searcher = create_searcher(config, logger)
    except SearchProviderException as e:
        logger.error(f"Initialization Error: {e}")
        sys.exit(1)

    downloader = ImageDownloader(
        config=config,
        validator=validator,
        deduplicator=deduplicator,
        metadata_manager=metadata_mgr,
        logger=logger,
    )

    all_results: List[DownloadResult] = []
    start_time = time.time()

    for idx, keyword in enumerate(config.keywords, 1):
        logger.info(f"\nProcessing keyword [{idx}/{len(config.keywords)}]: '{keyword}'")

        try:
            # Query candidates (fetch up to 2x target to compensate for filtered/corrupted images)
            fetch_target = max(config.max_images_per_keyword * 2, 10)
            candidates = searcher.search(keyword=keyword, max_results=fetch_target)

            if not candidates:
                logger.warning(f"No candidate images found for '{keyword}'.")
                continue

            results = downloader.download_keyword_candidates(
                keyword=keyword,
                candidates=candidates,
            )
            all_results.extend(results)

        except GoogleAntiBotException as e:
            logger.error("\n" + "!" * 60)
            logger.error("ANTI-BOT VERIFICATION ENCOUNTERED")
            logger.error(str(e))
            logger.error("!" * 60 + "\n")
            if len(config.keywords) == 1:
                sys.exit(2)
        except Exception as e:
            logger.error(f"Error processing keyword '{keyword}': {e}", exc_info=True)

        if idx < len(config.keywords):
            time.sleep(config.delay_between_requests)

    # Summarize Execution Statistics
    elapsed = time.time() - start_time
    success_count = sum(1 for r in all_results if r.download_status == "success")
    duplicate_count = sum(1 for r in all_results if r.download_status == "skipped_duplicate")
    failure_count = len(all_results) - success_count - duplicate_count

    logger.info("\n" + "=" * 60)
    logger.info("SCRAPING TASK SUMMARY")
    logger.info(f"Total Elapsed Time    : {elapsed:.2f} seconds")
    logger.info(f"Successfully Downloaded: {success_count} images")
    logger.info(f"Duplicates Skipped    : {duplicate_count} images")
    logger.info(f"Rejected / Failed     : {failure_count} images")
    logger.info(f"Dataset Output Path   : {Path(config.output_dir).resolve()}")
    logger.info(f"Metadata CSV File     : {metadata_mgr.csv_path.resolve()}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
