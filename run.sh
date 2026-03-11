#!/bin/bash
echo "🚀 Starting A2A Booking Agent System..."

# Activate virtualenv
source .venv/bin/activate

# Start Redis (background)
redis-server --daemonize yes &

# Wait for Redis
sleep 2

# Start FastAPI (using MODULE method - bulletproof)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

echo "✅ API running at http://localhost:8000"
echo "📱 UI: streamlit run streamlit_ui.py"
