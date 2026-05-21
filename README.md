# InterLock AI Build Challenge — Review Console

Cross-document discrepancy detection for engineering PDFs.
Every flag is grounded in source evidence. Every claim is inspectable. The system assists engineering judgment — it does not replace it.

## One-command run

```bash
cp .env.example .env
# Add your OPENAI_API_KEY to .env
bash run.sh
```

Then open: http://localhost:8501

## Architecture

PDF Upload → Ingestion (pdfplumber + OCR) → Hybrid Extraction (regex → Claude normalize)
→ Claim Store (SQLite) → Comparison Engine (deterministic) → LLM Explanation → Review UI

## LLM role

The LLM is used for exactly two things:

1. Normalizing and classifying ambiguous values from verbatim source snippets (bounded)
2. Writing cautious review-language explanations for discrepancies already found by the comparison engine

In this pipeline, the LLM never invents a discrepancy. All flag detection is deterministic.

## Sample PDFs

```bash
python sample_pdfs/download_samples.py
```

## Stack

Python · FastAPI · SQLite · SQLAlchemy · pdfplumber · pytesseract · Anthropic SDK · Streamlit · ReportLab
