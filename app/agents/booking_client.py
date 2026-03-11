from ..models.schemas import BookingRequest
from ..utils.redis_client import RedisClient
from ..utils.a2a_client import A2AClient
from ..utils.logger import logger
import asyncio
import uuid


class BookingClient:
    def __init__(self, session_id: str, redis_client: RedisClient):
        self.session_id = session_id
        self.redis = redis_client
        self.a2a = A2AClient(redis_client)

    async def process_booking(self, request: BookingRequest):
        logger.info(f"Booking client starting session {self.session_id}")

        # Log start event
        await self.redis.log_event("booking_start", "booking_client", {
            "request": request.dict(),
            "session_id": self.session_id
        })

        # Send A2A messages to start agents
        await self.a2a.send_message(
            "booking_client", "flight_agent",
            "START_BOOKING", {"request": request.dict()}
        )
        await self.a2a.send_message(
            "booking_client", "hotel_agent",
            "START_BOOKING", {"request": request.dict()}
        )

        # Wait for agent responses (simplified)
        await asyncio.sleep(2)

        await self.redis.log_event("booking_complete", "booking_client", {
            "status": "success",
            "total_cost": 710,
            "flights": "Booked",
            "hotels": "Booked"
        })
