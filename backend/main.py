"""
InterLock AI Demo — FastAPI app
Routes:
  POST /documents/upload          — upload + ingest 1 PDF
  POST /analysis/run              — run extraction + comparison on document set
  GET  /documents                 — list all documents
  GET  /documents/{id}/claims     — list extracted claims
  GET  /discrepancies             — list all discrepancies (with claim details)
  GET  /audit/json                — download JSON audit report
  GET  /audit/pdf                 — download PDF audit report
"""

import uuid
import logging
import tempfile
import os
from datetime import datetime, timezone
from typing import Annotated

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.database import get_db, init_db
from backend.models import Document, PageEvidence, ExtractedClaim, Discrepancy
from backend.schemas import DocumentOut, ClaimOut, DiscrepancyOut, AnalysisResult
from backend.ingestion.parser import parse_pdf
from backend.extraction.extractor import run_extraction
from backend.comparison.engine import run_comparison
from backend.audit.report import export_json, export_pdf_bytes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="InterLock AI", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/documents/upload", response_model=DocumentOut)
async def upload_document(
    file: Annotated[UploadFile, File()],
    doc_type: str = Query(default="unknown",
                          description="owner_spec | control_spec | vendor_submittal | unknown"),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")

    data = await file.read()
    doc_id = str(uuid.uuid4())[:8]

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        pages = parse_pdf(tmp_path, doc_id)
    finally:
        os.unlink(tmp_path)

    doc = Document(
        id=doc_id,
        filename=file.filename,
        doc_type=doc_type,
        uploaded_at=datetime.now(timezone.utc).isoformat(),
        page_count=len(pages),
        file_size=len(data),
    )
    db.add(doc)

    for p in pages:
        pe = PageEvidence(**p)
        db.add(pe)

    db.commit()
    db.refresh(doc)
    logger.info(f"Uploaded {file.filename} → {doc_id} ({len(pages)} pages)")
    return doc


@app.post("/analysis/run", response_model=AnalysisResult)
def run_analysis(
    document_ids: list[str],
    db: Session = Depends(get_db),
):
    if len(document_ids) < 2:
        raise HTTPException(400, "Provide at least two document IDs.")

    for did in document_ids:
        if not db.query(Document).filter(Document.id == did).first():
            raise HTTPException(404, f"Document {did} not found.")

    total_claims = 0
    for did in document_ids:
        claims = run_extraction(did, db)
        total_claims += len(claims)

    discrepancies = run_comparison(document_ids, db)

    high   = sum(1 for d in discrepancies if d.severity == "HIGH")
    medium = sum(1 for d in discrepancies if d.severity == "MEDIUM")
    low    = sum(1 for d in discrepancies if d.severity == "LOW")

    return AnalysisResult(
        document_ids=document_ids,
        claims_extracted=total_claims,
        discrepancies_found=len(discrepancies),
        high_count=high,
        medium_count=medium,
        low_count=low,
    )


@app.get("/documents", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return db.query(Document).order_by(Document.uploaded_at.desc()).all()


@app.get("/documents/{doc_id}/claims", response_model=list[ClaimOut])
def get_claims(doc_id: str, db: Session = Depends(get_db)):
    return db.query(ExtractedClaim).filter(ExtractedClaim.document_id == doc_id).all()


@app.get("/discrepancies", response_model=list[DiscrepancyOut])
def get_discrepancies(db: Session = Depends(get_db)):
    discs = db.query(Discrepancy).order_by(Discrepancy.severity).all()
    result = []
    for d in discs:
        ca = db.query(ExtractedClaim).filter(ExtractedClaim.id == d.claim_a_id).first()
        cb = db.query(ExtractedClaim).filter(ExtractedClaim.id == d.claim_b_id).first()
        result.append(DiscrepancyOut(
            id=d.id, mismatch_type=d.mismatch_type, severity=d.severity,
            confidence=d.confidence, summary=d.summary, explanation=d.explanation,
            claim_a=ca, claim_b=cb, created_at=d.created_at,
        ))
    return result


@app.get("/audit/json")
def download_json_report(document_ids: list[str] = Query(), db: Session = Depends(get_db)):
    content = export_json(document_ids, db)
    return Response(content=content, media_type="application/json",
                    headers={"Content-Disposition": "attachment; filename=audit_report.json"})


@app.get("/audit/pdf")
def download_pdf_report(document_ids: list[str] = Query(), db: Session = Depends(get_db)):
    content = export_pdf_bytes(document_ids, db)
    return Response(content=content, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=audit_report.pdf"})
