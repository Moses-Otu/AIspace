import os
import uuid
import streamlit as st
from dotenv import load_dotenv
import requests

# === Load environment variables ===
load_dotenv()
N8N_WEBHOOK_URL = "https://gecko-internal-partly.ngrok-free.app/webhook/bone"

# === Streamlit Page Config ===
st.set_page_config(page_title="📸 Chat with Your Documents and Images")
st.title("📸 Chat with Your Documents and Images")

# === Session Initialization ===
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# === Chat Input ===
user_input = st.chat_input("Ask a question about your documents or images...")

if user_input:
    # 1. Add user's message to session state
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    # 2. Build JSON payload for n8n
    payload = [
        {
            "sessionId": st.session_state.session_id,
            "action": "sendMessage",
            "chatInput": user_input,
            "chatHistory": st.session_state.chat_history,
            "chatHistoryJson": [
                {"role": msg["role"], "content": msg["content"]}
                for msg in st.session_state.chat_history
            ]
        }
    ]

    # 3. Send to n8n
    with st.spinner("Thinking..."):
        try:
            response = requests.post(N8N_WEBHOOK_URL, json=payload)

            if response.ok:
                assistant_reply = response.json().get("output", "🤖 No response from AI.")
            else:
                assistant_reply = f"❌ Server error: {response.status_code}"
        except Exception as e:
            assistant_reply = f"❌ Request failed: {e}"

    # 4. Display assistant message
    st.session_state.chat_history.append({"role": "assistant", "content": assistant_reply})

# === Display Full Chat History ===
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
