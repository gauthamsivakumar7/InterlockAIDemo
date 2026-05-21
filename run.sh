#!/bin/bash
set -e
echo "Starting InterLock AI Demo..."
cp -n .env.example .env 2>/dev/null || true
pip install -r requirements.txt -q

# Download sample PDFs if missing
python sample_pdfs/download_samples.py

# Start FastAPI backend in background
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start Streamlit frontend
streamlit run frontend/app.py --server.port 8501

# Cleanup
kill $BACKEND_PID
