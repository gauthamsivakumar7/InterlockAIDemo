"""
Categorical / enum assumption conflict detection.

If the same entity appears in 2+ documents with different normalized enum values → flag.
"""

HIGH_SEVERITY_ENTITIES = {
    "generator_rating_type",
    "frequency",
    "operation_mode",
}


def detect_assumption_mismatches(claims_by_doc: dict[str, list]) -> list[dict]:
    from collections import defaultdict
    entity_map: dict[str, dict[str, object]] = defaultdict(dict)

    for doc_id, claims in claims_by_doc.items():
        for claim in claims:
            if claim.claim_type == "assumption" and claim.value_normalized:
                existing = entity_map[claim.entity].get(doc_id)
                if existing is None or claim.confidence > existing.confidence:
                    entity_map[claim.entity][doc_id] = claim

    discrepancies = []
    for entity, by_doc in entity_map.items():
        if len(by_doc) < 2:
            continue

        docs = list(by_doc.values())
        values = {c.value_normalized for c in docs}
        if len(values) == 1:
            continue

        doc_list = list(by_doc.values())
        for i in range(len(doc_list)):
            for j in range(i + 1, len(doc_list)):
                ca, cb = doc_list[i], doc_list[j]
                if ca.value_normalized == cb.value_normalized:
                    continue

                severity = "HIGH" if entity in HIGH_SEVERITY_ENTITIES else "MEDIUM"
                confidence = round(min(ca.confidence, cb.confidence), 2)

                discrepancies.append({
                    "mismatch_type": "ASSUMPTION_MISMATCH",
                    "severity": severity,
                    "confidence": confidence,
                    "summary": (
                        f"{ca.parameter_name} conflict: "
                        f"'{ca.value_normalized}' vs '{cb.value_normalized}'"
                    ),
                    "claim_a": ca,
                    "claim_b": cb,
                })

    return discrepancies
