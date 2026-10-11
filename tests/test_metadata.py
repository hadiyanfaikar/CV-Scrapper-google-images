import csv
from pathlib import Path
from src.metadata.manager import MetadataManager
from src.models import DownloadResult


class TestMetadataManager:
    """Test suite for thread-safe metadata CSV handling."""

    def test_csv_initialization_and_header(self, tmp_path):
        mgr = MetadataManager(output_dir=tmp_path)
        assert mgr.csv_path.exists()

        with open(mgr.csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)

        expected = [
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
        assert header == expected

    def test_record_result(self, tmp_path):
        mgr = MetadataManager(output_dir=tmp_path)
        res = DownloadResult(
            filename="car_0001_abc12345.jpg",
            keyword="car",
            image_url="https://example.com/car.jpg",
            source_url="https://example.com/car-article",
            width=1920,
            height=1080,
            format="JPEG",
            file_size=204800,
            download_status="success",
        )
        mgr.record_result(res)

        with open(mgr.csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        assert len(rows) == 1
        r = rows[0]
        assert r["filename"] == "car_0001_abc12345.jpg"
        assert r["keyword"] == "car"
        assert r["image_url"] == "https://example.com/car.jpg"
        assert r["source_url"] == "https://example.com/car-article"
        assert r["width"] == "1920"
        assert r["height"] == "1080"
        assert r["format"] == "JPEG"
        assert r["file_size"] == "204800"
        assert r["download_status"] == "success"
