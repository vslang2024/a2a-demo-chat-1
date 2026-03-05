import streamlit as st
import requests
import json
import time

BOOKING_URL = "http://localhost:8000"

st.set_page_config(layout="wide")
st.title("A2A Travel Booking (LangGraph + SSE)")

# -------------------------
# Session State Init
# -------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "events" not in st.session_state:
    st.session_state.events = []
if "listening" not in st.session_state:
    st.session_state.listening = False

# -------------------------
# Booking Form
# -------------------------
payload = {
    "from": st.text_input("From"),
    "to": st.text_input("To"),
    "from_date": str(st.date_input("From Date")),
    "to_date": str(st.date_input("To Date")),
    "budget": st.text_input("Budget")
}

if st.button("Book Trip"):
    response = requests.post(f"{BOOKING_URL}/book", json=payload)
    data = response.json()
    st.session_state.session_id = data["session_id"]
    st.session_state.events = []
    st.success(f"Session started: {st.session_state.session_id}")

# -------------------------
# Live Event Stream
# -------------------------
st.subheader("Live Event Stream")
event_container = st.empty()  # Single container to update dynamically

if st.session_state.session_id:

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start Listening"):
            st.session_state.listening = True
    with col2:
        if st.button("Stop Listening"):
            st.session_state.listening = False

    if st.session_state.listening:
        try:
            # Use stream=True to get incremental events
            with requests.get(
                f"{BOOKING_URL}/events/{st.session_state.session_id}",
                stream=True,
                timeout=None  # keep open as long as needed
            ) as response:

                for line in response.iter_lines():
                    if not st.session_state.listening:
                        break
                    if not line:
                        continue

                    decoded = line.decode("utf-8").strip()

                    # Ignore SSE comments / keep-alive
                    if decoded.startswith(":"):
                        continue

                    # Remove SSE "data:" prefix
                    if decoded.startswith("data:"):
                        decoded = decoded.replace("data:", "").strip()

                    # Parse JSON safely
                    try:
                        event_data = json.loads(decoded)
                    except json.JSONDecodeError:
                        event_data = decoded

                    # Append to session events
                    st.session_state.events.append(event_data)

                    # Stop automatically on final
                    if isinstance(event_data, dict) and event_data.get("type") == "final":
                        st.session_state.listening = False

                    # -------------------------
                    # Re-render UI dynamically
                    # -------------------------
                    with event_container:
                        for event in st.session_state.events:
                            st.json(event)

                    # tiny sleep to allow Streamlit to refresh UI
                    time.sleep(0.05)

        except Exception as e:
            st.error(f"Stream error: {e}")

else:
    st.info("Book a trip first to start streaming.")