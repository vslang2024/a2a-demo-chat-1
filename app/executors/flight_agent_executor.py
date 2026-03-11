from ..agents.flight_agent import flight_agent
from ..models.schemas import BookingRequest
from ..utils.redis_client import RedisClient
from ..utils.logger import logger
import asyncio
import uuid
from typing import Any
import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    InvalidParamsError,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import (
    new_agent_text_message,
    new_task,
)
from a2a.utils.errors import ServerError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FlightAgentExecutor(AgentExecutor):
    """Flight Agent Executor implementing A2A interface with original Redis logging."""

    def __init__(self, redis_client: RedisClient):
        super().__init__()
        self.redis = redis_client
        self.agent = flight_agent
        self._active_tasks = set()

    async def execute(
            self,
            context: RequestContext,
            event_queue: EventQueue,
    ) -> None:
        """Execute flight agent preserving original langgraph.astream + Redis logging."""
        session_id = str(uuid.uuid4())
        self._active_tasks.add(session_id)

        # Extract BookingRequest from context (no mocking)
        try:
            request_data = context.get_user_input()
            request = BookingRequest(**request_data)
        except Exception as e:
            error = self._validate_request(context)
            if error:
                raise ServerError(error=InvalidParamsError())
            raise ServerError(error=InternalError(f"Invalid request format: {e}"))

        logger.info(f"[Flight] Session {session_id}: Started processing {request.from_city} -> {request.to_city}")

        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        try:
            # Original streaming logic preserved exactly
            await self.redis.log_event("agent_start", "flight_agent", {
                "request": request.dict()
            })

            async for event in self.agent.astream(
                    {"request": request, "status": "initializing"},
                    stream_mode="values"
            ):
                # Preserve original event structure
                agent_event = {
                    "agent": "flight_agent",
                    "status": event.get("status", "processing"),
                    "data": event.get("flights", []),
                    "a2a_message": event.get("a2a_message", ""),
                    "session_id": session_id
                }

                # Original Redis logging preserved exactly
                await self.redis.log_event("stream_event", "flight_agent", event)

                # A2A interface updates (using real TaskUpdater)
                is_task_complete = event.get("status") == "complete"
                require_user_input = False  # Flight agent doesn't need input

                if not is_task_complete and not require_user_input:
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(
                            str(agent_event),  # Convert to string for A2A interface
                            task.context_id,
                            task.id,
                        ),
                    )
                elif require_user_input:
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(
                            str(agent_event),
                            task.context_id,
                            task.id,
                        ),
                        final=True,
                    )
                    break
                else:
                    # Complete with results as artifact
                    await updater.add_artifact(
                        [Part(root=TextPart(text=str(agent_event)))],
                        name='flight_results',
                    )
                    await updater.complete()
                    break

            logger.info(f"[Flight] Session {session_id}: Completed successfully")

        except Exception as e:
            logger.error(f"[Flight] Session {session_id}: Error: {e}")
            await self.redis.log_event("error", "flight_agent", {
                "session_id": session_id,
                "error": str(e)
            })
            await updater.update_status(
                TaskState.error,
                new_agent_text_message(str(e), task.context_id, task.id),
                final=True,
            )
            raise ServerError(error=InternalError()) from e
        finally:
            self._active_tasks.discard(session_id)

    def _validate_request(self, context: RequestContext) -> bool:
        """Validate request contains required BookingRequest fields."""
        try:
            user_input = context.get_user_input()
            BookingRequest(**user_input)
            return False  # Valid
        except:
            return True  # Invalid

    async def cancel(
            self,
            context: RequestContext,
            event_queue: EventQueue
    ) -> None:
        """Cancel ongoing flight agent execution."""
        session_id = str(uuid.uuid4())

        logger.info(f"[Flight] Session {session_id}: Cancellation requested")

        # Log cancellation to Redis (preserving original logging pattern)
        await self.redis.log_event("cancel_requested", "flight_agent", {
            "session_id": session_id,
            "message": "Flight agent execution cancelled"
        })

        # Clear active tasks
        self._active_tasks.clear()

        # Notify via real event queue
        task = context.current_task or new_task(context.message)
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        await updater.update_status(
            TaskState.cancelled,
            new_agent_text_message("Flight agent execution was cancelled", task.context_id, task.id),
            final=True,
        )

    # Preserve original method for backward compatibility
    async def stream_a2a(self, request: BookingRequest):
        """Original streaming method preserved unchanged."""
        logger.info(f"Flight executor streaming for {request.from_city} -> {request.to_city}")

        await self.redis.log_event("agent_start", "flight_agent", {
            "request": request.dict()
        })

        async for event in flight_agent.astream(
                {"request": request, "status": "initializing"},
                stream_mode="values"
        ):
            yield {
                "agent": "flight_agent",
                "status": event.get("status", "processing"),
                "data": event.get("flights", []),
                "a2a_message": event.get("a2a_message", ""),
                "session_id": str(uuid.uuid4())
            }

            # Original Redis logging preserved
            await self.redis.log_event("stream_event", "flight_agent", event)
