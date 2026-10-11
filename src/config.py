import argparse
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import yaml


@dataclass
class ScraperConfig:
    """Configuration schema for Google Images Scraper."""
    keywords: List[str] = field(default_factory=lambda: ["sports car"])
    max_images_per_keyword: int = 20
    output_dir: str = "google_images_dataset"
    min_width: int = 150
    min_height: int = 150
    allowed_formats: List[str] = field(default_factory=lambda: ["JPEG", "JPG", "PNG", "WEBP", "AVIF"])
    timeout: float = 15.0
    max_retries: int = 3
    retry_delay: float = 2.0
    max_workers: int = 5
    delay_between_requests: float = 1.0

    # Engine & Browser automation settings
    engine: str = "google_browser"  # "google_browser", "google_api", or "commons"
    headless: bool = True
    browser_type: str = "firefox"  # "firefox" or "chromium"
    viewport_width: int = 1920
    viewport_height: int = 1080
    scroll_delay: float = 1.5
    max_scroll_attempts: int = 10
    extract_original_timeout: float = 8.0

    # Google Custom Search API credentials (optional, fallback from env)
    google_api_key: str = ""
    google_cx: str = ""

    def __post_init__(self):
        # Normalize allowed formats to uppercase
        self.allowed_formats = [fmt.upper().lstrip(".") for fmt in self.allowed_formats]
        # Include JPEG if JPG is present and vice-versa for Pillow compatibility
        if "JPG" in self.allowed_formats and "JPEG" not in self.allowed_formats:
            self.allowed_formats.append("JPEG")
        if "JPEG" in self.allowed_formats and "JPG" not in self.allowed_formats:
            self.allowed_formats.append("JPG")

        # Resolve API keys from environment if empty
        if not self.google_api_key:
            self.google_api_key = os.getenv("GOOGLE_API_KEY", "")
        if not self.google_cx:
            self.google_cx = os.getenv("GOOGLE_CX", "")

        # Sanity validation
        if self.max_images_per_keyword <= 0:
            raise ValueError("max_images_per_keyword must be greater than 0")
        if self.min_width < 0 or self.min_height < 0:
            raise ValueError("min_width and min_height must be non-negative")
        if self.timeout <= 0:
            raise ValueError("timeout must be greater than 0")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if self.max_workers <= 0:
            raise ValueError("max_workers must be greater than 0")

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "ScraperConfig":
        """Load configuration from a YAML file."""
        path = Path(yaml_path)
        if not path.is_file():
            raise FileNotFoundError(f"Config file not found: {yaml_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Filter valid fields
        valid_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in valid_fields and v is not None}
        return cls(**filtered)

    @classmethod
    def from_cli_args(cls, args: Optional[argparse.Namespace] = None) -> "ScraperConfig":
        """
        Create configuration combining YAML config file (if provided) and CLI overrides.
        """
        if args is None:
            parser = get_arg_parser()
            args = parser.parse_args()

        # Start with base config from YAML if specified, otherwise default
        config_file = getattr(args, "config", None)
        if config_file and Path(config_file).exists():
            cfg = cls.from_yaml(config_file)
        else:
            cfg = cls()

        # CLI overrides
        if getattr(args, "keywords", None):
            # Parse comma-separated keywords
            raw_kws = args.keywords
            if isinstance(raw_kws, str):
                keywords = [k.strip() for k in raw_kws.split(",") if k.strip()]
            else:
                keywords = list(raw_kws)
            if keywords:
                cfg.keywords = keywords

        if getattr(args, "max_images", None) is not None:
            cfg.max_images_per_keyword = args.max_images

        if getattr(args, "output_dir", None):
            cfg.output_dir = args.output_dir

        if getattr(args, "min_width", None) is not None:
            cfg.min_width = args.min_width

        if getattr(args, "min_height", None) is not None:
            cfg.min_height = args.min_height

        if getattr(args, "allowed_formats", None):
            formats = [f.strip().upper() for f in args.allowed_formats.split(",") if f.strip()]
            if formats:
                cfg.allowed_formats = formats

        if getattr(args, "timeout", None) is not None:
            cfg.timeout = args.timeout

        if getattr(args, "max_retries", None) is not None:
            cfg.max_retries = args.max_retries

        if getattr(args, "engine", None):
            cfg.engine = args.engine

        if getattr(args, "headless", None) is not None:
            cfg.headless = args.headless

        if getattr(args, "browser_type", None):
            cfg.browser_type = args.browser_type

        if getattr(args, "max_workers", None) is not None:
            cfg.max_workers = args.max_workers

        if getattr(args, "delay", None) is not None:
            cfg.delay_between_requests = args.delay

        if getattr(args, "api_key", None):
            cfg.google_api_key = args.api_key

        if getattr(args, "cx", None):
            cfg.google_cx = args.cx

        # Re-run post-init validation
        cfg.__post_init__()
        return cfg


def get_arg_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="scraper.py",
        description="Google Images Scraper for Machine Learning & Computer Vision Datasets.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--keywords",
        type=str,
        help="Comma-separated keywords (e.g. 'car,truck,motorcycle' or 'kucing anggora,anjing')",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        dest="max_images",
        help="Maximum images to download per keyword",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Root output directory for images, metadata, and logs",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--min-width",
        type=int,
        help="Minimum image width filter in pixels",
    )
    parser.add_argument(
        "--min-height",
        type=int,
        help="Minimum image height filter in pixels",
    )
    parser.add_argument(
        "--allowed-formats",
        type=str,
        help="Comma-separated allowed formats (e.g. 'JPEG,PNG,WEBP')",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        help="Request timeout in seconds",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        help="Maximum retry attempts on failed downloads",
    )
    parser.add_argument(
        "--engine",
        type=str,
        choices=["google", "google_browser", "google_api", "bing", "commons"],
        help="Scraper engine: 'google'/'google_browser' (Playwright), 'google_api' (Official API), 'bing', 'commons'",
    )
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Run browser in headless mode (--headless or --no-headless)",
    )
    parser.add_argument(
        "--browser-type",
        type=str,
        choices=["firefox", "chromium"],
        help="Browser automation engine (Playwright)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        help="Maximum concurrent worker threads for downloading",
    )
    parser.add_argument(
        "--delay",
        type=float,
        help="Delay between search operations in seconds",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="Google Custom Search JSON API Key",
    )
    parser.add_argument(
        "--cx",
        type=str,
        help="Google Custom Search Engine ID (CX)",
    )
    return parser
