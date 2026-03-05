# flight_agent_executor.py
import os
from dotenv import load_dotenv
from redis_stream import publish_event
from logging_config import setup_logger
from google import genai  # correct SDK import

load_dotenv()
logger = setup_logger()
API_KEY = os.getenv("GOOGLE_API_KEY")

# Initialize Gemini client
client = genai.Client(api_key=API_KEY)


async def run_flight_agent_stream(payload: dict):
    """
    Streaming flight agent executor.
    Publishes chunks to Redis and logs info/errors.
    """
    session_id = payload.get("session_id")
    prompt = f"Provide flight options based on:\n{payload}"

    try:
        # Start info
        logger.info(f"[Flight] Session {session_id}: Started processing")
        await publish_event(session_id, {
            "type": "info",
            "agent": "flight",
            "message": "Started processing"
        })

        # Streaming chunks from Gemini
        for chunk in client.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=prompt,
        ):
            text = chunk.text
            if text:
                await publish_event(session_id, {
                    "type": "chunk",
                    "agent": "flight",
                    "data": text
                })
                logger.info(f"[Flight] Session {session_id}: Chunk sent: {text[:50]}...")  # first 50 chars
                yield {"text": text}

        # Completion info
        logger.info(f"[Flight] Session {session_id}: Completed processing")
        await publish_event(session_id, {
            "type": "info",
            "agent": "flight",
            "message": "Completed processing"
        })

    except Exception as e:
        logger.error(f"[Flight] Session {session_id}: Error: {e}")
        await publish_event(session_id, {
            "type": "error",
            "agent": "flight",
            "message": str(e)
        })
        yield {"error": str(e)}