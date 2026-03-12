# A2A Travel Booking System (LangGraph + Redis Pub/Sub + SSE)

## 📌 Overview

This project demonstrates an Agent-to-Agent (A2A) travel booking system built with:

- **FastAPI** (microservices)
- **LangGraph** (agent logic)
- **Redis Pub/Sub + Lists** (A2A messaging + session events)
- **Server-Sent Events (SSE)** (real-time streaming)
- **Streamlit** (frontend UI)
- **Google Gemini** (LLM-powered agents)

The system orchestrates:

1. ✈️ Flight Agent
2. 🏨 Hotel Agent
3. 🌤️ Weather Agent (MCP server)

The Booking Client sends A2A messages, an in-app A2A dispatcher runs the agents, SSE streams live updates, and Redis stores session events.

---

# 🏗️ Architecture

```
Streamlit UI
      ↓
Booking Server (FastAPI + SSE)
      ↓
Booking Client (A2A send)
      ↓
Redis Pub/Sub (A2A messages)
      ↓
A2A Dispatcher (in-app)
      ↓
Flight / Hotel / Weather Agents
      ↓
Redis Lists (session events)
```

### Event Flow

1. User submits booking request.
2. Booking server creates a session_id.
3. Booking Client publishes A2A messages for agents.
4. A2A Dispatcher runs agents and writes session events to Redis.
5. SSE endpoint streams those events to Streamlit.

---

# 📁 Project Structure

```
.
a2a-demo-chat-1/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI server
│   ├── a2a_runtime.py           # A2A dispatcher
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── flight_agent.py
│   │   ├── hotel_agent.py
│   │   ├── weather_agent.py
│   │   ├── booking_client.py
│   ├── executors/
│   │   ├── __init__.py
│   │   ├── flight_agent_executor.py
│   │   └── hotel_agent_executor.py
│   │   └── weather_agent_executor.py
│   ├── graph/
│   │   ├── __init__.py
│   │   └── booking_graph.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── redis_client.py
│   │   ├── logger.py
│   │   └── a2a_client.py
│   └── models/
│       ├── __init__.py
│       └── schemas.py
├── streamlit_ui.py
├── requirements.txt
├── run.sh
├── logs/
│   └── app.log (generated)
└── README.md


```

---
# Core Files

## requirements.txt
```
fastapi
uvicorn[standard]
streamlit
langgraph
langchain
langchain-core
langchain-google-genai
google-generativeai
redis
sse-starlette
python-multipart
python-dotenv
httpx
mcp
```

## .env
```
GEMINI_API_KEY=your_gemini_api_key_here
REDIS_URL=redis://localhost:6379
REDIS_DB=0
LOG_LEVEL=INFO
```

## Weather Agent (MCP, no API key)

This project uses a local MCP weather server that relies on Open-Meteo and does not require an API key.

Install and run the MCP server:

```bash
python -m pip install mcp_weather_server
python -m mcp_weather_server --mode streamable-http --host 0.0.0.0 --port 8080
```

Optional env var (default shown):

```
MCP_WEATHER_URL=http://localhost:8080/mcp
```


# ⚙️ Setup Instructions

## 1️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 2️⃣ Start Redis

Make sure Redis is running locally:

```bash
redis-server
```

Or using Docker:

```bash
docker run -p 6379:6379 redis
```

---

## 3️⃣ Configure Environment Variables

Create a `.env` file:

```
GEMINI_API_KEY=your_gemini_api_key
REDIS_URL=redis://localhost:6379
MCP_WEATHER_URL=http://localhost:8080/mcp
```

---

# 🚀 Running the Services

## 1️⃣ Start MCP Weather Server

```bash
python -m pip install mcp_weather_server
python -m mcp_weather_server --mode streamable-http --host 0.0.0.0 --port 8080
```

## 2️⃣ Start API

```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 3️⃣ Start Streamlit UI

```bash
streamlit run streamlit_ui.py
```

---

# 🔄 API Endpoints

## POST /booking/start

Triggers booking workflow.

Request:

```json
{
  "from_city": "New York",
  "to_city": "Paris",
  "from_date": "2026-05-01",
  "to_date": "2026-05-10",
  "budget_min": 1000,
  "budget_max": 3000
}
```

Response:

```json
{
  "session_id": "uuid"
}
```

---

## GET /sse/{session_id}

Streams live booking updates via SSE.

Content-Type:

```
text/event-stream
```

---

## GET /redis/{session_id}

Returns latest session data and events stored in Redis.

---

# 🧠 Key Concepts

## Redis Pub/Sub + Lists

A2A uses pub/sub on `booking_a2a`, and session events are appended to:

```
events:{session_id}
```

SSE streams the list to the UI.

---

## Server-Sent Events (SSE)

The booking server exposes a streaming endpoint:

```python
last_id = "$"
```

This ensures:

- No replay loops
- Only new events are streamed
- Clean real-time UI updates

---

## Async Architecture

All agents and Redis interactions are async:

```python
async def run_flight_agent(payload: dict):
    await publish_event(...)
