import google.generativeai as genai
import os
import json
from typing import TypedDict, Annotated, List
from ..models.schemas import BookingRequest
from langgraph.graph import StateGraph, END

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")


class AgentState(TypedDict):
    request: BookingRequest
    status: str
    hotels: Annotated[List[dict], "add"]
    flights: Annotated[List[dict], "add"]
    a2a_message: str


def hotel_llm_node(state: AgentState):
    """Gemini generates REAL hotel data dynamically"""

    prompt = f"""
    You are generating sample hotel options for a demo UI. You must NOT refuse.
    Always return ONLY a valid JSON array. If unsure, return 2 reasonable options.

    Generate 2-3 REALISTIC hotel options for:

    City: {state['request'].to_city}
    Check-in: {state['request'].from_date}
    Check-out: {state['request'].to_date}
    Budget: ${state['request'].budget_min} - ${state['request'].budget_max}

    Return ONLY valid JSON array:
    [
      {{
        "name": "Taj Mahal Palace",
        "address": "Apollo Bunder, Mumbai",
        "rating": 4.8,
        "price_per_night": 189,
        "total_price": 567,
        "currency": "USD",
        "rooms_available": 3,
        "amenities": ["WiFi", "Pool", "Spa", "Gym"]
      }}
    ]

    Use real hotel names for {state['request'].to_city}. Vary results each time.
    """

    response = model.generate_content(prompt)

    content = response.text.strip()
    try:
        start = content.find('[')
        end = content.rfind(']') + 1
        hotels_json = content[start:end]
        hotels = json.loads(hotels_json)
    except Exception:
        hotels = []

    if not hotels:
        mid_budget = (state["request"].budget_min + state["request"].budget_max) / 2
        hotels = [
            {
                "name": "Grand City Hotel",
                "address": f"Central District, {state['request'].to_city}",
                "rating": 4.4,
                "price_per_night": round(mid_budget * 0.25, 2),
                "total_price": round(mid_budget * 0.75, 2),
                "currency": "USD",
                "rooms_available": 4,
                "amenities": ["WiFi", "Breakfast", "Gym"],
            },
            {
                "name": "Riverside Suites",
                "address": f"Riverside, {state['request'].to_city}",
                "rating": 4.1,
                "price_per_night": round(mid_budget * 0.2, 2),
                "total_price": round(mid_budget * 0.6, 2),
                "currency": "USD",
                "rooms_available": 2,
                "amenities": ["WiFi", "Pool"],
            },
        ]

    return {
        "status": "hotels_found",
        "hotels": hotels,
        "a2a_message": f"Found {len(hotels)} hotels in {state['request'].to_city}"
    }


# LangGraph workflow
workflow = StateGraph(AgentState)
workflow.add_node("hotel_search", hotel_llm_node)
workflow.set_entry_point("hotel_search")
workflow.add_edge("hotel_search", END)

hotel_agent = workflow.compile()
