"""
Generates exportable audit reports.
Formats: JSON (machine-readable) and PDF (human-readable via reportlab).
"""

import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.models import Document, ExtractedClaim, Discrepancy


def build_audit_dict(document_ids: list[str], db: Session) -> dict:
    """Build a full audit dict for JSON export."""
    docs = db.query(Document).filter(Document.id.in_(document_ids)).all()
    discrepancies = (
        db.query(Discrepancy)
        .join(ExtractedClaim, Discrepancy.claim_a_id == ExtractedClaim.id, isouter=True)
        .filter(ExtractedClaim.document_id.in_(document_ids))
        .all()
    )

    disc_list = []
    for d in discrepancies:
        claim_a = db.query(ExtractedClaim).filter(ExtractedClaim.id == d.claim_a_id).first()
        claim_b = db.query(ExtractedClaim).filter(ExtractedClaim.id == d.claim_b_id).first()

        doc_a = db.query(Document).filter(Document.id == claim_a.document_id).first() if claim_a else None
        doc_b = db.query(Document).filter(Document.id == claim_b.document_id).first() if claim_b else None

        disc_list.append({
            "id": d.id,
            "mismatch_type": d.mismatch_type,
            "severity": d.severity,
            "confidence": d.confidence,
            "summary": d.summary,
            "explanation": d.explanation,
            "citation_a": {
                "document": doc_a.filename if doc_a else None,
                "page": claim_a.page_number if claim_a else None,
                "source_text": claim_a.source_text if claim_a else None,
                "value": claim_a.value_raw if claim_a else None,
                "extraction_method": claim_a.extraction_method if claim_a else None,
            } if claim_a else None,
            "citation_b": {
                "document": doc_b.filename if doc_b else None,
                "page": claim_b.page_number if claim_b else None,
                "source_text": claim_b.source_text if claim_b else None,
                "value": claim_b.value_raw if claim_b else None,
                "extraction_method": claim_b.extraction_method if claim_b else None,
            } if claim_b else None,
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "documents": [{"id": d.id, "filename": d.filename, "doc_type": d.doc_type, "pages": d.page_count} for d in docs],
        "summary": {
            "total_flags": len(disc_list),
            "high": sum(1 for d in disc_list if d["severity"] == "HIGH"),
            "medium": sum(1 for d in disc_list if d["severity"] == "MEDIUM"),
            "low": sum(1 for d in disc_list if d["severity"] == "LOW"),
        },
        "discrepancies": disc_list,
    }


def export_json(document_ids: list[str], db: Session) -> str:
    return json.dumps(build_audit_dict(document_ids, db), indent=2)


def export_pdf_bytes(document_ids: list[str], db: Session) -> bytes:
    """Generate a simple PDF audit report using reportlab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.units import inch
    import io

    audit = build_audit_dict(document_ids, db)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=inch, rightMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("InterLock AI — Review Audit Report", styles["Title"]))
    story.append(Paragraph(f"Generated: {audit['generated_at']}", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    s = audit["summary"]
    story.append(Paragraph(
        f"Documents reviewed: {len(audit['documents'])} | "
        f"Flags: {s['total_flags']} ({s['high']} HIGH, {s['medium']} MEDIUM, {s['low']} LOW)",
        styles["Normal"]
    ))
    story.append(Spacer(1, 0.3 * inch))

    for disc in audit["discrepancies"]:
        story.append(Paragraph(
            f"<b>[{disc['severity']}] {disc['mismatch_type']}</b> — confidence {disc['confidence']:.0%}",
            styles["Heading3"]
        ))
        story.append(Paragraph(disc["summary"], styles["Normal"]))

        if disc["citation_a"]:
            c = disc["citation_a"]
            story.append(Paragraph(
                f"<i>{c['document']}, page {c['page']} ({c['extraction_method']}):</i><br/>\"{c['source_text']}\"",
                styles["Normal"]
            ))
        if disc["citation_b"]:
            c = disc["citation_b"]
            story.append(Paragraph(
                f"<i>{c['document']}, page {c['page']} ({c['extraction_method']}):</i><br/>\"{c['source_text']}\"",
                styles["Normal"]
            ))

        if disc["explanation"]:
            story.append(Paragraph(f"<b>Review note:</b> {disc['explanation']}", styles["Normal"]))

        story.append(Spacer(1, 0.2 * inch))

    doc.build(story)
    return buf.getvalue()
