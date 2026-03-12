import json
from datetime import datetime
from typing import List, Dict, Any

import redis.asyncio as redis

from .logger import get_logger, log_context


logger = get_logger(__name__)


class RedisClient:
    def __init__(self, redis_url: str = None, db: int = 0):
        self.redis_url = redis_url or "redis://localhost:6379"
        self.db = db
        self.client = None

    async def connect(self):
        self.client = redis.from_url(self.redis_url, db=self.db, decode_responses=True)
        await self.client.ping()
        logger.info("Connected to Redis")

    async def log_event(self, event_type: str, agent_id: str, data: Dict[str, Any]):
        if not self.client:
            await self.connect()

        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": agent_id,
            "event_type": event_type,
            "data": data,
        }

        await self.client.lpush(f"events:{agent_id}", json.dumps(event))
        await self.client.ltrim(f"events:{agent_id}", 0, 999)

        session_id = None
        if isinstance(data, dict):
            session_id = data.get("session_id")

        with log_context(session_id=session_id, agent=agent_id):
            logger.info(
                "Logged event",
                extra={"extra_fields": {"event_type": event_type}},
            )

    async def log_chat(
        self,
        session_id: str,
        role: str,
        content: str,
        agent: str | None = None,
        data: Any | None = None,
    ) -> None:
        if not self.client:
            await self.connect()

        chat_item = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "role": role,
            "content": content,
            "agent": agent,
            "data": data,
        }

        await self.client.rpush(f"chat:{session_id}", json.dumps(chat_item))
        await self.client.ltrim(f"chat:{session_id}", 0, 499)

        with log_context(session_id=session_id, agent=agent or "-"):
            logger.info("Logged chat", extra={"extra_fields": {"role": role}})

    async def get_events(self, agent_id: str, count: int = 50) -> List[Dict]:
        if not self.client:
            await self.connect()
        events = await self.client.lrange(f"events:{agent_id}", 0, count - 1)
        return [json.loads(event) for event in events]

    async def publish_a2a(self, channel: str, message: Dict):
        if not self.client:
            await self.connect()
        await self.client.publish(channel, json.dumps(message))
        logger.info("A2A published to %s", channel)

    async def subscribe_a2a(self, channel: str):
        if not self.client:
            await self.connect()
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub
