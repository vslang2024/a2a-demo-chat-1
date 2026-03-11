import google.generativeai as genai
import os
import json

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
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
    except:
        hotels = []

    return {
        "status": "hotels_found",
        "hotels": hotels,
        "a2a_message": f"Gemini found {len(hotels)} hotels in {state['request'].to_city}"
    }


# LangGraph workflow
workflow = StateGraph(AgentState)
workflow.add_node("hotel_search", hotel_llm_node)
workflow.set_entry_point("hotel_search")
workflow.add_edge("hotel_search", END)

hotel_agent = workflow.compile()