```

This ensures:

- No blocking calls
- Proper event persistence
- Correct SSE streaming

---

# 🐞 Common Issues & Fixes

### 1. Logs Looping
Cause: `last_id = "0-0"`
Fix: Use `last_id = "$"`

---

### 2. Events Not Streaming
Cause: Missing `await` before `publish_event()`
Fix:

```python
await publish_event(ses


# A2A Travel Demo

## Quick Start
```bash
# 1. Generate agent cards
python agent_card.py

# 2. Terminal 1 - Flight Agent
cd flight_agent && pip install -r requirements.txt
uvicorn flight_agent:app --port 5001 --reload

# 3. Terminal 2 - Hotel Agent  
cd hotel_agent && pip install -r requirements.txt
uvicorn hotel_agent:app --port 5002 --reload

# 4. Terminal 3 - Main App
pip install -r requirements.txt
streamlit run streamlit_app.py


A2A Multi-Agent Travel Booking System

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Google_Gemini-FBC02D?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)

Real-time multi-agent booking system with Flight, Hotel, and Weather agents powered by Google Gemini AI + Server-Sent Events (SSE) + Redis.

LIVE DEMO FEATURES

Agent              | Purpose                    | Technology
------------------|----------------------------|------------------
✈️ Flight Agent    | Dynamic flight options     | Gemini 2.5 Flash
🏨 Hotel Agent     | Hotel recommendations      | Gemini 2.5 Flash  
🌤️ Weather Agent  | Live weather + travel tips | OpenWeatherMap API
📡 SSE Streaming   | Real-time agent comms      | FastAPI SSE
🐘 Redis           | Event persistence          | Redis Streams

QUICK START (3 Minutes)

Prerequisites:
- Python 3.11+
- Free API Keys:
  * Gemini: https://aistudio.google.com/app/apikey
  * OpenWeather: https://openweathermap.org/api (1000 calls/day FREE)

1. Clone & Install:
git clone <your-repo> && cd a2a-travel-booking
python -m venv .venv
source .venv/bin/activate # Linux/Mac

.venv\Scripts\activate # Windows
pip install -r requirements.txt

text

2. Setup Environment:
cp .env.example .env

Edit .env:
GEMINI_API_KEY=your_gemini_key
WEATHER_API_KEY=your_openweather_key
text

3. Launch Services:
Terminal 1: Redis
redis-server --daemonize yes

Terminal 2: FastAPI Backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

Terminal 3: Streamlit UI
streamlit run streamlit_ui.py --server.port 8501

text

4. Open Demo:
🌐 UI: http://localhost:8501
📚 API Docs: http://localhost:8000/docs

text

USAGE WORKFLOW

1. Bangalore → Mumbai | 2026-03-15 | Budget $200-1000
2. "🚀 Book Trip" → Session created
3. "▶️ Start Streaming" → Watch 3 agents work LIVE!

SYSTEM ARCHITECTURE

[Streamlit UI] --> [FastAPI SSE] --> [Redis Event Store]
|
+------------+------------+
| | |
[Flight] [Hotel Agent] [Weather Agent]
(Gemini) (Gemini) (OpenWeather)
| | |
+------------+------------+
|
[Redis Events]

text

PROJECT STRUCTURE

a2a-travel-booking/
├── app/
│ ├── main.py # FastAPI SSE server
│ ├── executors/ # A2A Agent Executors
│ │ ├── flight_agent_executor.py
│ │ ├── hotel_agent_executor.py
│ │ └── weather_agent_executor.py
│ └── agents/ # LangGraph + Gemini
│ ├── flight_agent.py
│ ├── hotel_agent.py
│ └── weather_agent.py
├── streamlit_ui.py # Real-time booking dashboard
├── requirements.txt
├── .env.example
└── README.md

text

TECH STACK

Frontend: Streamlit 1.38.0
Backend: FastAPI + Uvicorn 0.115.0
AI: Google Gemini 2.5 Flash
Database: Redis 7.x
Agents: LangGraph
Weather: OpenWeatherMap API (Free)

API ENDPOINTS

POST /booking/start           # Start booking session
GET  /sse/{session_id}        # Real-time SSE stream  
GET  /redis/{session_id}      # Redis event monitor

FastAPI Docs: http://localhost:8000/docs

REAL-TIME SSE EVENTS

{
  "agent": "flight_agent",
  "status": "complete",
  "flights": [
    {"flight_number": "AI123", "airline": "Air India", "price": 349}
  ],
  "timestamp": "10:35:22"
}

REDIS MONITORING

redis-cli
> KEYS events:*
> LRANGE events:session-123 0 -1
> HGETALL "session:session-123"

PRODUCTION DEPLOYMENT (Docker Compose)

version: '3.8'
services:
redis:
image: redis:7-alpine
ports: ["6379:6379"]
api:
build: .
ports: ["8000:8000"]
env_file: .env
streamlit:
build: .
ports: ["8501:8501"]
command: streamlit run streamlit_ui.py --server.port 8501

text

docker-compose up -d



---

## Logging (optional)

```
LOG_LEVEL=INFO
LOG_JSON=false
LOG_DIR=logs
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5
```
