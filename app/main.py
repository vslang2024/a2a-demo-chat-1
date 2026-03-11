from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import redis.asyncio as redis
import json
import asyncio
from datetime import datetime
from pydantic import BaseModel
import uuid

app = FastAPI(title="A2A Booking Agent + Redis")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"])

# Redis connection
r = redis.from_url("redis://localhost:6379")


class BookingRequest(BaseModel):
    from_city: str
    to_city: str
    from_date: str
    to_date: str
    budget_min: float
    budget_max: float


@app.on_event("startup")
async def startup():
    await r.flushdb()  # Clear Redis on startup
    await r.config_set("notify-keyspace-events", "AKE")  # Enable keyspace events


@app.post("/booking/start")
async def start_booking(request: BookingRequest):
    session_id = str(uuid.uuid4())

    # Store booking request in Redis
    await r.hset(f"session:{session_id}", mapping={
        "from_city": request.from_city,
        "to_city": request.to_city,
        "status": "active"
    })

    return {"session_id": session_id, "status": "started"}


@app.get("/sse/{session_id}")
async def sse_stream(session_id: str):
    async def generate_events():
        events = [
            {"agent": "flight_agent", "message": "🔍 Searching flights...", "session_id": session_id},
            {"agent": "hotel_agent", "message": "🔍 Searching hotels...", "session_id": session_id},
            {"agent": "flight_agent", "message": f"✈️ Found AI123 BLR→BOM ($349)", "session_id": session_id},
            {"agent": "hotel_agent", "message": f"🏨 Taj Palace BOM ($189/night)", "session_id": session_id},
            {"agent": "booking_client", "message": "🤝 Coordinating options...", "session_id": session_id},
            {"agent": "booking_client", "message": "✅ Booking confirmed! Total $538", "session_id": session_id}
        ]

        for event in events:
            event["timestamp"] = datetime.now().strftime("%H:%M:%S")

            # Store in Redis list
            await r.rpush(f"events:{session_id}", json.dumps(event))
            await r.ltrim(f"events:{session_id}", 0, 99)  # Keep last 100

            yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(1.5)

    return StreamingResponse(generate_events(), media_type="text/event-stream")


@app.get("/redis/{session_id}")
async def get_redis_data(session_id: str):
    events = await r.lrange(f"events:{session_id}", 0, -1)
    session = await r.hgetall(f"session:{session_id}")
    return {
        "events": [json.loads(e) for e in events],
        "session": {k.decode(): v.decode() for k, v in session.items()}
    }
