"""
Orchestrates the hybrid extraction pipeline per document.
Order: regex first (high confidence, fast) → LLM normalization (edge cases).
Deduplicates on (entity, page_number) — regex wins over LLM for same entity.
"""

import uuid
import logging
from sqlalchemy.orm import Session

from backend.models import ExtractedClaim, PageEvidence
from backend.extraction.regex_rules import extract_regex_claims
from backend.extraction.llm_normalizer import llm_normalize_page

logger = logging.getLogger(__name__)


def run_extraction(document_id: str, db: Session) -> list[ExtractedClaim]:
    """
    For each PageEvidence record belonging to document_id:
    1. Run regex extraction
    2. Run LLM normalization
    3. Deduplicate: if same entity on same page, keep highest confidence
    4. Save all claims to DB
    Returns list of saved ExtractedClaim objects.
    """
    pages: list[PageEvidence] = (
        db.query(PageEvidence)
        .filter(PageEvidence.document_id == document_id)
        .order_by(PageEvidence.page_number)
        .all()
    )

    seen: dict[tuple, dict] = {}

    for page in pages:
        if not page.text:
            continue

        regex_claims = extract_regex_claims(page.text, page.page_number, document_id)
        llm_claims   = llm_normalize_page(page.text, page.page_number, document_id)

        for c in regex_claims + llm_claims:
            key = (c["entity"], c["page_number"])
            existing = seen.get(key)
            if existing is None or c["confidence"] > existing["confidence"]:
                seen[key] = c

    saved = []
    for c in seen.values():
        claim = ExtractedClaim(
            id=str(uuid.uuid4()),
            **{k: v for k, v in c.items() if k != "id"},
        )
        db.add(claim)
        saved.append(claim)

    db.commit()
    logger.info(f"Saved {len(saved)} claims for document {document_id}")
    return saved
