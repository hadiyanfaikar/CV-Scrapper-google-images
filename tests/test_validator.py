import io
import pytest
from PIL import Image

from src.validator.image_validator import ImageValidator


def create_dummy_image_bytes(width: int, height: int, fmt: str = "JPEG") -> bytes:
    """Helper creating valid in-memory image bytes."""
    mode = "RGB" if fmt.upper() in ("JPEG", "JPG") else "RGBA"
    fill_color = (120, 200, 255) if mode == "RGB" else (120, 200, 255, 255)
    img = Image.new(mode, (width, height), color=fill_color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


class TestImageValidator:
    """Test suite for image content validation."""

    def test_valid_image(self):
        validator = ImageValidator(min_width=100, min_height=100, allowed_formats=["JPEG", "PNG"])
        raw_bytes = create_dummy_image_bytes(200, 200, fmt="JPEG")
        result = validator.validate(raw_bytes)

        assert result.is_valid is True
        assert result.width == 200
        assert result.height == 200
        assert result.format in ("JPEG", "JPG")
        assert len(result.content_hash) == 64
        assert result.file_size == len(raw_bytes)
        assert result.error_reason == ""

    def test_below_minimum_dimensions(self):
        validator = ImageValidator(min_width=300, min_height=300, allowed_formats=["PNG"])
        raw_bytes = create_dummy_image_bytes(150, 250, fmt="PNG")
        result = validator.validate(raw_bytes)

        assert result.is_valid is False
        assert "below_minimum" in result.error_reason
        assert result.width == 150
        assert result.height == 250

    def test_disallowed_format(self):
        validator = ImageValidator(min_width=50, min_height=50, allowed_formats=["PNG"])
        # Generate JPEG instead
        raw_bytes = create_dummy_image_bytes(100, 100, fmt="JPEG")
        result = validator.validate(raw_bytes)

        assert result.is_valid is False
        assert "not_allowed" in result.error_reason
        assert result.format == "JPEG"

    def test_corrupted_image_bytes(self):
        validator = ImageValidator(min_width=50, min_height=50)
        corrupted_bytes = b"\xff\xd8\xff\xe0" + b"random invalid corrupted data 1234567890" * 10
        result = validator.validate(corrupted_bytes)

        assert result.is_valid is False
        assert "corrupted_or_invalid_image" in result.error_reason

    def test_empty_or_too_small_payload(self):
        validator = ImageValidator()
        result_empty = validator.validate(b"")
        assert result_empty.is_valid is False
        assert result_empty.error_reason == "empty_or_too_small_payload"

        result_tiny = validator.validate(b"short bytes")
        assert result_tiny.is_valid is False
        assert result_tiny.error_reason == "empty_or_too_small_payload"

    def test_webp_support(self):
        validator = ImageValidator(min_width=100, min_height=100, allowed_formats=["WEBP"])
        raw_bytes = create_dummy_image_bytes(120, 120, fmt="WEBP")
        result = validator.validate(raw_bytes)

        assert result.is_valid is True
        assert result.format == "WEBP"
