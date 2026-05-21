"""
Numeric parameter mismatch detection.

For each entity that appears in 2+ documents with numeric values:
- Parse value_normalized to float
- Compare with relative tolerance
- Flag if difference exceeds threshold
"""

NUMERIC_THRESHOLDS: dict[str, float] = {
    "power_kw":          0.01,
    "power_ekw":         0.01,
    "power_kva":         0.01,
    "voltage":           0.01,
    "frequency":         0.005,
    "power_factor":      0.02,
    "runtime_minutes":   0.05,
    "engine_speed_rpm":  0.01,
}

DEFAULT_THRESHOLD = 0.02


def detect_parameter_mismatches(claims_by_doc: dict[str, list]) -> list[dict]:
    """
    claims_by_doc: {document_id: [ExtractedClaim, ...]}
    Returns list of discrepancy dicts (not yet saved).
    """
    from collections import defaultdict
    entity_map: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))

    for doc_id, claims in claims_by_doc.items():
        for claim in claims:
            if claim.claim_type == "parameter" and claim.value_normalized:
                entity_map[claim.entity][doc_id].append(claim)

    discrepancies = []

    for entity, by_doc in entity_map.items():
        if len(by_doc) < 2:
            continue
        threshold = NUMERIC_THRESHOLDS.get(entity, DEFAULT_THRESHOLD)

        docs_with_entity = list(by_doc.keys())
        for i in range(len(docs_with_entity)):
            for j in range(i + 1, len(docs_with_entity)):
                doc_a_id = docs_with_entity[i]
                doc_b_id = docs_with_entity[j]
                claim_a = by_doc[doc_a_id][0]
                claim_b = by_doc[doc_b_id][0]

                try:
                    val_a = float(claim_a.value_normalized.replace(",", ""))
                    val_b = float(claim_b.value_normalized.replace(",", ""))
                except (ValueError, AttributeError):
                    continue

                if val_a == 0 and val_b == 0:
                    continue

                rel_diff = abs(val_a - val_b) / max(abs(val_a), abs(val_b))
                if rel_diff <= threshold:
                    continue

                severity = "HIGH" if rel_diff > 0.10 else "MEDIUM" if rel_diff > 0.03 else "LOW"
                confidence = min(claim_a.confidence, claim_b.confidence) * (1.0 - rel_diff * 0.5)
                confidence = round(max(0.3, min(1.0, confidence)), 2)

                discrepancies.append({
                    "mismatch_type": "PARAMETER_MISMATCH",
                    "severity": severity,
                    "confidence": confidence,
                    "summary": (
                        f"{claim_a.parameter_name} differs: "
                        f"{claim_a.value_normalized} {claim_a.unit or ''} vs "
                        f"{claim_b.value_normalized} {claim_b.unit or ''} "
                        f"({rel_diff*100:.1f}% difference)"
                    ),
                    "claim_a": claim_a,
                    "claim_b": claim_b,
                })

    return discrepancies
