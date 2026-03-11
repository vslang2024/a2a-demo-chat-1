import streamlit as st
import requests
import json
import time
from datetime import date

BOOKING_URL = "http://localhost:8000"

st.set_page_config(layout="wide")
st.title("✈️🏨 **A2A Travel Booking (LangGraph + SSE + Redis)**")

# Session State
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "events" not in st.session_state:
    st.session_state.events = []
if "listening" not in st.session_state:
    st.session_state.listening = False

# Booking Form
col1, col2 = st.columns([3, 1])
with col1:
    payload = {
        "from_city": st.text_input("✈️ From", value="Bangalore"),
        "to_city": st.text_input("🏨 To", value="Mumbai"),
        "from_date": str(st.date_input("📅 From Date", value=date(2026, 3, 15))),
        "to_date": str(st.date_input("📅 To Date", value=date(2026, 3, 18))),
        "budget_min": float(st.number_input("💰 Min Budget ($)", value=200.0)),
        "budget_max": float(st.number_input("💰 Max Budget ($)", value=1000.0))
    }

with col2:
    if st.button("🚀 **Book Trip**", type="primary"):
        try:
            response = requests.post(f"{BOOKING_URL}/booking/start", json=payload)
            data = response.json()
            st.session_state.session_id = data["session_id"]
            st.session_state.events = []
            st.success(f"✅ Session: {st.session_state.session_id}")
            st.rerun()
        except Exception as e:
            st.error(f"❌ {e}")

# Main Layout
if st.session_state.session_id:
    # Control Row
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ **Start Streaming**", disabled=st.session_state.listening):
            st.session_state.listening = True
            st.session_state.events = []
            st.rerun()
    with col2:
        if st.button("⏹️ **Stop Streaming**", disabled=not st.session_state.listening):
            st.session_state.listening = False
            st.rerun()

    # Two-column layout: SSE Stream | Redis Monitor
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("### 📡 **Real-time SSE JSON Events**")
        event_container = st.empty()

        if st.session_state.listening:
            try:
                response = requests.get(
                    f"{BOOKING_URL}/sse/{st.session_state.session_id}",
                    stream=True, timeout=30
                )

                for line in response.iter_lines():
                    if line:
                        decoded = line.decode("utf-8").strip()
                        if decoded.startswith("data: "):
                            event_data = json.loads(decoded[6:])
                            st.session_state.events.append(event_data)

                            # === LIVE JSON DISPLAY ===
                            with event_container.container():
                                st.markdown("**🔴 LIVE STREAM**")
                                st.json(event_data)  # Raw JSON

                                # Formatted event cards
                                agent = event_data.get("agent", "unknown")
                                agent_emoji = "✈️" if "flight" in agent else "🏨" if "hotel" in agent else "🎫"
                                color = "#ef4444" if "flight" in agent else "#0284c7" if "hotel" in agent else "#059669"

                                st.markdown(f"""
                                <div style="padding:1.5rem; margin:1rem 0; background:linear-gradient(135deg,{color}15,{color}05);
                                border-left:5px solid {color}; border-radius:12px;">
                                    <div style="display:flex;justify-content:space-between;">
                                        <strong style="color:{color};">{agent_emoji} {agent.replace('_agent', ' Agent').title()}</strong>
                                        <span style="color:#94a3b8;">● LIVE</span>
                                    </div>
                                    <div style="mt:0.8rem;color:#334155;">{event_data.get('message', 'Event')}</div>
                                </div>
                                """, unsafe_allow_html=True)

                            time.sleep(0.1)

            except Exception as e:
                st.error(f"Stream error: {e}")

    with col_right:
        st.markdown("### 🐘 **Redis Live Monitor**")
        redis_container = st.empty()

        try:
            redis_data = requests.get(f"{BOOKING_URL}/redis/{st.session_state.session_id}").json()

            with redis_container.container():
                st.markdown("**📊 Redis Data**")

                # Session info
                st.subheader("Session Info")
                for key, value in redis_data["session"].items():
                    st.metric(key.replace("_", " ").title(), value)

                # Events count
                st.metric("Events in Redis", len(redis_data["events"]))

                # Raw Redis events
                st.markdown("**📋 Last 5 Events**")
                for event in redis_data["events"][-5:]:
                    with st.expander(f"{event['agent']} - {event['timestamp']}"):
                        st.json(event)

        except Exception as e:
            st.error(f"Redis fetch error: {e}")

else:
    st.info("👆 Fill form and **Book Trip** to start real-time streaming!")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#ef444420,#f8717120);color:#dc2626;padding:2rem;border-radius:15px;text-align:center;">
            <h3>✈️ Flight Agent</h3><div style="font-size:2em;">● READY</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#0284c720,#0ea5e920);color:#0369a1;padding:2rem;border-radius:15px;text-align:center;">
            <h3>🏨 Hotel Agent</h3><div style="font-size:2em;">● READY</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#05966920,#10b98120);color:#065f46;padding:2rem;border-radius:15px;text-align:center;">
            <h3>🎫 Booking Client</h3><div style="font-size:2em;">● READY</div>
        </div>
        """, unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("📈 Stats")
    st.metric("Session", st.session_state.session_id or "None")
    st.metric("Events", len(st.session_state.events))
    st.metric("Status", "🔴 LIVE" if st.session_state.listening else "⏸️ PAUSED")

    if st.button("🗑️ Reset"):
        for key in ["session_id", "events", "listening"]:
            del st.session_state[key]
        st.rerun()
