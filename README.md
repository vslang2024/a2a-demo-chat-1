# A2A Travel Booking System (LangGraph + Redis Streams + SSE)

## 📌 Overview

This project demonstrates an Agent-to-Agent (A2A) travel booking system built with:

- **FastAPI** (microservices)
- **LangGraph** (orchestration layer)
- **Redis Streams** (persistent event storage)
- **Server-Sent Events (SSE)** (real-time streaming)
- **Streamlit** (frontend UI)
- **Google Gemini** (LLM-powered agents)

The system orchestrates:

1. ✈️ Flight Agent
2. 🏨 Hotel Agent

The Booking Orchestrator coordinates both agents, streams live updates via SSE, and persists all events in Redis.

---

# 🏗️ Architecture

```
Streamlit UI
      ↓
Booking Server (FastAPI + SSE)
      ↓
LangGraph Orchestrator
      ↓
Flight Agent (FastAPI)
      ↓
Hotel Agent (FastAPI)
      ↓
Redis Streams (Persistent Events)
```

### Event Flow

1. User submits booking request.
2. Booking server creates a session_id.
3. LangGraph invokes Flight → then Hotel.
4. Each agent publishes events to Redis Stream:
   - info
   - result
   - error
   - final
5. SSE endpoint streams live events to Streamlit.

---

# 📁 Project Structure

```
.
booking-agent-app/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI server
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── flight_agent.py
│   │   ├── hotel_agent.py
│   │   ├── booking_client.py
│   │   └── agent_cards.py
│   ├── executors/
│   │   ├── __init__.py
│   │   ├── flight_agent_executor.py
│   │   └── hotel_agent_executor.py
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
├── .env.example
├── .env
├── app.log (generated)
└── README.md


```

---
# Core Files

## requirements.txt
```
fastapi==0.115.0
uvicorn[standard]==0.32.0
streamlit==1.38.0
langgraph==0.2.20
langchain-google-genai==2.0.0
redis==5.2.1
pydantic==2.9.2
python-dotenv==1.0.1
httpx==0.27.0
sse-starlette==2.1.2
asyncio-mqtt==0.16.1
```

## .env
```
GOOGLE_API_KEY=your_gemini_api_key_here
REDIS_URL=redis://localhost:6379
REDIS_DB=0
LOG_LEVEL=INFO
```


# ⚙️ Setup Instructions

## 1️⃣ Install Dependencies

```bash
pip install fastapi uvicorn redis langgraph streamlit httpx python-dotenv google-generativeai sseclient
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
GOOGLE_API_KEY=your_gemini_api_key
REDIS_URL=redis://localhost:6379
FLIGHT_AGENT_URL=http://localhost:8001
HOTEL_AGENT_URL=http://localhost:8002
```

---

# 🚀 Running the Services

## Start Flight Agent

```bash
uvicorn agents:app --port 8001 --reload
```

## Start Hotel Agent

```bash
uvicorn hotel_agent:app --port 8002 --reload
```

## Start Booking Orchestrator

```bash
uvicorn booking_server:app --port 8000 --reload
```

## Start Streamlit UI

```bash
streamlit run streamlit_ui.py
```

---

# 🔄 API Endpoints

## POST /book

Triggers booking workflow.

Request:

```json
{
  "from": "New York",
  "to": "Paris",
  "from_date": "2026-05-01",
  "to_date": "2026-05-10",
  "budget": "3000"
}
```

Response:

```json
{
  "session_id": "uuid"
}
```

---

## GET /events/{session_id}

Streams live booking updates via SSE.

Content-Type:

```
text/event-stream
```

---

# 🧠 Key Concepts

## Redis Streams (Persistent Events)

Each session writes to:

```
session:{session_id}
```

Events are stored using `XADD` and streamed using `XREAD`.

Benefits:

- Durable event history
- Replay capability
- Scalable event architecture

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


