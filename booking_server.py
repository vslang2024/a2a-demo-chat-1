from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import asyncio
import uuid

from langgraph_orchestrator import build_graph
from redis_stream import publish_event, redis_client

app = FastAPI(title="Booking Orchestrator")

graph = build_graph()


# -------------------------
# Background Graph Runner
# -------------------------
async def run_graph(payload: dict, session_id: str):
    try:
        payload["session_id"] = session_id

        result = await graph.ainvoke(payload)

        await publish_event(session_id, {
            "type": "final",
            "data": result
        })

    except Exception as e:
        await publish_event(session_id, {
            "type": "error",
            "message": str(e)
        })


# -------------------------
# Trigger Orchestration
# -------------------------
@app.post("/book")
async def book(payload: dict):
    session_id = str(uuid.uuid4())

    asyncio.create_task(run_graph(payload, session_id))

    return {"session_id": session_id}


# -------------------------
# SSE Stream Endpoint
# -------------------------
@app.get("/events/{session_id}")
async def stream_events(request: Request, session_id: str):

    async def event_generator():
        stream_key = f"session:{session_id}"

        # 🔥 CRITICAL FIX:
        # Start from NEW messages only (prevents infinite replay loop)
        last_id = "$"

        while True:
            if await request.is_disconnected():
                break

            results = await redis_client.xread(
                streams={stream_key: last_id},
                block=5000,
                count=10
            )

            if results:
                for _, messages in results:
                    for message_id, fields in messages:
                        last_id = message_id
                        yield f"data: {fields['data']}\n\n"
            else:
                # keep-alive ping
                yield ": keep-alive\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )