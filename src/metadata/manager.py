import csv
from pathlib import Path
import threading
from typing import List, Optional, Set

from src.models import DownloadResult


class MetadataManager:
    """
    Manages structured metadata storage into <output_dir>/metadata/images.csv.
    Thread-safe to support concurrent downloads.
    """

    CSV_FIELDS = [
        "filename",
        "keyword",
        "image_url",
        "source_url",
        "width",
        "height",
        "format",
        "file_size",
        "download_status",
    ]

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.metadata_dir = self.output_dir / "metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.metadata_dir / "images.csv"
        self._lock = threading.Lock()
        self._init_csv()

    def _init_csv(self) -> None:
        """Create CSV file with header if it doesn't already exist."""
        with self._lock:
            if not self.csv_path.exists():
                with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=self.CSV_FIELDS)
                    writer.writeheader()

    def record_result(self, result: DownloadResult) -> None:
        """Append a single DownloadResult record to images.csv in a thread-safe manner."""
        with self._lock:
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.CSV_FIELDS)
                writer.writerow(result.to_csv_dict())

    def record_batch(self, results: List[DownloadResult]) -> None:
        """Append multiple records to images.csv."""
        with self._lock:
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.CSV_FIELDS)
                for res in results:
                    writer.writerow(res.to_csv_dict())

    def get_existing_filenames(self) -> Set[str]:
        """Read all existing filenames already successfully recorded."""
        with self._lock:
            if not self.csv_path.exists():
                return set()
            filenames = set()
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    fn = row.get("filename")
                    if fn and row.get("download_status") == "success":
                        filenames.add(fn)
            return filenames
