import json
import logging
from pathlib import Path
import re
import time
from typing import Dict, List, Optional, Set
import urllib.parse

from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
try:
    from playwright_stealth import Stealth
    _STEALTH_AVAILABLE = True
except ImportError:
    _STEALTH_AVAILABLE = False

from src.config import ScraperConfig
from src.models import ImageCandidate
from src.search.base import BaseImageSearcher, GoogleAntiBotException, SearchProviderException


class GoogleImagesBrowserSearcher(BaseImageSearcher):
    """
    Automated browser scraper for Google Images using Playwright.
    Employs stealth evasion, consent handling, progressive scrolling,
    and preview panel inspection to extract high-resolution original image URLs.
    """

    def __init__(self, config: ScraperConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger("GoogleImagesScraper")

    def search(self, keyword: str, max_results: int) -> List[ImageCandidate]:
        """
        Search Google Images for the given keyword and extract original image URLs.
        """
        self.logger.info(
            f"Launching Playwright ({self.config.browser_type}, headless={self.config.headless}) "
            f"for keyword: '{keyword}'"
        )
        candidates: List[ImageCandidate] = []
        profile_dir = Path(self.config.output_dir) / ".browser_profile"
        profile_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as playwright:
            args = ["--no-sandbox", "--disable-setuid-sandbox"]
            browser_type = (
                playwright.firefox if self.config.browser_type == "firefox" else playwright.chromium
            )
            context = browser_type.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=self.config.headless,
                args=args,
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/128.0.0.0 Safari/537.36"
                ),
                locale="en-US,en;q=0.9,id;q=0.8",
            )
            try:
                page = context.pages[0] if context.pages else context.new_page()

                # Apply stealth if available (Chromium)
                if _STEALTH_AVAILABLE and self.config.browser_type == "chromium":
                    try:
                        Stealth().apply_stealth_sync(page)
                    except Exception as e:
                        self.logger.debug(f"Stealth application note: {e}")

                candidates = self._run_search_flow(page, keyword, max_results)

            finally:
                context.close()

        return candidates

    def _run_search_flow(self, page: Page, keyword: str, max_results: int) -> List[ImageCandidate]:
        """Execute navigation, anti-bot check, consent approval, and extraction."""
        encoded_kw = urllib.parse.quote_plus(keyword)
        # udm=2 is the modern Google Images search mode
        search_url = f"https://www.google.com/search?q={encoded_kw}&udm=2"
        self.logger.info(f"Navigating to: {search_url}")

        page.goto(search_url, wait_until="domcontentloaded", timeout=self.config.timeout * 1000)
        try:
            page.wait_for_load_state("load", timeout=5000)
        except Exception:
            pass
        time.sleep(1.5)

        # Check for Google Anti-Bot / CAPTCHA page
        current_url = page.url
        body_text = page.inner_text("body").lower() if page.query_selector("body") else ""
        if "sorry/index" in current_url or "unusual traffic" in body_text or "our systems have detected" in body_text:
            if not self.config.headless:
                self.logger.warning("=" * 60)
                self.logger.warning("[VERIFIKASI GOOGLE CAPTCHA TERDETEKSI]")
                self.logger.warning("Jendela browser sedang terbuka di layar Anda.")
                self.logger.warning("Silakan selesaikan CAPTCHA di browser (menunggu hingga 60 detik)...")
                self.logger.warning("=" * 60)
                solved = False
                for _ in range(30):
                    time.sleep(2)
                    cur_url = page.url
                    cur_body = page.inner_text("body").lower() if page.query_selector("body") else ""
                    if "sorry/index" not in cur_url and "unusual traffic" not in cur_body:
                        solved = True
                        self.logger.info("Verifikasi CAPTCHA berhasil! Melanjutkan ekstraksi gambar...")
                        break
                if not solved:
                    raise GoogleAntiBotException("Waktu tunggu penyelesaian CAPTCHA habis (60s).")
            else:
                raise GoogleAntiBotException(
                    "Google mendeteksi trafik otomatis dari IP ini dan meminta verifikasi CAPTCHA (sorry/index).\n"
                    "Karena mode headless aktif, verifikasi tidak bisa diselesaikan secara otomatis.\n\n"
                    "Solusi agar bisa menggunakan Google Images:\n"
                    "1. Buka browser secara visual untuk menyelesaikan verifikasi sekali saja:\n"
                    "   python scraper.py --keywords \"CV Backend Developer\" --engine google --no-headless\n\n"
                    "2. Gunakan Google Custom Search API resmi (100% bebas CAPTCHA):\n"
                    "   python scraper.py --keywords \"CV Backend Developer\" --engine google_api --api-key KEY --cx CX"
                )

        # Handle cookie / consent dialogs if present
        self._handle_consent_dialog(page)

        time.sleep(self.config.delay_between_requests)

        # Extraction Pipeline
        collected_candidates: List[ImageCandidate] = []
        seen_urls: Set[str] = set()

        # Phase 1: High-res Extraction via Thumbnail Click & Preview Inspection
        self.logger.info("Extracting high-resolution images via preview pane inspection...")
        interactive_candidates = self._extract_via_preview_panel(page, keyword, max_results, seen_urls)
        collected_candidates.extend(interactive_candidates)

        # Phase 2: If we need more candidates, parse inline JSON / script data
        if len(collected_candidates) < max_results:
            self.logger.info(
                f"Collected {len(collected_candidates)}/{max_results} images via preview panel. "
                "Extracting additional candidates from structured page data..."
            )
            script_candidates = self._extract_from_page_scripts(page, keyword, max_results, seen_urls)
            collected_candidates.extend(script_candidates)

        # Phase 3: Fallback to rendered thumbnails only if allowed and still below target
        if len(collected_candidates) < max_results:
            self.logger.warning(
                f"Could not reach {max_results} original URLs (got {len(collected_candidates)}). "
                "Checking thumbnail fallbacks..."
            )
            thumbnail_candidates = self._extract_thumbnails_fallback(page, keyword, max_results, seen_urls)
            collected_candidates.extend(thumbnail_candidates)

        self.logger.info(
            f"Extraction completed for keyword '{keyword}'. Found {len(collected_candidates)} candidate URLs."
        )
        return collected_candidates[:max_results]

    def _handle_consent_dialog(self, page: Page) -> None:
        """Dismiss Google consent or cookie modal if it appears."""
        consent_selectors = [
            "button#L2AGLb",
            "button:has-text('Accept all')",
            "button:has-text('Setuju semua')",
            "button:has-text('I agree')",
            "button:has-text('Accept')",
        ]
        for sel in consent_selectors:
            try:
                elem = page.query_selector(sel)
                if elem and elem.is_visible():
                    self.logger.info("Accepting Google consent dialog...")
                    elem.click()
                    time.sleep(1.0)
                    break
            except Exception:
                pass

    def _extract_via_preview_panel(
        self,
        page: Page,
        keyword: str,
        max_results: int,
        seen_urls: Set[str],
    ) -> List[ImageCandidate]:
        """
        Click thumbnail cards to reveal Google's high-res side preview drawer,
        extracting the full resolution original image URL and source webpage.
        """
        results: List[ImageCandidate] = []
        scroll_attempts = 0

        while len(results) < max_results and scroll_attempts < self.config.max_scroll_attempts:
            # Query all thumbnail containers/images on the page
            thumbnails = page.query_selector_all("div[data-ved] img, div.eMoQbe img, div.H8JuOv img, img.YQ4gaf")
            if not thumbnails:
                # Alternative broad selector for image results
                thumbnails = page.query_selector_all("div[role='listitem'] img, a[role='link'] img")

            for thumb in thumbnails:
                if len(results) >= max_results:
                    break

                try:
                    if not thumb.is_visible():
                        continue

                    # Scroll thumbnail into view and click
                    thumb.scroll_into_view_if_needed(timeout=2000)
                    thumb.click(timeout=2000)
                    time.sleep(0.6)  # Allow preview panel to render

                    # Search for original high-resolution image in preview pane
                    # Google uses preview img elements that load the full image
                    candidate_info = self._get_preview_image_info(page)
                    if candidate_info and candidate_info["image_url"]:
                        img_url = candidate_info["image_url"]
                        if img_url not in seen_urls and not img_url.startswith("data:image/"):
                            seen_urls.add(img_url)
                            results.append(
                                ImageCandidate(
                                    keyword=keyword,
                                    image_url=img_url,
                                    source_url=candidate_info.get("source_url", ""),
                                    title=candidate_info.get("title", ""),
                                    thumbnail_url=candidate_info.get("thumbnail_url", ""),
                                )
                            )
                            self.logger.debug(f"Captured original image URL: {img_url[:70]}...")

                except Exception as e:
                    self.logger.debug(f"Note during thumbnail click: {e}")
                    continue

            # Scroll page down to load more thumbnails
            page.evaluate("window.scrollBy(0, window.innerHeight * 2);")
            time.sleep(self.config.scroll_delay)
            scroll_attempts += 1

        return results

    def _get_preview_image_info(self, page: Page) -> Optional[Dict[str, str]]:
        """
        Extract the original image URL and source URL from the currently active preview pane.
        """
        # Selectors for high-res preview image in Google Images
        preview_img_selectors = [
            "img.sFlh5c",
            "img.pT0Scc",
            "img.n3Vbe",
            "div[role='region'] img[src^='http']:not([src*='gstatic.com'])",
            "div[role='dialog'] img[src^='http']:not([src*='gstatic.com'])",
            "div[data-component-id] img[src^='http']:not([src*='gstatic.com'])",
        ]

        img_url = None
        title = ""
        source_url = ""

        for sel in preview_img_selectors:
            try:
                elements = page.query_selector_all(sel)
                for el in elements:
                    src = el.get_attribute("src") or el.get_attribute("data-src")
                    if src and src.startswith("http") and "encrypted-tbn0.gstatic.com" not in src:
                        img_url = src
                        title = el.get_attribute("alt") or ""
                        break
                if img_url:
                    break
            except Exception:
                continue

        # Look for source webpage link in preview pane
        source_selectors = [
            "a[role='link'][href^='http']:not([href*='google.com'])",
            "a.HM1uAd[href^='http']",
            "div[role='region'] a[href^='http']:not([href*='google.com'])",
        ]
        for s_sel in source_selectors:
            try:
                link_el = page.query_selector(s_sel)
                if link_el:
                    source_url = link_el.get_attribute("href") or ""
                    break
            except Exception:
                pass

        if img_url:
            return {
                "image_url": img_url,
                "source_url": source_url,
                "title": title,
                "thumbnail_url": "",
            }
        return None

    def _extract_from_page_scripts(
        self,
        page: Page,
        keyword: str,
        max_results: int,
        seen_urls: Set[str],
    ) -> List[ImageCandidate]:
        """
        Parse embedded JSON / script blobs containing high-resolution image URLs.
        Google Images injects candidate data in script blocks on initial and paginated loads.
        """
        results: List[ImageCandidate] = []
        content = page.content()

        # Match pattern: ["https://...", height, width]
        patterns = re.findall(r'\[\"(https?://[^\"]+?\.(?:jpg|jpeg|png|webp)[^\"]*?)\",\s*(\d+),\s*(\d+)\]', content, re.IGNORECASE)
        for url, height, width in patterns:
            # Filter out google/gstatic static assets
            if "gstatic.com" in url or "google.com" in url:
                continue
            # Unescape unicode characters if any
            clean_url = url.encode().decode("unicode-escape", errors="ignore")
            if clean_url not in seen_urls:
                seen_urls.add(clean_url)
                results.append(
                    ImageCandidate(
                        keyword=keyword,
                        image_url=clean_url,
                        estimated_width=int(width),
                        estimated_height=int(height),
                    )
                )
                if len(results) >= max_results:
                    break

        return results

    def _extract_thumbnails_fallback(
        self,
        page: Page,
        keyword: str,
        max_results: int,
        seen_urls: Set[str],
    ) -> List[ImageCandidate]:
        """
        Fallback only when original images are unavailable: extracts rendered thumbnails.
        """
        results: List[ImageCandidate] = []
        imgs = page.eval_on_selector_all(
            "img",
            """els => els.map(e => ({
                src: e.src || e.getAttribute('data-src') || '',
                alt: e.alt || ''
            })).filter(x => x.src.startsWith('http'))"""
        )
        for item in imgs:
            url = item.get("src", "")
            if url and url not in seen_urls and "google.com/images/branding" not in url:
                seen_urls.add(url)
                results.append(
                    ImageCandidate(
                        keyword=keyword,
                        image_url=url,
                        title=item.get("alt", ""),
                        thumbnail_url=url,
                    )
                )
                if len(results) >= max_results:
                    break
        return results
