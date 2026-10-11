# Google Images Scraper for Machine Learning & Computer Vision

A modular, production-grade Python tool designed to search, validate, deduplicate, and organize high-resolution images from Google Images into structured datasets for Computer Vision (CV) and Machine Learning (ML) workflows.

---

## 🌟 Key Features

- **Multi-Engine Search Architecture**:
  - `google_browser`: Automated browser scraping powered by **Playwright** with stealth headers, scrolling, and side preview panel extraction to get **original high-resolution image URLs** (bukan hanya thumbnail).
  - `google_api`: Integrates with the official **Google Custom Search JSON API** for 100% stable, compliant, zero-CAPTCHA dataset curation.
  - `commons`: Fallback engine using Wikimedia Commons for keyless offline/local testing and CI/CD validation.
- **Robust Image Processing & Validation**:
  - Validates image integrity using **Pillow** (`PIL.Image`).
  - Enforces minimum width and height limits (`min_width`, `min_height`).
  - Filters allowed formats (`JPEG`, `PNG`, `WEBP`, dll).
- **Content-Based Deduplication**:
  - Eliminates duplicate images using **SHA-256** hash checking across URLs and keywords.
- **Structured Dataset Organization**:
  - Categorizes images into subdirectories by sanitized keyword names.
  - Automatically records full metadata in `metadata/images.csv`.
  - Writes runtime logs to `logs/scraper.log`.
- **Concurrent & Resilient Downloader**:
  - Multi-threaded bounded downloads with `ThreadPoolExecutor`.
  - Automatic retry with exponential backoff on HTTP 429/5xx and network timeouts.
- **Ethical Anti-Bot Compliance**:
  - Detects Google CAPTCHA / `/sorry/index` redirects and halts gracefully with clear mitigation advice instead of attempting illicit CAPTCHA bypasses.

---

## 📁 Project Structure

```text
Scrapping-CV-google/
├── config.yaml                    # Default configuration file
├── requirements.txt              # Production dependencies
├── pyproject.toml                # Project metadata & pytest configuration
├── scraper.py                    # Main CLI entry point
├── README.md                     # Documentation & usage guide
├── src/
│   ├── __init__.py
│   ├── config.py                 # Configuration manager (YAML & CLI parser)
│   ├── models.py                 # Dataclasses: ImageCandidate, DownloadResult, etc.
│   ├── downloader/
│   │   ├── __init__.py
│   │   └── image_downloader.py   # Multi-threaded download engine with retries
│   ├── metadata/
│   │   ├── __init__.py
│   │   └── manager.py            # Thread-safe CSV metadata manager
│   ├── search/
│   │   ├── __init__.py
│   │   ├── base.py               # Abstract base class & exceptions
│   │   ├── browser_searcher.py   # Playwright Google Images automated scraper
│   │   ├── factory.py            # Searcher factory pattern
│   │   ├── google_api.py         # Official Google Custom Search JSON API provider
│   │   └── open_commons.py       # Wikimedia Commons open image provider
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── helpers.py            # Hashing, sanitization, filename generation
│   │   └── logger.py             # Dual console & file logger
│   └── validator/
│       ├── __init__.py
│       └── image_validator.py    # PIL validation & SHA-256 deduplicator
├── sample_output/
│   └── metadata/
│       └── images.csv            # Contoh output metadata CSV
└── tests/
    ├── __init__.py
    ├── test_config.py            # Tests for configuration & CLI overrides
    ├── test_deduplicator.py      # Tests for content-hash deduplication & concurrency
    ├── test_helpers.py           # Tests for keyword sanitization & filename hashing
    ├── test_metadata.py          # Tests for thread-safe metadata CSV handling
    └── test_validator.py         # Tests for PIL image validation & format filters
```

---

## 🗂 Dataset Directory Layout

Hasil scraping disusun secara otomatis dengan hierarki berikut:

```text
google_images_dataset/
├── images/
│   ├── sports_car/
│   │   ├── sports_car_0001_8f1a2c3b.jpg
│   │   └── sports_car_0002_5e4d3c2a.png
│   ├── truk_logistik/
│   │   └── truk_logistik_0001_1a2b3c4d.jpg
│   └── sepeda_motor/
│       └── sepeda_motor_0001_3b4c5d6e.jpg
├── metadata/
│   └── images.csv
└── logs/
    └── scraper.log
```

---

## 🚀 Installation

### 1. Prasyarat Sistem
- Python 3.11 atau versi lebih baru (diuji pada Python 3.11 – 3.14).
- Linux / macOS / Windows.

### 2. Setup Virtual Environment
```bash
# Clone atau masuk ke direktori proyek
cd Scrapping-CV-google

# Buat virtual environment
python3 -m venv .venv

# Aktifkan virtual environment
# Linux/macOS:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate
```

