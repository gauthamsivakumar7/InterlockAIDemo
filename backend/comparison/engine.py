"""
Main comparison engine orchestrator.
Runs all four detectors in sequence, then adds LLM explanations.
"""

import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.models import Document, ExtractedClaim, Discrepancy
from backend.comparison.parameter_mismatch  import detect_parameter_mismatches
from backend.comparison.assumption_mismatch import detect_assumption_mismatches
from backend.comparison.reference_gap       import detect_reference_gaps
from backend.comparison.checklist_gap       import detect_checklist_gaps
from backend.comparison.explainer           import generate_explanation

logger = logging.getLogger(__name__)


def run_comparison(document_ids: list[str], db: Session) -> list[Discrepancy]:
    """
    Run all detectors across the given documents. Save and return Discrepancy records.
    """
    claims_by_doc: dict[str, list[ExtractedClaim]] = {}
    doc_types: dict[str, str] = {}
    doc_names: dict[str, str] = {}

    for doc_id in document_ids:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            continue
        claims = db.query(ExtractedClaim).filter(ExtractedClaim.document_id == doc_id).all()
        claims_by_doc[doc_id] = claims
        doc_types[doc_id] = doc.doc_type
        doc_names[doc_id]  = doc.filename

    if len(claims_by_doc) < 2:
        logger.warning("Need at least 2 documents to compare")
        return []

    raw_flags = []
    raw_flags += detect_parameter_mismatches(claims_by_doc)
    raw_flags += detect_assumption_mismatches(claims_by_doc)
    raw_flags += detect_reference_gaps(claims_by_doc, doc_types)
    raw_flags += detect_checklist_gaps(claims_by_doc, doc_types)

    logger.info(f"Comparison engine: {len(raw_flags)} raw flags before explanation pass")

    saved: list[Discrepancy] = []
    for flag in raw_flags:
        claim_a = flag.get("claim_a")
        claim_b = flag.get("claim_b")

        doc_a_name = doc_names.get(claim_a.document_id, "Document A") if claim_a else "Document A"
        doc_b_name = doc_names.get(claim_b.document_id, "Document B") if claim_b else None

        explanation = generate_explanation(
            flag["mismatch_type"], claim_a, claim_b, doc_a_name, doc_b_name
        )

        disc = Discrepancy(
            id=str(uuid.uuid4()),
            mismatch_type=flag["mismatch_type"],
            severity=flag["severity"],
            confidence=flag["confidence"],
            summary=flag["summary"],
            explanation=explanation,
            claim_a_id=claim_a.id if claim_a else None,
            claim_b_id=claim_b.id if claim_b else None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        db.add(disc)
        saved.append(disc)

    db.commit()
    logger.info(f"Saved {len(saved)} discrepancies")
    return saved
