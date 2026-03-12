import asyncio
import json
from datetime import datetime
from typing import Any, Dict

from .agents.weather_agent import WeatherAgent
from .agents.flight_agent import flight_agent
from .agents.hotel_agent import hotel_agent
from .models.schemas import BookingRequest
from .utils.logger import get_logger, log_context
from .utils.redis_client import RedisClient


logger = get_logger(__name__)


class A2ADispatcher:
    def __init__(self, redis_client: RedisClient, channel: str = "booking_a2a") -> None:
        self.redis = redis_client
        self.channel = channel
        self.weather_agent = WeatherAgent()

    async def run(self) -> None:
        if not self.redis.client:
            await self.redis.connect()

        pubsub = await self.redis.subscribe_a2a(self.channel)
        logger.info("A2A dispatcher listening on %s", self.channel)

        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue

            try:
                data = json.loads(message.get("data", "{}"))
            except Exception:
                logger.exception("A2A dispatcher received invalid JSON")
                continue

            asyncio.create_task(self._handle_message(data))

    async def _handle_message(self, data: Dict[str, Any]) -> None:
        to_agent = data.get("to_agent")
        payload = data.get("payload") or {}
        request_data = payload.get("request") or {}
        session_id = payload.get("session_id")

        if not request_data or not to_agent:
            return

        try:
            request = BookingRequest(**request_data)
        except Exception as e:
            await self.redis.log_event(
                "error",
                "a2a_dispatcher",
                {"error": f"Invalid request: {e}", "session_id": session_id},
            )
            return

        if to_agent == "weather_agent":
            await self._run_weather(request, session_id)
        elif to_agent == "flight_agent":
            await self._run_flight(request, session_id)
        elif to_agent == "hotel_agent":
            await self._run_hotel(request, session_id)

    async def _run_weather(self, request: BookingRequest, session_id: str | None) -> None:
        await self._push_session_event(
            session_id,
            {"agent": "weather_agent", "message": "🌤️ Checking weather..."},
        )
        try:
            summary = await self.weather_agent.get_weather_summary(
                request.to_city,
                request.from_date,
                request.to_date,
            )
            await self._push_session_event(
                session_id,
                {"agent": "weather_agent", "message": f"🌤️ {summary}", "data": summary},
            )
        except Exception as e:
            await self._push_session_event(
                session_id,
                {"agent": "weather_agent", "message": f"⚠️ Weather lookup failed: {e}"},
            )
            await self.redis.log_event(
                "error",
                "weather_agent",
                {"error": str(e), "session_id": session_id},
            )

    async def _run_flight(self, request: BookingRequest, session_id: str | None) -> None:
        await self._push_session_event(
            session_id,
            {"agent": "flight_agent", "message": "🔍 Searching flights..."},
        )
        try:
            result = flight_agent.invoke({"request": request, "status": "initializing"})
            message = result.get("a2a_message") or f"✈️ Found {len(result.get('flights', []))} flights"
            await self._push_session_event(
                session_id,
                {"agent": "flight_agent", "message": message, "data": result.get("flights", [])},
            )
        except Exception as e:
            await self._push_session_event(
                session_id,
                {"agent": "flight_agent", "message": f"⚠️ Flight lookup failed: {e}"},
            )
            await self.redis.log_event(
                "error",
                "flight_agent",
                {"error": str(e), "session_id": session_id},
            )

    async def _run_hotel(self, request: BookingRequest, session_id: str | None) -> None:
        await self._push_session_event(
            session_id,
            {"agent": "hotel_agent", "message": "🔍 Searching hotels..."},
        )
        try:
            result = hotel_agent.invoke({"request": request, "status": "initializing"})
            message = result.get("a2a_message") or f"🏨 Found {len(result.get('hotels', []))} hotels"
            await self._push_session_event(
                session_id,
                {"agent": "hotel_agent", "message": message, "data": result.get("hotels", [])},
            )
        except Exception as e:
            await self._push_session_event(
                session_id,
                {"agent": "hotel_agent", "message": f"⚠️ Hotel lookup failed: {e}"},
            )
            await self.redis.log_event(
                "error",
                "hotel_agent",
                {"error": str(e), "session_id": session_id},
            )

    async def _push_session_event(self, session_id: str | None, event: Dict[str, Any]) -> None:
        if not session_id:
            return

        if not self.redis.client:
            await self.redis.connect()

        event = {
            **event,
            "session_id": session_id,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }
        await self.redis.client.rpush(f"events:{session_id}", json.dumps(event))
        await self.redis.client.ltrim(f"events:{session_id}", 0, 99)
        await self.redis.log_chat(
            session_id=session_id,
            role="assistant",
            content=event.get("message", ""),
            agent=event.get("agent"),
            data=event.get("data"),
        )
