from concurrent.futures import ThreadPoolExecutor
from src.utils.helpers import calculate_content_hash
from src.validator.image_validator import ImageDeduplicator


class TestImageDeduplicator:
    """Test suite for content hash deduplication."""

    def test_unique_registration(self):
        dedup = ImageDeduplicator()
        hash1 = calculate_content_hash(b"image content A")
        hash2 = calculate_content_hash(b"image content B")

        assert dedup.is_duplicate(hash1) is False
        assert dedup.register(hash1) is True
        assert dedup.is_duplicate(hash1) is True

        assert dedup.is_duplicate(hash2) is False
        assert dedup.register(hash2) is True
        assert dedup.count() == 2

    def test_duplicate_registration_rejected(self):
        dedup = ImageDeduplicator()
        raw = b"identical content bytes"
        hash_val = calculate_content_hash(raw)

        # First registration succeeds
        assert dedup.register(hash_val) is True
        # Second registration fails
        assert dedup.register(hash_val) is False
        assert dedup.count() == 1

    def test_thread_safety(self):
        dedup = ImageDeduplicator()
        same_hash = calculate_content_hash(b"shared test image payload")

        def attempt_register():
            return dedup.register(same_hash)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(attempt_register) for _ in range(20)]
            results = [f.result() for f in futures]

        # Exactly one worker thread should succeed in registering
        assert results.count(True) == 1
        assert results.count(False) == 19
        assert dedup.count() == 1
