"""
LLM explanation pass — runs AFTER all discrepancies are found deterministically.

LLM's only job here: write cautious, 2-3 sentence engineering review language
explaining why a pre-found discrepancy matters.
It is given the two source snippets verbatim. It cannot invent a flag.
"""

import logging
from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI()

EXPLAINER_SYSTEM = """You are a cautious engineering document reviewer.
You will be given two cited source excerpts from engineering documents that contain a potential discrepancy.
Write 2-3 sentences explaining:
1. What the discrepancy is and why it matters for engineering review
2. What an engineer should verify before proceeding

Rules:
- Never say which document is correct
- Never make a compliance judgment or certification claim
- Use cautious language: "appears to", "may require", "should be verified"
- Do not recommend a specific fix — recommend review
- Keep it under 60 words"""


def generate_explanation(mismatch_type: str, claim_a, claim_b, doc_a_name: str, doc_b_name: str | None) -> str:
    """Generate a cautious explanation for a pre-found discrepancy."""

    if claim_b is None:
        user_msg = f"""Discrepancy type: {mismatch_type}

Document A ({doc_a_name}) requires: "{claim_a.source_text}"

This requirement appears to be absent from the vendor submittal. Explain why this gap should be reviewed."""
    else:
        user_msg = f"""Discrepancy type: {mismatch_type}

Document A ({doc_a_name}), page {claim_a.page_number}:
"{claim_a.source_text}"

Document B ({doc_b_name}), page {claim_b.page_number}:
"{claim_b.source_text}"

These two claims appear to conflict. Explain why this should be reviewed."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=150,
            messages=[
                {"role": "system", "content": EXPLAINER_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Explainer failed: {e}")
        return f"A potential {mismatch_type.lower().replace('_', ' ')} was detected. Review source documents before proceeding."
