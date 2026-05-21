from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey
from backend.database import Base

class Document(Base):
    __tablename__ = "documents"
    id          = Column(String, primary_key=True)
    filename    = Column(String, nullable=False)
    doc_type    = Column(String, nullable=False)
    uploaded_at = Column(String, nullable=False)
    page_count  = Column(Integer)
    file_size   = Column(Integer)

class PageEvidence(Base):
    __tablename__ = "page_evidence"
    id                = Column(String, primary_key=True)
    document_id       = Column(String, ForeignKey("documents.id"), nullable=False)
    page_number       = Column(Integer, nullable=False)
    text              = Column(Text)
    extraction_method = Column(String, nullable=False)
    confidence        = Column(Float, nullable=False)

class ExtractedClaim(Base):
    __tablename__ = "extracted_claims"
    id                = Column(String, primary_key=True)
    document_id       = Column(String, ForeignKey("documents.id"), nullable=False)
    page_number       = Column(Integer, nullable=False)
    claim_type        = Column(String, nullable=False)
    entity            = Column(String, nullable=False)
    parameter_name    = Column(String, nullable=False)
    value_raw         = Column(Text, nullable=False)
    value_normalized  = Column(Text)
    unit              = Column(String)
    condition         = Column(Text)
    source_text       = Column(Text, nullable=False)
    extraction_method = Column(String, nullable=False)
    confidence        = Column(Float, nullable=False)

class Discrepancy(Base):
    __tablename__ = "discrepancies"
    id            = Column(String, primary_key=True)
    mismatch_type = Column(String, nullable=False)
    severity      = Column(String, nullable=False)
    confidence    = Column(Float, nullable=False)
    summary       = Column(Text, nullable=False)
    explanation   = Column(Text)
    claim_a_id    = Column(String, ForeignKey("extracted_claims.id"))
    claim_b_id    = Column(String, ForeignKey("extracted_claims.id"))
    created_at    = Column(String, nullable=False)
