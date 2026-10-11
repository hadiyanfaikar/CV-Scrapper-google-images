import argparse
from pathlib import Path
import pytest

from src.config import ScraperConfig


class TestConfig:
    """Test suite for configuration loading, CLI args, and validations."""

    def test_default_config(self):
        cfg = ScraperConfig()
        assert cfg.max_images_per_keyword == 20
        assert "JPEG" in cfg.allowed_formats
        assert "PNG" in cfg.allowed_formats
        assert cfg.min_width == 150
        assert cfg.min_height == 150

    def test_invalid_max_images(self):
        with pytest.raises(ValueError, match="max_images_per_keyword"):
            ScraperConfig(max_images_per_keyword=0)

    def test_invalid_dimensions(self):
        with pytest.raises(ValueError, match="min_width"):
            ScraperConfig(min_width=-10)

    def test_cli_override(self, tmp_path):
        # Create a sample YAML config
        yaml_content = """
keywords:
  - "apple"
max_images_per_keyword: 10
output_dir: "custom_dir"
"""
        cfg_file = tmp_path / "test_config.yaml"
        cfg_file.write_text(yaml_content)

        # Simulate CLI arguments overriding YAML
        args = argparse.Namespace(
            config=str(cfg_file),
            keywords="banana,orange",
            max_images=50,
            output_dir=None,
            min_width=300,
            min_height=300,
            allowed_formats="WEBP",
            timeout=25.0,
            max_retries=5,
            engine="google_api",
            headless=False,
            browser_type="firefox",
            max_workers=8,
            delay=2.0,
            api_key="TEST_KEY",
            cx="TEST_CX",
        )

        cfg = ScraperConfig.from_cli_args(args)
        assert cfg.keywords == ["banana", "orange"]
        assert cfg.max_images_per_keyword == 50
        assert cfg.output_dir == "custom_dir"  # Retained from YAML because CLI was None
        assert cfg.min_width == 300
        assert "WEBP" in cfg.allowed_formats
        assert cfg.engine == "google_api"
        assert cfg.google_api_key == "TEST_KEY"
        assert cfg.google_cx == "TEST_CX"
