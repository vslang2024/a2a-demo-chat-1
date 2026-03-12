from typing import Any
import asyncio
import uuid

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

from ..agents.hotel_agent import hotel_agent
from ..models.schemas import BookingRequest
from ..utils.redis_client import RedisClient
from ..utils.logger import get_logger, log_context


logger = get_logger(__name__)


class HotelAgentExecutor(AgentExecutor):
    """Hotel Agent Executor implementing A2A interface with original Redis logging."""

    def __init__(self, redis_client: RedisClient):
        super().__init__()
        self.redis = redis_client
        self.agent = hotel_agent
        self._active_tasks = set()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute hotel agent preserving original langgraph.astream + Redis logging."""
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

        with log_context(session_id=session_id, agent="hotel_agent"):
            logger.info("[Hotel] Session %s: Started processing %s", session_id, request.to_city)

            task = context.current_task
            if not task:
                task = new_task(context.message)
                await event_queue.enqueue_event(task)

            updater = TaskUpdater(event_queue, task.id, task.context_id)

            try:
                # Original streaming logic preserved exactly
                await self.redis.log_event("agent_start", "hotel_agent", {"request": request.dict(), "session_id": session_id})

                async for event in self.agent.astream(
                    {"request": request, "status": "initializing"},
                    stream_mode="values",
                ):
                    # Preserve original event structure
                    agent_event = {
                        "agent": "hotel_agent",
                        "status": event.get("status", "processing"),
                        "data": event.get("hotels", []),
                        "a2a_message": event.get("a2a_message", ""),
                        "session_id": session_id,
                    }

                    # Original Redis logging preserved exactly
                    await self.redis.log_event("stream_event", "hotel_agent", event)

                    # A2A interface updates (using real TaskUpdater)
                    is_task_complete = event.get("status") == "complete"
                    require_user_input = False  # Hotel agent doesn't need input

                    if not is_task_complete and not require_user_input:
                        await updater.update_status(
                            TaskState.working,
                            new_agent_text_message(
                                str(agent_event),
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
                            name="hotel_results",
                        )
                        await updater.complete()
                        break

                logger.info("[Hotel] Session %s: Completed successfully", session_id)

            except Exception as e:
                logger.error("[Hotel] Session %s: Error: %s", session_id, e)
                await self.redis.log_event(
                    "error",
                    "hotel_agent",
                    {"session_id": session_id, "error": str(e)},
                )
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
        except Exception:
            return True  # Invalid

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Cancel ongoing hotel agent execution."""
        session_id = str(uuid.uuid4())

        with log_context(session_id=session_id, agent="hotel_agent"):
            logger.info("[Hotel] Session %s: Cancellation requested", session_id)

            # Log cancellation to Redis (preserving original logging pattern)
            await self.redis.log_event(
                "cancel_requested",
                "hotel_agent",
                {"session_id": session_id, "message": "Hotel agent execution cancelled"},
            )

            # Clear active tasks
            self._active_tasks.clear()

            # Notify via real event queue
            task = context.current_task or new_task(context.message)
            updater = TaskUpdater(event_queue, task.id, task.context_id)
            await updater.update_status(
                TaskState.cancelled,
                new_agent_text_message("Hotel agent execution was cancelled", task.context_id, task.id),
                final=True,
            )

    # Preserve original method for backward compatibility
    async def stream_a2a(self, request: BookingRequest):
        """Original streaming method preserved unchanged."""
        session_id = str(uuid.uuid4())
        with log_context(session_id=session_id, agent="hotel_agent"):
            logger.info("Hotel executor streaming for %s", request.to_city)

            await self.redis.log_event(
                "agent_start",
                "hotel_agent",
                {"request": request.dict(), "session_id": session_id},
            )

            async for event in hotel_agent.astream(
                {"request": request, "status": "initializing"},
                stream_mode="values",
            ):
                yield {
                    "agent": "hotel_agent",
                    "status": event.get("status", "processing"),
                    "data": event.get("hotels", []),
                    "a2a_message": event.get("a2a_message", ""),
                    "session_id": str(uuid.uuid4()),
                }

                # Original Redis logging preserved
                await self.redis.log_event("stream_event", "hotel_agent", event)
