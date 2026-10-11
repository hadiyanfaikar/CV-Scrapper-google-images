import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    output_dir: str | Path = "google_images_dataset",
    log_filename: str = "scraper.log",
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Setup centralized logger that outputs to both console and a log file
    under <output_dir>/logs/<log_filename>.
    """
    logger = logging.getLogger("GoogleImagesScraper")
    logger.setLevel(level)

    # Avoid duplicate handlers if setup is called multiple times
    if logger.handlers:
        return logger

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File Handler
    try:
        log_dir = Path(output_dir) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / log_filename

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_format = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning("Failed to initialize file logger at %s: %s", output_dir, e)

    return logger
