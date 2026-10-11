import hashlib
import re
import unicodedata
from pathlib import Path


def sanitize_keyword(keyword: str) -> str:
    """
    Sanitize search keyword into a safe directory and filename prefix.
    Supports Indonesian, English, accented characters, and replaces symbols with underscores.
    """
    # Normalize unicode characters
    normalized = unicodedata.normalize("NFKD", keyword)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")

    # Lowercase and replace non-alphanumeric with underscores
    cleaned = re.sub(r"[^\w\s-]", "", ascii_text.lower()).strip()
    sanitized = re.sub(r"[-\s]+", "_", cleaned)
    return sanitized if sanitized else "unknown_keyword"


def calculate_content_hash(data: bytes) -> str:
    """Calculate SHA-256 hash of binary content for accurate deduplication."""
    return hashlib.sha256(data).hexdigest()


def generate_filename(keyword: str, index: int, content_hash: str, ext: str) -> str:
    """
    Generate unique, structured filename:
    e.g. {sanitized_keyword}_{index:04d}_{short_hash}.{ext}
    """
    clean_kw = sanitize_keyword(keyword)
    short_hash = content_hash[:8] if content_hash else "nohash"
    clean_ext = ext.lower().lstrip(".")
    if not clean_ext:
        clean_ext = "jpg"
    return f"{clean_kw}_{index:04d}_{short_hash}.{clean_ext}"


def ensure_directory(path: str | Path) -> Path:
    """Ensure directory exists and return Path object."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
