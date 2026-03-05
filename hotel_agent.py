from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from hotel_agent_executor import run_hotel_agent_stream  # streaming version
from agent_card import AgentCard
import json

app = FastAPI(title="Hotel Agent")

agent_card = AgentCard(
    name="hotel_agent",
    description="Provides hotel booking options",
    endpoint="/stream",
    capabilities=["hotel_search"]
)

@app.get("/agent-card")
def get_card():
    return agent_card.dict()

@app.post("/stream")
async def stream_invoke(payload: dict):
    async def event_generator():
        # Async generator yields partial hotel results
        async for chunk in run_hotel_agent_stream(payload):
            yield json.dumps(chunk) + "\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")