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
USD_TO_INR = 86.0  # Conversion rate

# --- Helper Functions for Formatting ---
def format_cost_inr(cost_usd):
    if not isinstance(cost_usd, (int, float)) or cost_usd == 0:
        return "₹0.00"
    
    cost_inr = cost_usd * USD_TO_INR
    if cost_inr < 0.01:
        return "< ₹0.01"
    
    return f"₹{cost_inr:.4f}"

def load_metrics():
    try:
        # Fixed: Was previously using undefined API_URL
        response = requests.get(f"{BACKEND_URL}/analytics")
        if response.status_code == 200:
            return pd.DataFrame(response.json())
    except Exception:
        pass
    return pd.DataFrame()

# 2. Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "latencies" not in st.session_state:
    st.session_state.latencies = []

st.title("🧠 AI Personality Stress Test Lab")

# 3. Global Dashboard (Wrapped in an expander to keep the chat interface clean)
with st.expander("📊 View Global Observability Dashboard", expanded=False):
    metrics_df = load_metrics()

    if not metrics_df.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Requests", len(metrics_df))
        c2.metric("Avg Latency", f"{round(metrics_df['latency'].mean(), 2)}s")
        c3.metric("Total Tokens", f"{int(metrics_df['total_tokens'].sum()):,}")
        
        # Format the total cost using our new INR formatter
        total_cost_usd = metrics_df["cost"].sum()
        c4.metric("Estimated Spend", format_cost_inr(total_cost_usd))

        col_fig1, col_fig2 = st.columns(2)
        
        with col_fig1:
            cost_fig = px.bar(metrics_df, x="model", y="cost", title="Cost by Model (USD)")
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
                cost_usd = result.get("cost", 0.0)
                
                # Token Math
                prompt_tokens = result.get("prompt_tokens", 0)
                response_tokens = result.get("response_tokens", 0)
                total_tokens = prompt_tokens + response_tokens
                
                # Update Session State (Tracking tokens and cost now too)
                st.session_state.latencies.append({
                    "model": selected_model,
                    "latency": latency,
                    "cost": cost_usd,
                    "total_tokens": total_tokens
                })
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_reply
                })

                # Render Assistant Message and LLMOps Metrics
                with st.chat_message("assistant"):
                    st.markdown(assistant_reply)

                    # 5-Column Inline metrics matching the production UX requested
                    st.caption("Message Analytics")
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("Latency", f"{latency:.2f}s")
                    col2.metric("Input Tokens", prompt_tokens)
                    col3.metric("Output Tokens", response_tokens)
                    col4.metric("Total Tokens", total_tokens)
                    col5.metric("Est. Cost", format_cost_inr(cost_usd))
            else:
                st.error(f"Backend returned an error: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            st.error("Failed to connect to the backend API.")

st.divider()

# 5. Session Analytics & Usage (Recruiter View)
st.subheader("📈 Today's Session Usage")

if len(st.session_state.latencies) > 0:
    df = pd.DataFrame(st.session_state.latencies)

    # Top-level session metrics
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Total Requests", len(df))
    sc2.metric("Total Tokens", f"{int(df['total_tokens'].sum()):,}")
    sc3.metric("Estimated Spend", format_cost_inr(df["cost"].sum()))
    sc4.metric("Average Latency", f"{df['latency'].mean():.2f}s")
    
    st.write("") # Spacer

    fig1, fig2 = st.columns(2)
    
    with fig1:
        box_fig = px.box(df, x="model", y="latency", title="Session Latency Distribution")
        st.plotly_chart(box_fig, use_container_width=True)
        
    with fig2:
        bar_fig = px.bar(df, x="model", y="latency", title="Latency Per Request")
        st.plotly_chart(bar_fig, use_container_width=True)