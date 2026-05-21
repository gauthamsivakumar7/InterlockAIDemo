from pydantic import BaseModel
from typing import Optional

class DocumentOut(BaseModel):
    id: str
    filename: str
    doc_type: str
    uploaded_at: str
    page_count: Optional[int]
    model_config = {"from_attributes": True}

class PageEvidenceOut(BaseModel):
    id: str
    document_id: str
    page_number: int
    text: Optional[str]
    extraction_method: str
    confidence: float
    model_config = {"from_attributes": True}

class ClaimOut(BaseModel):
    id: str
    document_id: str
    page_number: int
    claim_type: str
    entity: str
    parameter_name: str
    value_raw: str
    value_normalized: Optional[str]
    unit: Optional[str]
    condition: Optional[str]
    source_text: str
    extraction_method: str
    confidence: float
    model_config = {"from_attributes": True}

class DiscrepancyOut(BaseModel):
    id: str
    mismatch_type: str
    severity: str
    confidence: float
    summary: str
    explanation: Optional[str]
    claim_a: Optional[ClaimOut]
    claim_b: Optional[ClaimOut]
    created_at: str
    model_config = {"from_attributes": True}

class AnalysisResult(BaseModel):
    document_ids: list[str]
    claims_extracted: int
    discrepancies_found: int
    high_count: int
    medium_count: int
    low_count: int
