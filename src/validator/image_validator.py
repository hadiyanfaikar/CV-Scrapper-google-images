import io
import threading
from typing import List, Optional, Set
from PIL import Image, UnidentifiedImageError

from src.models import ImageValidationResult
from src.utils.helpers import calculate_content_hash


class ImageValidator:
    """
    Validates downloaded image data using Pillow:
    - Integrity verification (not corrupted)
    - Minimum width & height enforcement
    - Allowed image formats enforcement
    - SHA-256 content hashing
    """

    def __init__(
        self,
        min_width: int = 150,
        min_height: int = 150,
        allowed_formats: Optional[List[str]] = None,
    ):
        self.min_width = min_width
        self.min_height = min_height
        self.allowed_formats = (
            [fmt.upper() for fmt in allowed_formats]
            if allowed_formats
            else ["JPEG", "JPG", "PNG", "WEBP"]
        )
        if "JPG" in self.allowed_formats and "JPEG" not in self.allowed_formats:
            self.allowed_formats.append("JPEG")
        if "JPEG" in self.allowed_formats and "JPG" not in self.allowed_formats:
            self.allowed_formats.append("JPG")

    def validate(self, raw_bytes: bytes) -> ImageValidationResult:
        """
        Validate image content bytes and extract metadata.
        """
        if not raw_bytes or len(raw_bytes) < 32:
            return ImageValidationResult(
                is_valid=False,
                error_reason="empty_or_too_small_payload",
                file_size=len(raw_bytes) if raw_bytes else 0,
            )

        file_size = len(raw_bytes)
        content_hash = calculate_content_hash(raw_bytes)

        try:
            # First pass: verify image integrity
            stream = io.BytesIO(raw_bytes)
            img = Image.open(stream)
            img_format = (img.format or "").upper()
            width, height = img.size
            img.verify()

            # Pillow verify() requires re-opening for further checks
            stream.seek(0)
            img = Image.open(stream)
            img.load()  # Force decode all image data to detect truncation/corruption
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as e:
            return ImageValidationResult(
                is_valid=False,
                content_hash=content_hash,
                file_size=file_size,
                error_reason=f"corrupted_or_invalid_image: {type(e).__name__}",
            )

        # Check allowed formats
        if img_format not in self.allowed_formats:
            return ImageValidationResult(
                is_valid=False,
                width=width,
                height=height,
                format=img_format,
                content_hash=content_hash,
                file_size=file_size,
                error_reason=f"format_{img_format}_not_allowed",
            )

        # Check minimum dimensions
        if width < self.min_width or height < self.min_height:
            return ImageValidationResult(
                is_valid=False,
                width=width,
                height=height,
                format=img_format,
                content_hash=content_hash,
                file_size=file_size,
                error_reason=f"dimensions_{width}x{height}_below_minimum_{self.min_width}x{self.min_height}",
            )

        return ImageValidationResult(
            is_valid=True,
            width=width,
            height=height,
            format=img_format,
            content_hash=content_hash,
            file_size=file_size,
            error_reason="",
        )


class ImageDeduplicator:
    """
    Thread-safe deduplicator tracking content hashes to eliminate duplicate images.
    """

    def __init__(self, initial_hashes: Optional[Set[str]] = None):
        self._seen_hashes: Set[str] = set(initial_hashes) if initial_hashes else set()
        self._lock = threading.Lock()

    def is_duplicate(self, content_hash: str) -> bool:
        """Check if content hash is already registered."""
        with self._lock:
            return content_hash in self._seen_hashes

    def register(self, content_hash: str) -> bool:
        """
        Register a content hash.
        Returns True if newly added, False if it was already present.
        """
        with self._lock:
            if content_hash in self._seen_hashes:
                return False
            self._seen_hashes.add(content_hash)
            return True

    def count(self) -> int:
        """Return total unique registered hashes."""
        with self._lock:
            return len(self._seen_hashes)
