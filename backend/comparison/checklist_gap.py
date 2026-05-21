"""
Checklist gap detection.

Required checklist items (from spec docs) are checked for presence in vendor submittal.
Uses the entity keys from regex_rules.CHECKLIST_ITEMS.
"""

from backend.extraction.regex_rules import CHECKLIST_ITEMS

SPEC_DOC_TYPES   = {"owner_spec", "control_spec"}
VENDOR_DOC_TYPES = {"vendor_submittal"}


def detect_checklist_gaps(claims_by_doc: dict[str, list], doc_types: dict[str, str]) -> list[dict]:
    checklist_by_doc: dict[str, set[str]] = {}
    claim_by_doc_item: dict[str, dict[str, object]] = {}

    for doc_id, claims in claims_by_doc.items():
        present = set()
        claim_map = {}
        for c in claims:
            if c.claim_type == "checklist":
                item_key = c.entity.replace("checklist_", "")
                present.add(item_key)
                claim_map[item_key] = c
        checklist_by_doc[doc_id] = present
        claim_by_doc_item[doc_id] = claim_map

    required_items: dict[str, object | None] = {}
    for doc_id, items in checklist_by_doc.items():
        if doc_types.get(doc_id) in SPEC_DOC_TYPES:
            for item in items:
                required_items[item] = claim_by_doc_item[doc_id].get(item)

    discrepancies = []
    for doc_id, items in checklist_by_doc.items():
        if doc_types.get(doc_id) not in VENDOR_DOC_TYPES:
            continue
        for required_item, source_claim in required_items.items():
            if required_item not in items:
                discrepancies.append({
                    "mismatch_type": "CHECKLIST_GAP",
                    "severity": "HIGH" if required_item in {
                        "remote_emergency_stop", "overcurrent_protection", "auto_start_on_power_loss"
                    } else "MEDIUM",
                    "confidence": 0.80,
                    "summary": (
                        f"Required item '{required_item.replace('_', ' ').title()}' "
                        f"present in spec but absent from vendor submittal"
                    ),
                    "claim_a": source_claim,
                    "claim_b": None,
                    "missing_in_doc_id": doc_id,
                })

    return discrepancies
