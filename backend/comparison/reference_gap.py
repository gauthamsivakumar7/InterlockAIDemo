"""
Standards reference gap detection.

Takes the union of all references from 'owner_spec' and 'control_spec' documents
as the required set. Flags any required reference absent from 'vendor_submittal'.
Also flags direct conflicts (e.g. UL 508A in spec A but not spec B).
"""

SPEC_DOC_TYPES = {"owner_spec", "control_spec"}
VENDOR_DOC_TYPES = {"vendor_submittal"}


def detect_reference_gaps(claims_by_doc: dict[str, list], doc_types: dict[str, str]) -> list[dict]:
    """
    doc_types: {document_id: doc_type}
    """
    refs_by_doc: dict[str, dict[str, object]] = {}
    for doc_id, claims in claims_by_doc.items():
        refs_by_doc[doc_id] = {
            c.value_normalized: c
            for c in claims
            if c.claim_type == "reference"
        }

    spec_docs   = {d: refs for d, refs in refs_by_doc.items() if doc_types.get(d) in SPEC_DOC_TYPES}
    vendor_docs = {d: refs for d, refs in refs_by_doc.items() if doc_types.get(d) in VENDOR_DOC_TYPES}

    discrepancies = []

    required: dict[str, object] = {}
    for refs in spec_docs.values():
        required.update(refs)

    for vendor_id, vendor_refs in vendor_docs.items():
        for std_name, req_claim in required.items():
            if std_name not in vendor_refs:
                discrepancies.append({
                    "mismatch_type": "REFERENCE_GAP",
                    "severity": "MEDIUM",
                    "confidence": round(req_claim.confidence * 0.85, 2),
                    "summary": f"Required standard '{std_name}' present in spec but not cited in vendor submittal",
                    "claim_a": req_claim,
                    "claim_b": None,
                    "missing_in_doc_id": vendor_id,
                })

    spec_doc_list = list(spec_docs.keys())
    for i in range(len(spec_doc_list)):
        for j in range(i + 1, len(spec_doc_list)):
            refs_a = spec_docs[spec_doc_list[i]]
            refs_b = spec_docs[spec_doc_list[j]]
            only_in_a = set(refs_a) - set(refs_b)
            for std in only_in_a:
                discrepancies.append({
                    "mismatch_type": "REFERENCE_GAP",
                    "severity": "LOW",
                    "confidence": 0.75,
                    "summary": f"Standard '{std}' cited in one spec document but not the other",
                    "claim_a": refs_a[std],
                    "claim_b": None,
                })

    return discrepancies
