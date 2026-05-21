set -e
echo "Starting InterLock AI Demo..."
cp -n .env.example .env 2>/dev/null || true
pip install -r requirements.txt -q

python sample_pdfs/download_samples.py

uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

streamlit run frontend/app.py --server.port 8501

kill $BACKEND_PID
