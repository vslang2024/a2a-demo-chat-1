import json
import re
import time
from datetime import date, datetime, timedelta

import requests
import streamlit as st

BOOKING_URL = "http://localhost:8000"

st.set_page_config(layout="wide")
st.title("A2A Booking Chat")
st.markdown("")

if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "listening" not in st.session_state:
    st.session_state.listening = False
if "seen_events" not in st.session_state:
    st.session_state.seen_events = set()
if "seen_agents" not in st.session_state:
    st.session_state.seen_agents = set()
if "expected_agents" not in st.session_state:
    st.session_state.expected_agents = None
if "pending_booking" not in st.session_state:
    st.session_state.pending_booking = None
if "pending_github" not in st.session_state:
    st.session_state.pending_github = False
if "latest_results" not in st.session_state:
    st.session_state.latest_results = {}
if "last_message_by_agent" not in st.session_state:
    st.session_state.last_message_by_agent = {}


CITY_PATTERN = re.compile(r"\bfrom\s+([A-Za-z ]+)\s+to\s+([A-Za-z ]+)", re.IGNORECASE)
CITY_REVERSED_PATTERN = re.compile(r"\bto\s+([A-Za-z ]+)\s+from\s+([A-Za-z ]+)", re.IGNORECASE)
DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
NIGHTS_PATTERN = re.compile(r"\bfor\s+(\d{1,2})\s+nights?\b", re.IGNORECASE)
BUDGET_RANGE_PATTERN = re.compile(
    r"\b(?:budget|\$)\s*([0-9]+(?:\.[0-9]+)?)\s*(?:-|to|–)\s*([0-9]+(?:\.[0-9]+)?)\b",
    re.IGNORECASE,
)
BUDGET_MAX_PATTERN = re.compile(r"\b(?:under|below|max)\s*\$?\s*([0-9]+(?:\.[0-9]+)?)\b", re.IGNORECASE)
BUDGET_MIN_PATTERN = re.compile(r"\b(?:min|at least|from)\s*\$?\s*([0-9]+(?:\.[0-9]+)?)\b", re.IGNORECASE)
NEXT_WEEKDAY_PATTERN = re.compile(
    r"\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)
GITHUB_PATTERN = re.compile(r"\bgithub\b|\bgit hub\b|\bgh:\b", re.IGNORECASE)
GITHUB_USER_PATTERN = re.compile(r"\bgithub\s+@?([A-Za-z0-9-]{1,39})\b", re.IGNORECASE)
GITHUB_USER_COLON_PATTERN = re.compile(r"\buser\s*:\s*([A-Za-z0-9-]{1,39})\b", re.IGNORECASE)
GITHUB_USER_PHRASE_PATTERN = re.compile(r"\bgithub\s+user\s*:\s*([A-Za-z0-9-]{1,39})\b", re.IGNORECASE)
WEATHER_PATTERN = re.compile(r"\bweather\b|\bforecast\b", re.IGNORECASE)
WEATHER_CITY_PATTERN = re.compile(r"\bweather\s+in\s+([A-Za-z ]+)", re.IGNORECASE)

WEEKDAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _parse_next_weekday(text: str) -> str | None:
    match = NEXT_WEEKDAY_PATTERN.search(text)
    if not match:
        return None

    weekday = WEEKDAY_INDEX[match.group(1).lower()]
    today = date.today()
    days_ahead = (weekday - today.weekday() + 7) % 7
    if days_ahead == 0:
        days_ahead = 7
    return (today + timedelta(days=days_ahead)).isoformat()


def parse_trip(text: str) -> dict:
    parsed: dict = {}

    city_match = CITY_PATTERN.search(text)
    if city_match:
        parsed["from_city"] = city_match.group(1).strip()
        parsed["to_city"] = city_match.group(2).strip()
    else:
        reversed_match = CITY_REVERSED_PATTERN.search(text)
        if reversed_match:
            parsed["to_city"] = reversed_match.group(1).strip()
            parsed["from_city"] = reversed_match.group(2).strip()

    dates = DATE_PATTERN.findall(text)
    if len(dates) >= 2:
        parsed["from_date"] = dates[0]
        parsed["to_date"] = dates[1]
    elif len(dates) == 1:
        parsed["from_date"] = dates[0]

    next_weekday = _parse_next_weekday(text)
    if next_weekday and "from_date" not in parsed:
        parsed["from_date"] = next_weekday

    nights_match = NIGHTS_PATTERN.search(text)
    if nights_match and "from_date" in parsed and "to_date" not in parsed:
        nights = int(nights_match.group(1))
        try:
            start = datetime.strptime(parsed["from_date"], "%Y-%m-%d").date()
            parsed["to_date"] = (start + timedelta(days=nights)).isoformat()
        except ValueError:
            pass

    budget_range_match = BUDGET_RANGE_PATTERN.search(text)
    if budget_range_match:
        parsed["budget_min"] = float(budget_range_match.group(1))
        parsed["budget_max"] = float(budget_range_match.group(2))
    else:
        max_match = BUDGET_MAX_PATTERN.search(text)
        if max_match:
            parsed["budget_max"] = float(max_match.group(1))
        min_match = BUDGET_MIN_PATTERN.search(text)
        if min_match:
            parsed["budget_min"] = float(min_match.group(1))

    return parsed


def missing_fields(payload: dict) -> list[str]:
    required = ["from_city", "to_city", "from_date", "to_date", "budget_min", "budget_max"]
    return [field for field in required if field not in payload]


def should_hide_event(agent: str, message: str) -> bool:
    if agent != "booking_client":
        lowered = message.lower()
        return (
            "cannot fulfill your request" in lowered
            or "searching flights" in lowered
            or "searching hotels" in lowered
            or "checking weather" in lowered
            or "looking up github details" in lowered
        )
    return (
        "Coordinating options" in message
        or "Debug:" in message
        or "missing events" in message
        or "empty data" in message
    )


def event_key(event: dict) -> str:
    return json.dumps(event, sort_keys=True)



def _format_table_rows(data: list[dict], keys: list[str]) -> list[dict]:
    rows: list[dict] = []
    for item in data:
        row = {}
        for key in keys:
            row[key] = item.get(key)
        rows.append(row)
    return rows


def _render_data(agent: str | None, data: object) -> None:
    if isinstance(data, list) and data:
        if agent == "flight_agent":
            st.table(
                _format_table_rows(
                    data,
                    [
                        "airline",
                        "flight_number",
                        "departure_time",
                        "arrival_time",
                        "duration",
                        "price",
                        "currency",
                        "seats_available",
                        "class",
                    ],
                )
            )
        elif agent == "hotel_agent":
            st.table(
                _format_table_rows(
                    data,
                    [
                        "name",
                        "address",
                        "rating",
                        "price_per_night",
                        "total_price",
                        "currency",
                        "rooms_available",
                        "amenities",
                    ],
                )
            )
        else:
            st.table(data)
    elif isinstance(data, dict) and data:
        st.json(data)
    elif isinstance(data, str) and data.strip():
        if agent == "weather_agent":
            st.markdown("**Weather Details**")
            lines = [line.strip() for line in data.split("\n") if line.strip()]
            for line in lines:
                st.markdown(f"- {line}")
        else:
            st.markdown(data)


def render_event(agent: str, message: str, data: object) -> None:
    with st.chat_message("assistant"):
        st.markdown(f"**{agent}**: {message}")
        if agent == "weather_agent" and isinstance(data, str) and data and data in message:
            return
        _render_data(agent, data)


def log_chat(session_id: str, role: str, content: str, agent: str | None = None, data: object | None = None) -> None:
    try:
        requests.post(
            f"{BOOKING_URL}/chat/log",
            json={
                "session_id": session_id,
                "role": role,
                "content": content,
                "agent": agent,
                "data": data,
            },
            timeout=3,
        )
    except Exception:
        pass


def is_github_query(text: str) -> bool:
    if text.strip().lower().startswith("gh "):
        return True
    return bool(GITHUB_PATTERN.search(text))


def normalize_github_query(text: str) -> str:
    lowered = text.strip().lower()
    if lowered.startswith("github "):
        return text.strip()[7:].strip()
    if lowered.startswith("gh "):
        return text.strip()[3:].strip()
    phrase_match = GITHUB_USER_PHRASE_PATTERN.search(text)
    if phrase_match:
        return f"Tell me about the GitHub user {phrase_match.group(1)}"
    colon_match = GITHUB_USER_COLON_PATTERN.search(text)
    if colon_match:
        return f"Tell me about the GitHub user {colon_match.group(1)}"
    match = GITHUB_USER_PATTERN.search(text)
    if match:
        return f"Tell me about the GitHub user {match.group(1)}"
    return text.strip()


def is_weather_query(text: str) -> bool:
    return bool(WEATHER_PATTERN.search(text))


def normalize_weather_query(text: str) -> str | None:
    match = WEATHER_CITY_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    return None


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "data" in message and message["data"] is not None:
            _render_data(message.get("agent"), message["data"])

# Follow-up prompts for missing details (interactive)
if st.session_state.pending_booking:
    missing = st.session_state.pending_booking.get("missing", [])
    with st.form("booking_followup"):
        st.markdown("I need a few more details to continue your booking:")
        inputs = {}
        for field in missing:
            label = field.replace("_", " ").title()
            inputs[field] = st.text_input(label, key=f"followup_{field}")
        submitted = st.form_submit_button("Continue booking")
    if submitted:
        payload = st.session_state.pending_booking.get("payload", {}).copy()
        payload.update({k: v for k, v in inputs.items() if v})
        still_missing = missing_fields(payload)
        if still_missing:
            st.session_state.pending_booking = {"payload": payload, "missing": still_missing}
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": f"I still need: {', '.join(still_missing)}.",
                }
            )
        else:
            st.session_state.pending_booking = None
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": (
                        "Great, booking now: "
                        f"{payload['from_city']} → {payload['to_city']} on "
                        f"{payload['from_date']} to {payload['to_date']}, "
                        f"budget ${payload['budget_min']}–${payload['budget_max']}."
                    ),
                }
            )
            try:
                response = requests.post(f"{BOOKING_URL}/booking/start", json=payload)
                response.raise_for_status()
                data = response.json()
                st.session_state.session_id = data["session_id"]
                st.session_state.listening = True
                st.session_state.seen_events = set()
                log_chat(st.session_state.session_id, "user", user_prompt)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"Session started: `{st.session_state.session_id}`. Fetching options now.",
                    }
                )
                log_chat(
                    st.session_state.session_id,
                    "assistant",
                    f"Session started: {st.session_state.session_id}. Fetching options now.",
                    agent="booking_client",
                )
            except Exception as e:
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"Failed to start booking: {e}"}
                )

