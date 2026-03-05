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
├── booking_Server.py
├── langgraph_orchestrator.py
├── redis_stream.py
├── streamlit_app.py
│
├── flight_agent/
│   ├── flight_agent.py
│   └── flight_agent_executor.py
│
├── hotel_agent/
│   ├── hotel_agent.py
│   └── hotel_agent_executor.py
│
├── logging_config.py
├── agent_card.py
├── .env
└── README.md
```

---

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
uvicorn flight_agent:app --port 8001 --reload
```

## Start Hotel Agent

```bash
uvicorn hotel_agent:app --port 8002 --reload
```

## Start Booking Orchestrator

```bash
uvicorn booking_Server:app --port 8000 --reload
```

## Start Streamlit UI

```bash
streamlit run streamlit_app.py
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