import redis.asyncio as redis
import json
import os
import asyncio
from dotenv import load_dotenv
from logging_config import setup_logger  # your logger

load_dotenv()
logger = setup_logger()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

async def publish_event(session_id: str, data: dict):
    """
    Persist event to Redis Stream and log it.
    """
    if not session_id:
        logger.warning("publish_event called without session_id")
        return

    stream_key = f"session:{session_id}"
    try:
        await redis_client.xadd(
            name=stream_key,
            fields={"data": json.dumps(data)},
            maxlen=1000,
            approximate=True
        )
        await redis_client.expire(stream_key, 3600)  # auto-expire after 1 hour
        logger.debug(f"Published event to {stream_key}: {data}")
    except Exception as e:
        logger.error(f"Redis publish failed for {session_id}: {e}", exc_info=True)


async def stream_session_events(session_id: str):
    """
    Async generator to read events from Redis Stream.
    """
    r = redis.from_url(REDIS_URL, decode_responses=True)
    last_id = "0"
    while True:
        try:
            entries = await r.xread({f"session:{session_id}": last_id}, block=5000, count=10)
            if not entries:
                continue
            for _, messages in entries:
                for message_id, fields in messages:
                    last_id = message_id
                    data = json.loads(fields["data"])
                    logger.debug(f"Read event from session {session_id}: {data}")
                    yield data
        except asyncio.CancelledError:
            logger.info(f"Stream for session {session_id} cancelled")
            break
        except Exception as e:
            logger.error(f"Redis stream error for session {session_id}: {e}", exc_info=True)
            await asyncio.sleep(1)


# Example usage if run directly
if __name__ == "__main__":
    async def main():
        async for event in stream_session_events("12345"):
            logger.info(event)
    asyncio.run(main())