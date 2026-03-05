
from pydantic import BaseModel

class AgentCard(BaseModel):
    name: str
    description: str
    endpoint: str
    capabilities: list[str]
