🚀 A2A Multi-Agent Travel Booking System
[
[
[
[

Real-time multi-agent travel booking platform featuring Flight, Hotel, and Weather agents powered by Google Gemini AI, Server-Sent Events (SSE), and Redis real-time data streaming.

✨ Key Features
Agent	🎯 Purpose	🛠️ Technology
✈️ Flight Agent	Dynamic flight search & pricing	Google Gemini 2.5 Flash
🏨 Hotel Agent	Hotel recommendations w/ pricing	Google Gemini 2.5 Flash
🌤️ Weather Agent	Live weather + travel advisories	OpenWeatherMap API
📡 SSE Streaming	Real-time agent communication	FastAPI Server-Sent Events
🐘 Redis Monitor	Live event persistence	Redis Streams
🖼️ Dynamic Images	Agent screenshot visualization	PIL/PNG generation
🎬 Live Demo Flow
text
1. Bangalore → Mumbai (2026-03-15, $200-1000 budget)
2. 🚀 "Book Trip" → Creates SSE session
3. ▶️ "Start Streaming" → Watch 3 agents work LIVE:
   ✈️ Flight Agent: AI123 ($349), 6E214 ($285)
   🏨 Hotel Agent: Taj Palace ($189/nt), ITC Grand ($229/nt)
   🌤️ Weather: Mumbai 28°C ☁️, "Light jacket recommended"
4. 🖼️ Agent screenshots + 📊 booking metrics appear instantly
🚀 Quick Start (3 Minutes)
Prerequisites
text
✅ Python 3.11+
✅ Free API Keys:
   • Gemini: https://aistudio.google.com/app/apikey
   • OpenWeatherMap: https://openweathermap.org/api (1000 calls/day FREE)
1. Setup Environment
bash
git clone <your-repo> && cd a2a-travel-booking
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate     # Windows
pip install -r requirements.txt
2. Configure API Keys
bash
cp .env.example .env
# Edit .env file:
# GEMINI_API_KEY=your_gemini_key_here
# WEATHER_API_KEY=your_openweather_key_here
3. Launch Stack
bash
# Terminal 1: Redis
redis-server --daemonize yes

# Terminal 2: FastAPI Backend + SSE
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 3: Streamlit Dashboard
streamlit run streamlit_ui.py --server.port 8501 --server.address 0.0.0.0
4. Open Dashboard
text
🌐 Main UI: http://localhost:8501
📚 API Docs: http://localhost:8000/docs
🏗️ System Architecture
text
graph TB
    A[Streamlit UI<br/>localhost:8501] 
    A --> B[FastAPI SSE<br/>localhost:8000]
    B --> C[Redis<br/>Event Store]
    B --> D[Flight Agent<br/>Gemini AI]
    B --> E[Hotel Agent<br/>Gemini AI]
    B --> F[Weather Agent<br/>OpenWeatherMap]
    D --> G[Dynamic Images<br/>PIL/PNG]
    E --> G
    F --> G
    G --> C
    C --> A
📁 Project Structure
text
a2a-travel-booking/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI + SSE endpoints
│   ├── models/
│   │   └── schemas.py             # Pydantic models
│   ├── agents/                    # LangGraph + Gemini agents
│   │   ├── flight_agent.py
│   │   ├── hotel_agent.py
│   │   └── weather_agent.py
│   └── executors/                 # A2A Agent Executors
│       ├── flight_agent_executor.py
│       ├── hotel_agent_executor.py
│       └── weather_agent_executor.py
├── streamlit_ui.py                # Real-time booking dashboard
├── utils/
│   ├── redis_client.py
│   └── logger.py
├── requirements.txt
├── .env.example
├── .env                           # ⚠️ ADD YOUR API KEYS
└── README.md
🛠️ Tech Stack
Component	Technology	Purpose
Frontend	Streamlit 1.38+	Real-time booking UI
Backend	FastAPI 0.115+	SSE streaming API
AI Engine	Google Gemini 2.5 Flash	Dynamic flight/hotel data
Database	Redis 7.x	Event persistence & pub/sub
Agents	LangGraph	Multi-agent orchestration
Weather	OpenWeatherMap API	Live weather forecasts
Images	PIL/Pillow	Dynamic agent screenshots
🔌 API Endpoints
bash
# Start booking session
curl -X POST "http://localhost:8000/booking/start" \
  -H "Content-Type: application/json" \
  -d '{
    "from_city": "Bangalore",
    "to_city": "Mumbai", 
    "from_date": "2026-03-15",
    "budget_min": 200,
    "budget_max": 1000
  }'

# Real-time SSE stream (data + images)
curl "http://localhost:8000/sse/session-123"

# Redis event monitor
curl "http://localhost:8000/redis/session-123"
📊 Sample SSE Events
json
// Flight Agent Data
{
  "agent": "flight_agent",
  "status": "complete",
  "flights": [
    {"flight_number": "AI123", "airline": "Air India", "price": 349}
  ],
  "timestamp": "10:42:15"
}

// Dynamic Image Event  
{
  "type": "image",
  "agent": "flight_agent",
  "image_b64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "data_summary": {"flights": 2}
}

// Weather Agent Data
{
  "agent": "weather_agent",
  "weather": {
    "city": "Mumbai",
    "temperature": 28.5,
    "condition": "Clouds",
    "humidity": 72
  }
}
🐘 Redis Monitoring Commands
bash
redis-cli

# View all events for session
> KEYS "events:session-*"
> LRANGE "events:session-123" 0 -1

# Session metadata
> HGETALL "session:session-123"

# Live monitoring
> MONITOR
🚀 Production Deployment
Docker Compose (Recommended)
text
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: ['./redis-data:/data']

  api:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [redis]

  streamlit:
    build: .
    ports: ["8501:8501"]
    command: streamlit run streamlit_ui.py --server.port 8501
    env_file: .env
    depends_on: [api, redis]
bash
```
docker-compose up -d
```
🔧 Development Workflow
bash
# Install dev tools
```
pip install -r requirements-dev.txt
```

# Code quality
```
black .
ruff check --fix .
pre-commit install
```

# Run tests
```
pytest tests/ -v
```

# Debug SSE stream
``` 
curl "http://localhost:8000/sse/debug" | jq
```

📦 Requirements
```
text
fastapi==0.115.0
uvicorn[standard]==0.30.6
streamlit==1.38.0
redis==5.0.8
google-generativeai==0.8.3
langgraph==0.2.20
pydantic==2.9.2
pillow==10.4.0
python-dotenv==1.0.1
requests==2.32.3
```

# .env
```
GOOGLE_API_KEY="your-api-key"
GOOGLE_GEMINI_API_KEY="your-api-key"
GEMINI_API_KEY="your-api-key"
REDIS_URL=redis://localhost:6379
REDIS_DB=0
LOG_LEVEL=INFO
A2A_CHANNEL=booking_a2a
```