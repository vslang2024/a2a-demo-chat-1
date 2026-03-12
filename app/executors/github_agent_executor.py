# app/executors/github_agent_executor.py
"""MCP GitHub Agent Executor - Redis persistent"""

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message
from langchain_core.messages import HumanMessage, AIMessage
from app.agents.github_agent import github_agent


class GithubAgentExecutor(AgentExecutor):
    """MCP GitHub Agent with tool calling + Redis persistence"""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_input = context.get_user_input()

        if not user_input.strip():
            await event_queue.enqueue_event(
                new_agent_text_message("Please ask about a GitHub user!")
            )
            return

        # Use session_id as Redis thread_id for persistence
        thread_id = context.session_id or "default"
        config = {"configurable": {"thread_id": thread_id}}
        messages = [HumanMessage(content=user_input)]

        result = ""
        try:
            # Stream MCP agent with tool calls + Redis persistence
            for chunk in github_agent.stream({"messages": messages}, config, stream_mode="values"):
                if chunk["messages"]:
                    last_msg = chunk["messages"][-1]
                    if isinstance(last_msg, AIMessage) and last_msg.content:
                        result += last_msg.content
                    elif hasattr(last_msg, 'content') and last_msg.content:
                        result += f"🛠️ {last_msg.content}\n\n"

            await event_queue.enqueue_event(new_agent_text_message(result))

        except Exception as e:
            error_msg = f"🤖 GitHub lookup failed. Try a public username like 'langchain-ai'. (Error: {str(e)[:50]})"
            await event_queue.enqueue_event(new_agent_text_message(error_msg))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Cancellation not supported")
