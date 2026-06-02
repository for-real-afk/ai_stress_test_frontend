import streamlit as st
import requests
import pandas as pd
import plotly.express as px




# 1. Page config MUST be the first Streamlit command
st.set_page_config(
    page_title="AI Stress Test Lab",
    page_icon="🧠",
    layout="wide"
)

BACKEND_URL = "https://ai-stress-test-backend.onrender.com"

# 2. Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "latencies" not in st.session_state:
    st.session_state.latencies = []
def load_metrics():

    try:

        response = requests.get(
            f"{API_URL}/analytics"
        )

        if response.status_code == 200:

            return pd.DataFrame(
                response.json()
            )

    except Exception:
        pass

    return pd.DataFrame()
metrics = pd.DataFrame()
st.title("🧠 AI Personality Stress Test Lab")

# 3. Global Dashboard (Wrapped in an expander to keep the chat interface clean)
with st.expander("📊 View Global Observability Dashboard", expanded=False):
    try:
        metrics_df = load_metrics()
    except Exception:
        metrics_df = pd.DataFrame() # Fallback if backend analytics fails

    if not metrics_df.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Requests", len(metrics_df))
        c2.metric("Avg Latency", round(metrics_df["latency"].mean(), 2))
        c3.metric("Total Tokens", int(metrics_df["total_tokens"].sum()))
        c4.metric("Total Cost", round(metrics_df["cost"].sum(), 4))

        col_fig1, col_fig2 = st.columns(2)
        
        with col_fig1:
            cost_fig = px.bar(metrics_df, x="model", y="cost", title="Cost by Model")
            st.plotly_chart(cost_fig, use_container_width=True)

            latency_fig = px.box(metrics_df, x="model", y="latency", title="Latency Distribution")
            st.plotly_chart(latency_fig, use_container_width=True)

        with col_fig2:
            token_fig = px.bar(metrics_df, x="model", y="total_tokens", title="Token Usage")
            st.plotly_chart(token_fig, use_container_width=True)

            leaderboard = metrics_df.groupby("model").agg({
                "latency": "mean",
                "cost": "sum",
                "total_tokens": "sum"
            }).reset_index()

            st.subheader("🏆 Model Leaderboard")
            st.dataframe(leaderboard, use_container_width=True)

st.divider()

# 4. Main Chat Interface
left, right = st.columns([3, 1])

with right:
    st.subheader("Settings")
    selected_model = st.selectbox(
        "Choose Model",
        ["gemini", "groq", "qwen"]
    )

    if st.button("Reset Memory"):
        try:
            requests.post(f"{BACKEND_URL}/reset")
            st.session_state.messages = []
            st.session_state.latencies = []
            st.success("Conversation Cleared")
        except requests.exceptions.ConnectionError:
            st.error("Failed to connect to backend to reset memory.")

with left:
    st.subheader("Chat")

    # Render previous messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input Trigger
    prompt = st.chat_input("Ask something...")

    if prompt:
        # Add and render user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Fetch and render assistant response
        try:
            response = requests.post(
                f"{BACKEND_URL}/chat",
                json={
                    "model": selected_model,
                    "message": prompt
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                assistant_reply = result.get("response", "Error: No response field")
                latency = result.get("latency", 0.0)
                
                # Update Session State
                st.session_state.latencies.append({
                    "model": selected_model,
                    "latency": latency
                })
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_reply
                })

                # Render Assistant Message and Per-Message Metrics
                with st.chat_message("assistant"):
                    st.markdown(assistant_reply)

                    # Inline metrics directly under the chat bubble
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Latency", f"{latency}s")
                    col2.metric("Prompt Tokens", result.get("prompt_tokens", 0))
                    col3.metric("Output Tokens", result.get("response_tokens", 0))
                    col4.metric("Cost", f"${result.get('cost', 0.0)}")
            else:
                st.error(f"Backend returned an error: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            st.error("Failed to connect to the backend API. Is it running on port 8000?")

st.divider()

# 5. Session Latency Analytics (Live updates based on current chat)
st.subheader("Current Session Latency Analytics")

if len(st.session_state.latencies) > 0:
    df = pd.DataFrame(st.session_state.latencies)

    fig1, fig2 = st.columns(2)
    
    with fig1:
        box_fig = px.box(df, x="model", y="latency", title="Session Latency Distribution")
        st.plotly_chart(box_fig, use_container_width=True)
        
    with fig2:
        bar_fig = px.bar(df, x="model", y="latency", title="Latency Per Request")
        st.plotly_chart(bar_fig, use_container_width=True)