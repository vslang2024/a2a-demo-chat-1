from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from flight_agent_executor import run_flight_agent_stream  # a streaming version of your agent
from agent_card import AgentCard
import asyncio
import json

app = FastAPI(title="Flight Agent")

agent_card = AgentCard(
    name="flight_agent",
    description="Provides flight booking options",
    endpoint="/invoke",
    capabilities=["flight_search"]
)

@app.get("/agent-card")
def get_card():
    return agent_card.dict()

@app.post("/stream")
async def stream_invoke(payload: dict):
    async def event_generator():
        # Assume run_flight_agent_stream is an async generator
        async for chunk in run_flight_agent_stream(payload):
            # Each chunk is sent as a JSON string
            yield json.dumps(chunk) + "\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")