from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import redis.asyncio as redis
import json
import asyncio
from datetime import datetime
import uuid

from dotenv import load_dotenv

load_dotenv()

from .agents.booking_client import BookingClient
from .agents.github_agent import github_agent
from .agents.weather_agent import WeatherAgent
from .a2a_runtime import A2ADispatcher
from .models.schemas import BookingRequest
from .utils.redis_client import RedisClient
from .utils.logger import get_logger, log_context
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel

app = FastAPI(title="A2A Booking Agent + Redis")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"])

# Redis connection (session store + SSE events)
r = redis.from_url("redis://localhost:6379")
logger = get_logger(__name__)


@app.on_event("startup")
async def startup():
    await r.flushdb()  # Clear Redis on startup
    await r.config_set("notify-keyspace-events", "AKE")  # Enable keyspace events
    app.state.redis_client = RedisClient()
    await app.state.redis_client.connect()
    app.state.a2a_dispatcher = A2ADispatcher(app.state.redis_client)
    app.state.a2a_task = asyncio.create_task(app.state.a2a_dispatcher.run())


@app.on_event("shutdown")
async def shutdown():
    task = getattr(app.state, "a2a_task", None)
    if task:
        task.cancel()


class GithubQuery(BaseModel):
    message: str


class WeatherQuery(BaseModel):
    city: str
    start_date: str | None = None
    end_date: str | None = None


class ChatLog(BaseModel):
    session_id: str
    role: str
    content: str
    agent: str | None = None
    data: object | None = None


async def _push_event(session_id: str, event: dict) -> None:
    event = {
        **event,
        "session_id": session_id,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }
    await r.rpush(f"events:{session_id}", json.dumps(event))
    await r.ltrim(f"events:{session_id}", 0, 99)
    await app.state.redis_client.log_chat(
        session_id=session_id,
        role="assistant",
        content=event.get("message", ""),
        agent=event.get("agent"),
        data=event.get("data"),
    )


async def _run_github_agent(session_id: str, message: str) -> None:
    with log_context(session_id=session_id, agent="github_agent"):
        logger.info("GitHub agent start: %s", message)
    await _push_event(session_id, {"agent": "github_agent", "message": "🔍 Looking up GitHub details..."})
    await app.state.redis_client.log_event(
        "agent_start",
        "github_agent",
        {"session_id": session_id, "message": message},
    )

    thread_id = session_id
    config = {"configurable": {"thread_id": thread_id}}
    messages = [HumanMessage(content=message)]

    def _stream_github() -> str:
        result = ""
        last_ai = None
        tool_chunks: list[str] = []
        for chunk in github_agent.stream({"messages": messages}, config, stream_mode="values"):
            if not chunk.get("messages"):
                continue
            last_msg = chunk["messages"][-1]
            if not hasattr(last_msg, "content") or not last_msg.content:
                continue
            content = last_msg.content
            if isinstance(content, list):
                parts: list[str] = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        parts.append(str(part.get("text", "")))
                    else:
                        parts.append(str(part))
                content = "\n".join(p for p in parts if p)
            else:
                content = str(content)
            if isinstance(last_msg, AIMessage):
                if content != last_ai:
                    last_ai = content
            else:
                tool_chunks.append(content)
        if last_ai:
            result = last_ai
        elif tool_chunks:
            # Fallback: return tool output once if no final AI message was produced
            result = "\n\n".join(tool_chunks)
        return result.strip()

    try:
        result = await asyncio.to_thread(_stream_github)
        if not result:
            result = "No response."
        await _push_event(session_id, {"agent": "github_agent", "message": result, "data": result})
        await app.state.redis_client.log_event(
            "chat",
            "github_agent",
            {"session_id": session_id, "message": result},
        )
        with log_context(session_id=session_id, agent="github_agent"):
            logger.info("GitHub agent complete")
    except Exception as e:
        await _push_event(session_id, {"agent": "github_agent", "message": f"⚠️ GitHub lookup failed: {e}"})
        await app.state.redis_client.log_event(
            "error",
            "github_agent",
            {"session_id": session_id, "error": str(e)},
        )
        with log_context(session_id=session_id, agent="github_agent"):
            logger.exception("GitHub agent error")


async def _run_weather_agent(session_id: str, city: str, start_date: str | None, end_date: str | None) -> None:
    agent = WeatherAgent()
    await _push_event(session_id, {"agent": "weather_agent", "message": "🌤️ Checking weather..."})
    try:
        summary = await agent.get_weather_summary(
            city,
            start_date or datetime.now().date().isoformat(),
            end_date or datetime.now().date().isoformat(),
        )
        await _push_event(
            session_id,
            {"agent": "weather_agent", "message": f"🌤️ {summary}", "data": summary},
        )
    except Exception as e:
        await _push_event(
            session_id,
            {"agent": "weather_agent", "message": f"⚠️ Weather lookup failed: {e}"},
        )


@app.post("/booking/start")
async def start_booking(request: BookingRequest):
    session_id = str(uuid.uuid4())

    # Store booking request in Redis
    await r.hset(f"session:{session_id}", mapping={
        "from_city": request.from_city,
        "to_city": request.to_city,
        "from_date": request.from_date,
        "to_date": request.to_date,
        "budget_min": str(request.budget_min),
        "budget_max": str(request.budget_max),
        "status": "active"
    })

    booking_client = BookingClient(session_id, app.state.redis_client)
    asyncio.create_task(booking_client.process_booking(request))

    return {"session_id": session_id, "status": "started"}


@app.post("/github/start")
async def github_start(query: GithubQuery):
    if not query.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    session_id = str(uuid.uuid4())
    await r.hset(
        f"session:{session_id}",
        mapping={"type": "github", "message": query.message, "status": "active"},
    )
    asyncio.create_task(_run_github_agent(session_id, query.message))
    return {"session_id": session_id, "status": "started"}


@app.post("/weather/start")
async def weather_start(query: WeatherQuery):
    if not query.city.strip():
        raise HTTPException(status_code=400, detail="city is required")

    session_id = str(uuid.uuid4())
    await r.hset(
        f"session:{session_id}",
        mapping={"type": "weather", "city": query.city, "status": "active"},
    )
    asyncio.create_task(_run_weather_agent(session_id, query.city, query.start_date, query.end_date))
    return {"session_id": session_id, "status": "started"}


@app.post("/chat/log")
async def chat_log(payload: ChatLog):
    await app.state.redis_client.log_chat(
        session_id=payload.session_id,
        role=payload.role,
        content=payload.content,
        agent=payload.agent,
        data=payload.data,
    )
    return {"status": "ok"}


@app.get("/sse/{session_id}")
async def sse_stream(session_id: str):
    async def generate_events():
        last_index = 0
        while True:
            total = await r.llen(f"events:{session_id}")
            if total < last_index:
                last_index = total

            events = await r.lrange(f"events:{session_id}", last_index, -1)
            if events:
                for raw in events:
                    if isinstance(raw, bytes):
                        raw = raw.decode()
                    event = json.loads(raw)
                    if "timestamp" not in event:
                        event["timestamp"] = datetime.now().strftime("%H:%M:%S")
                    yield f"data: {json.dumps(event)}\n\n"
                    last_index += 1
            else:
                await asyncio.sleep(0.5)

    return StreamingResponse(generate_events(), media_type="text/event-stream")


@app.get("/redis/{session_id}")
async def get_redis_data(session_id: str):
    events = await r.lrange(f"events:{session_id}", 0, -1)
    session = await r.hgetall(f"session:{session_id}")
    return {
        "events": [json.loads(e) for e in events],
        "session": {k.decode(): v.decode() for k, v in session.items()}
    }
