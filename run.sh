#!/bin/bash
set -euo pipefail

echo "🚀 Starting A2A Booking Agent System..."

# Activate virtualenv
source .venv/bin/activate

# Start Redis (background)
redis-server --daemonize yes

# Wait for Redis
sleep 2

# Start FastAPI + Streamlit
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

streamlit run streamlit_ui.py --server.port 8501 --server.address 0.0.0.0 &
UI_PID=$!

echo "✅ API running at http://localhost:8000"
echo "📱 UI running at http://localhost:8501"

trap "kill ${API_PID} ${UI_PID} 2>/dev/null || true" EXIT
wait
