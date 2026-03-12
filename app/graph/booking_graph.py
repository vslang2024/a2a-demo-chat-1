from langgraph.graph import StateGraph, END
from typing import TypedDict

from ..models.schemas import BookingRequest
from ..utils.logger import get_logger, log_context


logger = get_logger(__name__)


class BookingGraphState(TypedDict):
    request: BookingRequest
    session_id: str
    status: str
    results: dict


def coordinate_node(state: BookingGraphState):
    with log_context(session_id=state.get("session_id"), agent="booking_graph"):
        logger.info("Booking graph coordinating session")
    return {
        "status": "coordination_complete",
        "results": {"flights": "booked", "hotels": "booked"},
    }


graph = StateGraph(BookingGraphState)
graph.add_node("coordinate", coordinate_node)
graph.set_entry_point("coordinate")
graph.add_edge("coordinate", END)

booking_graph = graph.compile()
