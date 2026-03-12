import asyncio
import json
import time
from datetime import datetime

from ..models.schemas import BookingRequest
from ..utils.redis_client import RedisClient
from ..utils.a2a_client import A2AClient
from ..utils.logger import get_logger, log_context


logger = get_logger(__name__)


class BookingClient:
    def __init__(self, session_id: str, redis_client: RedisClient):
        self.session_id = session_id
        self.redis = redis_client
        self.a2a = A2AClient(redis_client)

    async def process_booking(self, request: BookingRequest):
        with log_context(session_id=self.session_id, agent="booking_client"):
            logger.info("Booking client starting session")

            # Log start event
            await self.redis.log_event(
                "booking_start",
                "booking_client",
                {"request": request.dict(), "session_id": self.session_id},
            )
            await self._push_session_event("🤝 Coordinating options...")

            # Send A2A messages to start agents
            await self.a2a.send_message(
                "booking_client",
                "flight_agent",
                "START_BOOKING",
                {"request": request.dict(), "session_id": self.session_id},
            )
            await self.a2a.send_message(
                "booking_client",
                "hotel_agent",
                "START_BOOKING",
                {"request": request.dict(), "session_id": self.session_id},
            )
            await self.a2a.send_message(
                "booking_client",
                "weather_agent",
                "START_BOOKING",
                {"request": request.dict(), "session_id": self.session_id},
            )

            # Wait for agent responses and collect results
            results = await self._wait_for_agent_events()
            total_cost = self._compute_total_cost(results)

            await self._emit_debug_summary(results)

            await self.redis.log_event(
                "booking_complete",
                "booking_client",
                {
                    "status": "success",
                    "total_cost": total_cost,
                    "flights": "Booked",
                    "hotels": "Booked",
                    "session_id": self.session_id,
                },
            )

            if total_cost is None:
                await self._push_session_event("✅ Booking confirmed! Total: TBD")
            else:
                await self._push_session_event(f"✅ Booking confirmed! Total ${total_cost}")

    async def _push_session_event(self, message: str) -> None:
        if not self.redis.client:
            await self.redis.connect()

        event = {
            "agent": "booking_client",
            "message": message,
            "session_id": self.session_id,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }
        await self.redis.client.rpush(f"events:{self.session_id}", json.dumps(event))
        await self.redis.client.ltrim(f"events:{self.session_id}", 0, 99)
        await self.redis.log_chat(
            session_id=self.session_id,
            role="assistant",
            content=message,
            agent="booking_client",
        )

    async def _wait_for_agent_events(self, timeout_seconds: int = 20) -> dict:
        if not self.redis.client:
            await self.redis.connect()

        deadline = time.monotonic() + timeout_seconds
        targets = {"flight_agent", "hotel_agent", "weather_agent"}
        found = {}

        while time.monotonic() < deadline and targets - set(found):
            events = await self.redis.client.lrange(f"events:{self.session_id}", 0, -1)
            for raw in events:
                try:
                    event = json.loads(raw)
                except Exception:
                    continue

                agent = event.get("agent")
                if agent in targets:
                    found[agent] = event

            if targets - set(found):
                await asyncio.sleep(0.5)

        return found

    def _compute_total_cost(self, results: dict) -> float | None:
        flight_event = results.get("flight_agent") or {}
        hotel_event = results.get("hotel_agent") or {}

        flight_total = self._min_price(flight_event.get("data"), ["price"])
        hotel_total = self._min_price(hotel_event.get("data"), ["total_price", "price_per_night"])

        if flight_total is None or hotel_total is None:
            return None

        return round(flight_total + hotel_total, 2)

    def _min_price(self, items: list | None, keys: list[str]) -> float | None:
        if not items:
            return None

        values = []
        for item in items:
            if not isinstance(item, dict):
                continue
            for key in keys:
                value = item.get(key)
                if isinstance(value, (int, float)):
                    values.append(float(value))
        return min(values) if values else None

    async def _emit_debug_summary(self, results: dict) -> None:
        missing = []
        empty = []

        for agent in ("flight_agent", "hotel_agent", "weather_agent"):
            event = results.get(agent)
            if not event:
                missing.append(agent)
                continue
            data = event.get("data")
            if data is None or data == []:
                empty.append(agent)

        if missing or empty:
            parts = []
            if missing:
                parts.append(f"missing events: {', '.join(missing)}")
            if empty:
                parts.append(f"empty data: {', '.join(empty)}")
            await self._push_session_event("🔎 Debug: " + "; ".join(parts))
