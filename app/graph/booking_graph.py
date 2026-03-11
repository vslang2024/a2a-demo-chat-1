from langgraph.graph import StateGraph, END
from typing import TypedDict
from ..models.schemas import BookingRequest
from ..utils.logger import logger

class BookingGraphState(TypedDict):
    request: BookingRequest
    session_id: str
    status: str
    results: dict

def coordinate_node(state: BookingGraphState):
    logger.info(f"Booking graph coordinating session {state['session_id']}")
    return {
        "status": "coordination_complete",
        "results": {"flights": "booked", "hotels": "booked"}
    }

graph = StateGraph(BookingGraphState)
graph.add_node("coordinate", coordinate_node)
graph.set_entry_point("coordinate")
graph.add_edge("coordinate", END)

booking_graph = graph.compile()