### 3. Install Dependensi & Browser Playwright
```bash
pip install -r requirements.txt

# Install binary headless browser untuk Playwright
playwright install firefox chromium
```

---

## 💻 Penggunaan (CLI)

### 1. Pencarian Standar via CLI
```bash
python scraper.py --keywords "car,truck,motorcycle" --max-images 50
```

### 2. Pencarian Keyword Bahasa Indonesia & Multibahasa
```bash
python scraper.py --keywords "kucing anggora,truk logistik,sepeda motor balap" --max-images 20
```

### 3. Menggunakan File Konfigurasi (`config.yaml`)
```bash
python scraper.py --config config.yaml
```

### 4. Menyesuaikan Filter Resolusi & Format Gambar
```bash
python scraper.py \
  --keywords "sports car" \
  --max-images 30 \
  --min-width 800 \
  --min-height 600 \
  --allowed-formats "JPEG,PNG" \
  --output-dir "dataset_highres"
```

### 5. Menggunakan Official Google Custom Search JSON API
Untuk performa tingkat produksi tanpa risiko pemblokiran IP atau CAPTCHA:
```bash
python scraper.py \
  --keywords "sports car" \
  --engine google_api \
  --api-key "YOUR_GOOGLE_API_KEY" \
  --cx "YOUR_SEARCH_ENGINE_ID" \
  --max-images 50
```
*(Bisa juga diset melalui environment variable `GOOGLE_API_KEY` dan `GOOGLE_CX`)*.

### 6. Mode Headful Browser (Debugging Otomasi)
```bash
python scraper.py --keywords "electric car" --no-headless --browser-type firefox
```

### 7. Menampilkan Panduan Lengkap Opsi CLI
```bash
python scraper.py --help
```

---

## ⚙️ Opsi Konfigurasi (`config.yaml`)

| Parameter | Tipe | Default | Deskripsi |
| :--- | :---: | :---: | :--- |
| `keywords` | `list[str]` | `["sports car"]` | Daftar kata kunci pencarian batch |
| `engine` | `str` | `"google_browser"` | Pilihan engine: `google_browser`, `google_api`, `commons` |
| `max_images_per_keyword` | `int` | `20` | Batas maksimum gambar tersimpan per keyword |
| `output_dir` | `str` | `"google_images_dataset"` | Direktori output penyimpanan dataset |
| `min_width` | `int` | `150` | Lebar minimum piksel yang diizinkan |
| `min_height` | `int` | `150` | Tinggi minimum piksel yang diizinkan |
| `allowed_formats` | `list[str]` | `["JPEG", "JPG", "PNG", "WEBP"]` | Format gambar yang diizinkan |
| `timeout` | `float` | `15.0` | Timeout HTTP request / navigasi (detik) |
| `max_retries` | `int` | `3` | Jumlah percobaan ulang saat unduhan gagal |
| `retry_delay` | `float` | `2.0` | Jeda backoff percobaan ulang (detik) |
| `max_workers` | `int` | `5` | Jumlah worker thread download concurrent |
| `delay_between_requests`| `float`| `1.5` | Politeness delay antar keyword |
| `headless` | `bool` | `true` | Menjalankan browser secara headless |
| `browser_type` | `str` | `"firefox"` | Jenis otomasi browser (`firefox` atau `chromium`) |

---

## 📊 Contoh Output Metadata CSV (`images.csv`)

File tersimpan di `<output_dir>/metadata/images.csv`:

```csv
filename,keyword,image_url,source_url,width,height,format,file_size,download_status
sports_car_0001_8f1a2c3b.jpg,sports car,https://images.unsplash.com/photo-1503376780353-7e6692767b70,https://unsplash.com/photos/sports-car,1920,1080,JPEG,328450,success
sports_car_0002_5e4d3c2a.png,sports car,https://upload.wikimedia.org/wikipedia/commons/a/a0/Porsche_356_No._1_Roadster.png,https://commons.wikimedia.org/wiki/File:Porsche_356.png,1280,720,PNG,845120,success
sports_car_0003_d1e2f3a4.webp,sports car,https://cdn.motor1.com/images/mgl/porsche-911-gt3.webp,https://www.motor1.com/reviews/porsche-gt3,1024,768,WEBP,194200,success
,sports car,https://example.com/duplicate_car.jpg,https://example.com/article,1920,1080,JPEG,328450,skipped_duplicate
,sports car,https://example.com/tiny_icon.png,https://example.com/blog,64,64,PNG,4096,failed_validation_dimensions_64x64_below_minimum_150x150
,sports car,https://example.com/unsupported.bmp,https://example.com/archive,800,600,BMP,1440000,failed_validation_format_BMP_not_allowed
,sports car,https://broken-domain.net/not-found.jpg,https://broken-domain.net/post,,,,failed_http_404
```

