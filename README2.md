# A2A Multi-Agent Travel Booking + GitHub + Weather

Real-time multi-agent demo with a Streamlit chat UI, FastAPI SSE backend, Redis event storage, and multiple agents:
flight, hotel, weather, and GitHub profile lookup.

## Key Agents

Agent | Purpose | Implementation
---|---|---
`flight_agent` | Generate sample flight options | Gemini (LangGraph)
`hotel_agent` | Generate sample hotel options | Gemini (LangGraph)
`weather_agent` | Weather summary for destination | MCP (optional) + Open-Meteo fallback
`github_agent` | GitHub profile details | Gemini tool + GitHub REST/GraphQL
`booking_client` | Orchestrates booking workflow | A2A runtime + Redis events

## Project Structure

```
a2a-demo-chat-1/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app + SSE + GitHub/Weather endpoints
│   ├── a2a_runtime.py             # A2A dispatcher for booking workflow
│   ├── agents/
│   │   ├── booking_client.py
│   │   ├── flight_agent.py
│   │   ├── hotel_agent.py
│   │   ├── weather_agent.py
│   │   └── github_agent.py
│   ├── executors/
│   │   ├── flight_agent_executor.py
│   │   ├── hotel_agent_executor.py
│   │   ├── weather_agent_executor.py
│   │   └── github_agent_executor.py
│   ├── models/
│   │   └── schemas.py
│   └── utils/
│       ├── a2a_client.py
│       ├── logger.py
│       └── redis_client.py
├── streamlit_ui.py                # Chat UI (booking + GitHub + weather)
├── run.sh                         # Starts Redis + API + Streamlit
├── requirements.txt
├── logs/
├── redis_stream.py
└── README.md
```

## Setup

### 1) Create venv and install deps

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Environment variables

Create a `.env` (optional but recommended):

```
# Gemini / Google
GEMINI_API_KEY=your_key
GOOGLE_API_KEY=your_key

# GitHub (optional, enables contribution totals)
GITHUB_TOKEN=your_token

# Weather MCP server (optional)
MCP_WEATHER_URL=http://localhost:8080/mcp

# Logging
LOG_LEVEL=INFO
```

## Run

### Option A: One command

```
./run.sh
```

### Option B: Manual (separate terminals)

Terminal 1:
```
redis-server --daemonize yes
```

Terminal 2:
```
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 3:
```
streamlit run streamlit_ui.py --server.port 8501 --server.address 0.0.0.0
```

### Optional: MCP Weather Server

If you want MCP weather instead of the Open-Meteo fallback:

```
python -m pip install mcp_weather_server
python -m mcp_weather_server --mode streamable-http --host 0.0.0.0 --port 8080
```

## UI

Open:
```
http://localhost:8501
```

## API Endpoints

```
POST /booking/start
POST /github/start
POST /weather/start
POST /chat/log
GET  /sse/{session_id}
GET  /redis/{session_id}
```

### Example: Booking
```
curl -X POST "http://localhost:8000/booking/start" \
  -H "Content-Type: application/json" \
  -d '{
    "from_city": "Bangalore",
    "to_city": "Chicago",
    "from_date": "2026-03-15",
    "to_date": "2026-03-18",
    "budget_min": 2000,
    "budget_max": 10000
  }'
```

### Example: GitHub
```
curl -X POST "http://localhost:8000/github/start" \
  -H "Content-Type: application/json" \
  -d '{"message":"Tell me about the GitHub user langchain-ai"}'
```

### Example: Weather
```
curl -X POST "http://localhost:8000/weather/start" \
  -H "Content-Type: application/json" \
  -d '{"city":"Chicago"}'
```

## Redis Data

```
events:{session_id}   # SSE events
chat:{session_id}     # Chat history
session:{session_id}  # Session metadata
```

## Notes

- Flight and hotel agents generate demo data (JSON output) via Gemini.
- Weather agent uses MCP if available, otherwise falls back to Open-Meteo.
- GitHub agent can show total contributions when `GITHUB_TOKEN` is set.
