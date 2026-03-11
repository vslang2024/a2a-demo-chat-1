import json
from typing import Dict, Any
from .redis_client import RedisClient
from .logger import logger


class A2AClient:
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self.channel = "booking_a2a"

    async def send_message(self, from_agent: str, to_agent: str, message: str, payload: Dict[str, Any]):
        msg = {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message": message,
            "payload": payload,
            "timestamp": str(datetime.utcnow().isoformat())
        }
        await self.redis.publish_a2a(self.channel, msg)
        logger.info(f"A2A: {from_agent} -> {to_agent}: {message}")

    async def listen_for_messages(self, agent_id: str):
        pubsub = await self.redis.subscribe_a2a(self.channel)
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                if data.get('to_agent') == agent_id:
                    yield data
