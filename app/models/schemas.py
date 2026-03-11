from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import date

class BookingRequest(BaseModel):
    from_city: str = Field(..., description="Departure city")
    to_city: str = Field(..., description="Destination city")
    from_date: str = Field(..., description="Travel start date")
    to_date: str = Field(..., description="Travel end date")
    budget_min: float = Field(..., ge=0, description="Minimum budget")
    budget_max: float = Field(..., gt=0, description="Maximum budget")

class AgentEvent(BaseModel):
    agent_id: str
    event_type: str
    data: Dict[str, Any]
    timestamp: str

class A2AMessage(BaseModel):
    from_agent: str
    to_agent: str
    message: str
    payload: Dict[str, Any]
