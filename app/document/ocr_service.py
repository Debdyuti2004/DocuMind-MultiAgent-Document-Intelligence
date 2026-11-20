"""Modular OCR service for scanned PDFs and image-only document pages."""

from typing import Optional
from app.utils.config import settings
from app.utils.logging import logger

TESSERACT_LANG_MAP = {
    "en": "eng",
    "hi": "hin",
    "bn": "ben",
    "es": "spa",
    "fr": "fra",
    "de": "deu",
    "ar": "ara",
    "zh": "chi_sim",
    "ja": "jpn",
    "ru": "rus",
    "pt": "por",
    "it": "ita",
    "nl": "nld",
    "id": "ind",
    "tr": "tur",
    "ur": "urd",
}


class OCRService:
    """Provides modular, optional OCR capability when scanned or image-heavy pages are encountered."""

    def __init__(self):
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        """Checks if OCR engine (pytesseract + tesseract binary) is installed and available."""
        if self._available is None:
            try:
                import pytesseract
                # Test minimal call or version check
                pytesseract.get_tesseract_version()
                self._available = True
            except Exception:
                self._available = False
        return self._available

    def is_scanned_page(self, text: str, min_chars: int = 40) -> bool:
        """Determines if extracted page text is insufficient, indicating a scanned image."""
        clean = (text or "").strip()
        return len(clean) < min_chars

    def ocr_pixmap(self, pixmap, language_code: str = "en") -> str:
        """Runs OCR on a PyMuPDF Pixmap if OCR engine is available."""
        if not settings.OCR_ENABLED or not self.is_available():
            return ""

        try:
            import pytesseract
            from PIL import Image
            import io

            img_bytes = pixmap.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            lang = TESSERACT_LANG_MAP.get(language_code, "eng")
            text = pytesseract.image_to_string(img, lang=lang)
            return text.strip()
        except Exception as e:
            logger.warning(f"OCR execution failed on page: {e}")
            return ""


ocr_service = OCRService()