if st.session_state.pending_github:
    with st.form("github_followup"):
        st.markdown("Who should I look up on GitHub?")
        username = st.text_input("GitHub username", key="followup_github_user")
        submitted = st.form_submit_button("Lookup")
    if submitted:
        if username.strip():
            st.session_state.pending_github = False
            try:
                response = requests.post(
                    f"{BOOKING_URL}/github/start",
                    json={"message": f"Tell me about the GitHub user {username.strip()}"},
                )
                response.raise_for_status()
                data = response.json()
                st.session_state.session_id = data["session_id"]
                st.session_state.listening = True
                st.session_state.seen_events = set()
                st.session_state.seen_agents = set()
                st.session_state.expected_agents = {"github_agent"}
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"Session started: `{st.session_state.session_id}`. Fetching GitHub details now.",
                    }
                )
            except Exception as e:
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"GitHub query failed: {e}"}
                )
        else:
            st.session_state.messages.append(
                {"role": "assistant", "content": "Please enter a GitHub username."}
            )

user_prompt = st.chat_input("Describe your trip and I will book it")

if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    # Auto-detect GitHub queries and route to GitHub agent (SSE flow).
    if is_github_query(user_prompt):
        query = normalize_github_query(user_prompt)
        if not query or query.strip().lower() in {"github", "git hub", "gh"}:
            st.session_state.pending_github = True
            st.session_state.messages.append(
                {"role": "assistant", "content": "Sure — which GitHub user should I look up?"}
            )
            query = ""
        try:
            if query:
                response = requests.post(
                    f"{BOOKING_URL}/github/start",
                    json={"message": query},
                )
                response.raise_for_status()
                data = response.json()
                st.session_state.session_id = data["session_id"]
                st.session_state.listening = True
                st.session_state.seen_events = set()
                log_chat(st.session_state.session_id, "user", user_prompt)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"Session started: `{st.session_state.session_id}`. Fetching GitHub details now.",
                    }
                )
                log_chat(
                    st.session_state.session_id,
                    "assistant",
                    f"Session started: {st.session_state.session_id}. Fetching GitHub details now.",
                    agent="github_agent",
                )
        except Exception as e:
            st.session_state.messages.append(
                {"role": "assistant", "content": f"GitHub query failed: {e}"}
            )
    elif is_weather_query(user_prompt):
        city = normalize_weather_query(user_prompt)
        if not city:
            st.session_state.messages.append(
                {"role": "assistant", "content": "Which city should I check the weather for?"}
            )
        else:
            try:
                response = requests.post(
                    f"{BOOKING_URL}/weather/start",
                    json={"city": city},
                )
                response.raise_for_status()
                data = response.json()
                st.session_state.session_id = data["session_id"]
                st.session_state.listening = True
                st.session_state.seen_events = set()
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"Session started: `{st.session_state.session_id}`. Fetching weather now.",
                    }
                )
            except Exception as e:
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"Weather query failed: {e}"}
                )
    else:
        extracted = parse_trip(user_prompt)
        missing = missing_fields(extracted)

        if missing:
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": (
                        "I need these details to proceed: "
                        f"{', '.join(missing)}. Please provide them in this format: "
                        "from <city> to <city> YYYY-MM-DD YYYY-MM-DD budget 200-1000. "
                        "You can also say: next Friday for 3 nights under 800."
                    ),
                }
            )
            st.session_state.pending_booking = {"payload": extracted, "missing": missing}
        else:
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": (
                        "Got it. I will book using: "
                        f"{extracted['from_city']} → {extracted['to_city']} on "
                        f"{extracted['from_date']} to {extracted['to_date']}, "
                        f"budget ${extracted['budget_min']}–${extracted['budget_max']}."
                    ),
                }
            )

            try:
                response = requests.post(f"{BOOKING_URL}/booking/start", json=extracted)
                response.raise_for_status()
                data = response.json()
                st.session_state.session_id = data["session_id"]
                st.session_state.listening = True
                st.session_state.seen_events = set()
                st.session_state.seen_agents = set()
                st.session_state.expected_agents = {
                    "flight_agent",
                    "hotel_agent",
                    "weather_agent",
                    "booking_client",
                }
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"Session started: `{st.session_state.session_id}`. Fetching options now.",
                    }
                )
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": "**booking_client**: ✅ Booking request received",
                        "data": extracted,
                        "agent": "booking_client",
                    }
                )
            except Exception as e:
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"Failed to start booking: {e}"}
                )

