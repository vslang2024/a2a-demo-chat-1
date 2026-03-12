# app/agents/github_agent.py
"""GitHub MCP Tool Agent - Redis persistent, callable as MCP tool"""

import os
import requests
from typing import Annotated, List, TypedDict, Optional
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
try:
    from langgraph.checkpoint.redis import RedisSaver
except Exception:  # pragma: no cover - optional dependency
    RedisSaver = None
from langgraph.prebuilt import ToolNode
import redis
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# Redis client (redis==7.3.0 from your requirements)
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD"),
    db=0,
    decode_responses=True
)

checkpointer = RedisSaver(redis_client) if RedisSaver else None

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

# MCP TOOL - callable by LLM
@tool
def get_github_account_details(username: str) -> str:
    """Fetch GitHub profile details for a given GitHub username.
    Use this tool when users ask about GitHub profiles, repos, or followers."""
    url = f"https://api.github.com/users/{username}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return f"❌ GitHub user '{username}' not found"
        data = response.json()
        contributions = _get_contributions_total(username)
        contributions_line = (
            f"📈 Total Contributions: {contributions}"
            if contributions is not None
            else "📈 Total Contributions: unavailable (set GITHUB_TOKEN)"
        )
        return (
            f"👤 Username: {data.get('login')}\n"
            f"📛 Name: {data.get('name')}\n"
            f"🧑‍💻 Bio: {data.get('bio')}\n"
            f"🏢 Company: {data.get('company')}\n"
            f"📍 Location: {data.get('location')}\n"
            f"🔗 Blog: {data.get('blog')}\n"
            f"🐦 Twitter: {data.get('twitter_username')}\n"
            f"📦 Public Repos: {data.get('public_repos')}\n"
            f"🧩 Public Gists: {data.get('public_gists')}\n"
            f"👥 Followers: {data.get('followers')}\n"
            f"👤 Following: {data.get('following')}\n"
            f"📅 Created: {data.get('created_at')}\n"
            f"🔄 Updated: {data.get('updated_at')}\n"
            f"{contributions_line}\n"
            f"🔗 Profile: {data.get('html_url')}"
        )
    except Exception as e:
        return f"❌ Error fetching GitHub data: {str(e)}"


def _get_contributions_total(username: str) -> Optional[int]:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return None

    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
          }
        }
      }
    }
    """
    headers = {"Authorization": f"bearer {token}"}
    try:
        response = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": {"login": username}},
            headers=headers,
            timeout=10,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        return (
            data.get("data", {})
            .get("user", {})
            .get("contributionsCollection", {})
            .get("contributionCalendar", {})
            .get("totalContributions")
        )
    except Exception:
        return None

# LLM with MCP tool bound (langchain-google-genai==4.2.1)
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)
llm_with_tools = llm.bind_tools([get_github_account_details])

def agent_node(state: AgentState):
    """MCP Agent node - decides when to call GitHub tool"""
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# Redis-persistent MCP graph with tool node
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode([get_github_account_details]))  # MCP tool execution
workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    lambda s: "tools" if s["messages"][-1].tool_calls else END
)
workflow.add_edge("tools", "agent")
workflow.add_edge("tools", END)

github_agent = workflow.compile(checkpointer=checkpointer) if checkpointer else workflow.compile()
