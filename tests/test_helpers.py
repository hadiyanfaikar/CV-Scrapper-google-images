from src.utils.helpers import calculate_content_hash, generate_filename, sanitize_keyword


class TestHelpers:
    """Test suite for sanitization and helper utilities."""

    def test_sanitize_keyword_indonesian(self):
        assert sanitize_keyword("Kucing Lucu & Gemas!") == "kucing_lucu_gemas"
        assert sanitize_keyword("truk logistik") == "truk_logistik"
        assert sanitize_keyword("sepeda motor roda 2") == "sepeda_motor_roda_2"

    def test_sanitize_keyword_english_and_symbols(self):
        assert sanitize_keyword("Sports Car 2024 (HD)") == "sports_car_2024_hd"
        assert sanitize_keyword("   white-tiger---wild   ") == "white_tiger_wild"

    def test_generate_filename_structure(self):
        content = b"sample image binary"
        c_hash = calculate_content_hash(content)
        filename = generate_filename(
            keyword="sports car",
            index=1,
            content_hash=c_hash,
            ext="jpg",
        )
        # Expected: sports_car_0001_{hash[:8]}.jpg
        assert filename.startswith("sports_car_0001_")
        assert filename.endswith(".jpg")
        # Split from right to get hash and extension
        parts = filename.rsplit("_", 2)
        # parts: ['sports_car', '0001', '{hash[:8]}.jpg']
        assert parts[1] == "0001"
        hash_ext = parts[2]
        hash_part = hash_ext.split(".")[0]
        assert len(hash_part) == 8

    def test_calculate_content_hash_deterministic(self):
        data1 = b"abc123xyz"
        data2 = b"abc123xyz"
        data3 = b"different"
        assert calculate_content_hash(data1) == calculate_content_hash(data2)
        assert calculate_content_hash(data1) != calculate_content_hash(data3)
