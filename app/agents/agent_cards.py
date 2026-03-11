from typing import Dict, Any

AGENT_CARDS = {
    "flight_agent": {
        "name": "Flight Agent",
        "emoji": "✈️",
        "color": "#f093fb",
        "description": "Searches and books flights"
    },
    "hotel_agent": {
        "name": "Hotel Agent",
        "emoji": "🏨",
        "color": "#4facfe",
        "description": "Finds and books hotels"
    },
    "booking_client": {
        "name": "Booking Client",
        "emoji": "🎫",
        "color": "#43e97b",
        "description": "Coordinates all bookings"
    }
}

def get_agent_card(agent_id: str) -> Dict[str, Any]:
    return AGENT_CARDS.get(agent_id, {})
