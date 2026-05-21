"""
PDF → PageEvidence records.

Strategy per page:
1. pdfplumber text extraction
2. pdfplumber table extraction (appended to text)
3. If text < MIN_CHARS threshold → OCR fallback via pytesseract
4. Store: page_number, text, extraction_method, confidence
"""

import uuid
import logging
import pdfplumber
from backend.ingestion.ocr import ocr_page

logger = logging.getLogger(__name__)
MIN_TEXT_CHARS = 80


def parse_pdf(file_path: str, document_id: str) -> list[dict]:
    """
    Returns list of PageEvidence dicts (not yet saved to DB).
    Each dict: {id, document_id, page_number, text, extraction_method, confidence}
    """
    pages = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            pnum = page.page_number
            method = "text"
            confidence = 1.0
            parts = []

            raw = (page.extract_text() or "").strip()
            if raw:
                parts.append(raw)

            try:
                for table in page.extract_tables():
                    if not table:
                        continue
                    rows = []
                    for row in table:
                        cells = [str(c or "").strip() for c in row]
                        rows.append(" | ".join(cells))
                    table_text = "\n".join(rows)
                    if table_text.strip():
                        parts.append(f"[TABLE]\n{table_text}\n[/TABLE]")
                        method = "table" if not raw else "text+table"
            except Exception as e:
                logger.warning(f"Table extraction failed page {pnum}: {e}")

            combined = "\n\n".join(parts).strip()

            if len(combined) < MIN_TEXT_CHARS:
                ocr_text = ocr_page(page)
                if ocr_text and len(ocr_text) > len(combined):
                    combined = ocr_text
                    method = "ocr"
                    confidence = 0.75
                    logger.info(f"  Page {pnum}: OCR fallback used ({len(combined)} chars)")
                else:
                    confidence = 0.5
                    logger.warning(f"  Page {pnum}: sparse text, OCR unavailable or worse")

            pages.append({
                "id": str(uuid.uuid4()),
                "document_id": document_id,
                "page_number": pnum,
                "text": combined,
                "extraction_method": method,
                "confidence": confidence,
            })

    logger.info(f"Parsed {len(pages)} pages from {file_path}")
    return pages
