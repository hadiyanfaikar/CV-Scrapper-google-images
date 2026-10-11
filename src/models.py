from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ImageCandidate:
    """Represents a discovered image candidate from search."""
    keyword: str
    image_url: str
    source_url: str = ""
    title: str = ""
    thumbnail_url: str = ""
    estimated_width: Optional[int] = None
    estimated_height: Optional[int] = None
    format_hint: Optional[str] = None


@dataclass
class ImageValidationResult:
    """Result of validating image content via Pillow."""
    is_valid: bool
    width: int = 0
    height: int = 0
    format: str = ""
    content_hash: str = ""
    file_size: int = 0
    error_reason: str = ""


@dataclass
class DownloadResult:
    """Metadata record for a downloaded or processed image."""
    filename: str
    keyword: str
    image_url: str
    source_url: str
    width: Optional[int] = None
    height: Optional[int] = None
    format: str = ""
    file_size: Optional[int] = None
    download_status: str = "success"
    local_path: Optional[str] = None
    error_message: Optional[str] = None

    def to_csv_dict(self) -> dict:
        """Convert to dictionary matching the required CSV columns."""
        return {
            "filename": self.filename,
            "keyword": self.keyword,
            "image_url": self.image_url,
            "source_url": self.source_url,
            "width": self.width if self.width is not None else "",
            "height": self.height if self.height is not None else "",
            "format": self.format,
            "file_size": self.file_size if self.file_size is not None else "",
            "download_status": self.download_status,
        }
