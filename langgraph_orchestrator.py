import os
from dotenv import load_dotenv
from redis_stream import publish_event
from logging_config import setup_logger  # your existing logger
import httpx
from langgraph.graph import StateGraph
import json

load_dotenv()
logger = setup_logger()

FLIGHT_AGENT_URL = os.getenv("FLIGHT_AGENT_URL")
HOTEL_AGENT_URL = os.getenv("HOTEL_AGENT_URL")


# ---- Flight Node (streaming) ----
async def flight_node(state: dict):
    session_id = state["session_id"]
    logger.info(f"[{session_id}] Flight node started")

    await publish_event(session_id, {
        "type": "info",
        "agent": "flight",
        "message": "Calling flight agent (stream)"
    })

    flight_result = {"chunks": []}

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{FLIGHT_AGENT_URL}/stream",
                json=state
            ) as response:
                async for line in response.aiter_lines():
                    if not line.strip() or line.startswith(":"):
                        continue
                    try:
                        chunk = json.loads(line.strip())
                    except json.JSONDecodeError:
                        chunk = {"error": f"Invalid JSON: {line.strip()}"}
                        logger.warning(f"[{session_id}] Invalid JSON chunk: {line.strip()}")

                    flight_result["chunks"].append(chunk)

                    await publish_event(session_id, {
                        "type": "chunk",
                        "agent": "flight",
                        "data": chunk
                    })
                    logger.debug(f"[{session_id}] Published flight chunk: {chunk}")

        logger.info(f"[{session_id}] Flight node completed")
        return {**state, "flight": flight_result}

    except Exception as e:
        await publish_event(session_id, {
            "type": "error",
            "agent": "flight",
            "message": str(e)
        })
        logger.error(f"[{session_id}] Flight node error: {e}", exc_info=True)
        raise


# ---- Hotel Node (streaming) ----
async def hotel_node(state: dict):
    session_id = state["session_id"]
    logger.info(f"[{session_id}] Hotel node started")

    await publish_event(session_id, {
        "type": "info",
        "agent": "hotel",
        "message": "Calling hotel agent (stream)"
    })

    hotel_result = {"chunks": []}

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{HOTEL_AGENT_URL}/stream",
                json=state
            ) as response:
                async for line in response.aiter_lines():
                    if not line.strip() or line.startswith(":"):
                        continue
                    try:
                        chunk = json.loads(line.strip())
                    except json.JSONDecodeError:
                        chunk = {"error": f"Invalid JSON: {line.strip()}"}
                        logger.warning(f"[{session_id}] Invalid JSON chunk: {line.strip()}")

                    hotel_result["chunks"].append(chunk)

                    await publish_event(session_id, {
                        "type": "chunk",
                        "agent": "hotel",
                        "data": chunk
                    })
                    logger.debug(f"[{session_id}] Published hotel chunk: {chunk}")

        logger.info(f"[{session_id}] Hotel node completed")
        return {**state, "hotel": hotel_result}

    except Exception as e:
        await publish_event(session_id, {
            "type": "error",
            "agent": "hotel",
            "message": str(e)
        })
        logger.error(f"[{session_id}] Hotel node error: {e}", exc_info=True)
        raise


# ---- Graph Builder ----
def build_graph():
    workflow = StateGraph(dict)

    workflow.add_node("flight", flight_node)
    workflow.add_node("hotel", hotel_node)

    workflow.set_entry_point("flight")
    workflow.add_edge("flight", "hotel")
    workflow.set_finish_point("hotel")

    logger.info("Workflow graph built successfully")
    return workflow.compile()