"""
OCR fallback using pytesseract.
Accepts a pdfplumber page object, rasterizes it, returns text.
"""

import logging

logger = logging.getLogger(__name__)


def ocr_page(page) -> str | None:
    try:
        import pytesseract
        img = page.to_image(resolution=200).original
        text = pytesseract.image_to_string(img, config="--psm 6")
        return text.strip()
    except ImportError:
        logger.warning("pytesseract not installed — OCR unavailable")
        return None
    except Exception as e:
        logger.warning(f"OCR failed: {e}")
        return None
