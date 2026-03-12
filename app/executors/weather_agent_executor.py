import uuid

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import InternalError, InvalidParamsError, Part, TaskState, TextPart
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

from ..agents.weather_agent import WeatherAgent
from ..models.schemas import BookingRequest
from ..utils.redis_client import RedisClient
from ..utils.logger import get_logger, log_context


logger = get_logger(__name__)


class WeatherAgentExecutor(AgentExecutor):
    """Weather Agent Executor that calls MCP weather server."""

    def __init__(self, redis_client: RedisClient):
        super().__init__()
        self.redis = redis_client
        self.agent = WeatherAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        session_id = str(uuid.uuid4())

        # Extract BookingRequest from context
        try:
            request_data = context.get_user_input()
            request = BookingRequest(**request_data)
        except Exception as e:
            error = self._validate_request(context)
            if error:
                raise ServerError(error=InvalidParamsError())
            raise ServerError(error=InternalError(f"Invalid request format: {e}"))

        with log_context(session_id=session_id, agent="weather_agent"):
            logger.info("[Weather] Session %s: Started processing %s", session_id, request.to_city)

            task = context.current_task
            if not task:
                task = new_task(context.message)
                await event_queue.enqueue_event(task)

            updater = TaskUpdater(event_queue, task.id, task.context_id)

            try:
                await self.redis.log_event(
                    "agent_start",
                    "weather_agent",
                    {"request": request.dict(), "session_id": session_id},
                )

                summary = await self.agent.get_weather_summary(
                    request.to_city,
                    request.from_date,
                    request.to_date,
                )

                agent_event = {
                    "agent": "weather_agent",
                    "status": "complete",
                    "data": summary,
                    "session_id": session_id,
                }

                await self.redis.log_event("stream_event", "weather_agent", agent_event)

                await updater.add_artifact(
                    [Part(root=TextPart(text=str(agent_event)))],
                    name="weather_results",
                )
                await updater.complete()

                logger.info("[Weather] Session %s: Completed successfully", session_id)

            except Exception as e:
                logger.error("[Weather] Session %s: Error: %s", session_id, e)
                await self.redis.log_event(
                    "error",
                    "weather_agent",
                    {"session_id": session_id, "error": str(e)},
                )
                await updater.update_status(
                    TaskState.error,
                    new_agent_text_message(str(e), task.context_id, task.id),
                    final=True,
                )
                raise ServerError(error=InternalError()) from e

    def _validate_request(self, context: RequestContext) -> bool:
        try:
            user_input = context.get_user_input()
            BookingRequest(**user_input)
            return False
        except Exception:
            return True
