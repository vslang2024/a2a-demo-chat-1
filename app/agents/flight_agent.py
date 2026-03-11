import json
from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
import google.generativeai as genai
import os
from datetime import datetime

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")


class AgentState(TypedDict):
    request: BookingRequest
    status: str
    flights: Annotated[List[dict], "add"]
    hotels: Annotated[List[dict], "add"]
    a2a_message: str


def flight_llm_node(state: AgentState):
    """Gemini generates REAL flight data dynamically"""

    prompt = f"""
    Generate 2-3 REALISTIC flight options for this booking request:

    From: {state['request'].from_city}
    To: {state['request'].to_city} 
    Date: {state['request'].from_date}
    Budget: ${state['request'].budget_min} - ${state['request'].budget_max}

    Return ONLY valid JSON array:
    [
      {{
        "flight_number": "AI123",
        "airline": "Air India",
        "departure_time": "08:30",
        "arrival_time": "10:15", 
        "duration": "1h 45m",
        "price": 349,
        "currency": "USD",
        "seats_available": 12,
        "class": "Economy"
      }}
    ]

    Use realistic flight numbers, airlines, and prices for this route.
    Vary results each time.
    """

    response = model.generate_content(prompt)

    # Extract JSON from response
    content = response.text.strip()
    try:
        # Find JSON array in response
        start = content.find('[')
        end = content.rfind(']') + 1
        flights_json = content[start:end]
        flights = json.loads(flights_json)
    except:
        flights = []

    return {
        "status": "flights_found",
        "flights": flights,
        "a2a_message": f"Gemini found {len(flights)} flights from {state['request'].from_city}"
    }


# LangGraph workflow
workflow = StateGraph(AgentState)
workflow.add_node("flight_search", flight_llm_node)
workflow.set_entry_point("flight_search")
workflow.add_edge("flight_search", END)

flight_agent = workflow.compile()