---

## 🧪 Pengujian Unit Test

Proyek ini dilengkapi dengan pengujian unit komprehensif menggunakan `pytest`.

Jalankan pengujian:
```bash
pytest -v
```

Cakupan pengujian:
1. **`test_validator.py`**:
   - Memvalidasi gambar sah (JPEG, PNG, WEBP).
   - Menolak gambar yang dimensinya di bawah `min_width` / `min_height`.
   - Menolak format yang tidak terdaftar dalam `allowed_formats`.
   - Mendeteksi byte gambar yang korup atau terpotong.
   - Menangani payload kosong / terlalu kecil.
2. **`test_deduplicator.py`**:
   - Pendaftaran hash unik (SHA-256).
   - Penolakan duplikasi konten identik dari URL berbeda.
   - Thread-safety saat registrasi bersamaan pada lingkungan multi-thread.
3. **`test_helpers.py`**:
   - Sanitasi keyword multi-bahasa (Indonesia, Inggris, simbol khusus).
   - Struktur penamaan file yang unik dan deterministik.
4. **`test_config.py`**:
   - Validasi nilai konfigurasi default.
   - Pengecekan override parameter via CLI terhadap file YAML.
5. **`test_metadata.py`**:
   - Integritas header CSV dan penulisan thread-safe baris metadata.

---

## 🔍 Keterbatasan Scraper & Strategi Menghadapi Perubahan DOM

### 1. Keterbatasan Scraper Berbasis Otomasi Browser
- **Mekanisme Anti-Bot Google**:
  Google Images menerapkan sistem deteksi bot canggih. Jika permintaan dikirim dari IP datacenter (misal AWS, GCP, Azure, DigitalOcean) atau mengirimkan query terlalu cepat, Google akan mengalihkan halaman ke `https://www.google.com/sorry/index` (CAPTCHA/Unusual Traffic). Sesuai prinsip rekayasa yang bertanggung jawab dan Terms of Service, aplikasi ini **tidak membobol CAPTCHA** melainkan mendeteksi sinyal ini dan melempar `GoogleAntiBotException` secara terstruktur.
- **Tingkat Kegagalan URL Sumber Asli**:
  Beberapa website pihak ketiga yang diindeks Google mengaktifkan proteksi hotlinking (HTTP 403 Forbidden) atau telah menghapus gambar (HTTP 404 Not Found). Downloader menangani ini melalui status pencatatan metadata tanpa menghentikan proses scraping keseluruhan.

### 2. Strategi Menghadapi Perubahan Struktur DOM Google Images
Google secara berkala mengubah class CSS (misalnya dari nama kelas lama seperti `rg_i`, `n3Vbe` menjadi nama terobfuskasi acak seperti `sFlh5c`, `pT0Scc`, dll).

Untuk memastikan keandalan jangka panjang, aplikasi ini menerapkan 3 strategi:
1. **Multi-Selector Semantic Fallback**:
   Tidak hanya mengandalkan satu nama class CSS spesifik, scraper menggunakan selektor fungsional berbasis atribut dan hierarki ARIA:
   - `img[src^="http"]:not([src*="gstatic.com"])` di dalam container `div[role="region"]` atau `div[role="dialog"]`.
   - Selektor `a[role="link"]` untuk URL halaman sumber.
2. **In-Page Script / JSON Hydration Parsing**:
   Selain simulasi klik DOM, scraper memindai blok skrip inline `AF_initDataCallback` yang menyematkan metadata gambar langsung dari backend Google. Cara ini kebal terhadap perubahan nama class CSS UI.
3. **Penyediaan Jalur Resmi (Official Google Custom Search API)**:
   Untuk kebutuhan dataset ML skala besar di lingkungan server/CI/CD cloud, gunakan opsi `--engine google_api`. API resmi menjamin struktur output yang stabil, tidak terpengaruh oleh pembaruan UI Google, serta legal dan sesuai kepatuhan hak cipta.

---

## ⚖️ Etika, Hak Cipta, dan Kepatuhan Hukum

- **Penggunaan Wajar (Fair Use)**: Pastikan pengumpulan gambar mematuhi ketentuan lisensi hak cipta dari masing-masing pemilik konten asli.
- **Rate Limiting**: Gunakan parameter `delay_between_requests` dan batasi `max_workers` agar tidak membebani server penyedia gambar.
- **Pemberian Atribusi**: Metadata CSV selalu menyimpan `source_url` untuk mempermudah pelacakan sumber dan lisensi asli gambar.