if st.session_state.session_id and st.session_state.listening:
    try:
        response = requests.get(
            f"{BOOKING_URL}/sse/{st.session_state.session_id}",
            stream=True,
            timeout=(5, None),
        )

        for line in response.iter_lines():
            if not st.session_state.listening:
                break

            if not line:
                continue

            decoded = line.decode("utf-8").strip()
            if not decoded.startswith("data: "):
                continue

            event = json.loads(decoded[6:])
            key = event_key(event)
            if key in st.session_state.seen_events:
                continue
            st.session_state.seen_events.add(key)

            agent = event.get("agent", "agent")
            message = event.get("message", "")
            data = event.get("data")
            if agent:
                st.session_state.seen_agents.add(agent)

            if message and not should_hide_event(agent, message):
                last_message = st.session_state.last_message_by_agent.get(agent)
                if last_message == message:
                    continue
                st.session_state.last_message_by_agent[agent] = message
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"**{agent}**: {message}"}
                )
                st.session_state.messages[-1]["agent"] = agent
                st.session_state.messages[-1]["data"] = data
                render_event(agent, message, data)
                if data is not None and agent in {"flight_agent", "hotel_agent", "weather_agent"}:
                    st.session_state.latest_results[agent] = data

            if st.session_state.expected_agents:
                if agent == "booking_client" and "Booking confirmed" in message:
                    if st.session_state.expected_agents.issubset(st.session_state.seen_agents):
                        st.session_state.listening = False
                        break
                if agent == "github_agent" and "Looking up" not in message:
                    st.session_state.listening = False
                    break

            time.sleep(0.05)

    except Exception as e:
        st.session_state.messages.append(
            {"role": "assistant", "content": f"Stream error: {e}"}
        )
        st.session_state.listening = False

if st.session_state.session_id and not st.session_state.listening:
    if st.button("Start Listening"):
        st.session_state.listening = True

st.session_state.latest_results = st.session_state.latest_results
