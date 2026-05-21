"""
LLM-powered normalization pass.

IMPORTANT DESIGN CONSTRAINT:
- The LLM receives only verbatim source snippets from the document.
- The LLM may NOT invent values. Its only job is to normalize and classify
  what is already present in the provided text.
- This runs AFTER regex. It handles edge cases regex missed.
- Returns JSON objects.
"""

import json
import re
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI()

NORMALIZATION_SYSTEM = """You are a structured data extractor for industrial engineering documents.

You will receive a page of text from an engineering PDF. Extract structured claims ONLY from the text provided.

CRITICAL RULES:
1. Extract ONLY values explicitly stated in the provided text. Never infer or assume.
2. If a value is ambiguous, set confidence to 0.5 or lower.
3. Do not duplicate claims already obvious from regex (kW, kVA, Hz, V are already captured).
4. Focus on: ambient temperature ranges, altitude/elevation limits, fuel consumption rates,
   coolant type, noise levels (dBA), emissions ratings, IP/NEMA enclosure ratings,
   warranty terms, cooling type (air/liquid), starting system details.

Return ONLY a JSON array. Each object:
{
  "claim_type": "parameter" | "assumption" | "reference" | "checklist",
  "entity": "<snake_case concept key>",
  "parameter_name": "<human readable name>",
  "value_raw": "<exactly as written>",
  "value_normalized": "<normalized form>",
  "unit": "<unit or null>",
  "condition": "<operating condition or null>",
  "source_text": "<verbatim sentence containing the value, max 200 chars>",
  "confidence": <0.0–1.0>
}

Return [] if nothing new to add. No preamble. No markdown. Only the JSON array."""


def llm_normalize_page(page_text: str, page_number: int, document_id: str) -> list[dict]:
    """
    Run LLM normalization on a page. Only called for pages where regex
    extraction yielded fewer than expected claims, OR after all regex runs,
    to catch remaining structured values.
    """
    if len(page_text.strip()) < 50:
        return []

    truncated = page_text[:3000]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1024,
            messages=[
                {"role": "system", "content": NORMALIZATION_SYSTEM},
                {"role": "user", "content": f"Extract claims from this page:\n\n{truncated}"},
            ],
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        items = json.loads(raw)
    except Exception as e:
        logger.warning(f"LLM normalization failed page {page_number}: {e}")
        return []

    claims = []
    for item in items:
        try:
            claims.append({
                "document_id": document_id,
                "page_number": page_number,
                "claim_type": item.get("claim_type", "parameter"),
                "entity": item.get("entity", "unknown"),
                "parameter_name": item.get("parameter_name", ""),
                "value_raw": item.get("value_raw", ""),
                "value_normalized": item.get("value_normalized"),
                "unit": item.get("unit"),
                "condition": item.get("condition"),
                "source_text": item.get("source_text", "")[:500],
                "extraction_method": "llm",
                "confidence": float(item.get("confidence", 0.7)),
            })
        except Exception:
            continue

    return claims
