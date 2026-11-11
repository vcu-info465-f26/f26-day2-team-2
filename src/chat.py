import os
import streamlit as st
from openai import OpenAI

MODEL = "openai/gpt-oss-120b"

def _client():
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        try:
            key = st.secrets["GROQ_API_KEY"]
        except Exception:
            key = None
    return OpenAI(base_url="https://api.groq.com/openai/v1", api_key=key)

def render_chat(df):
    st.subheader("Ask about this data")

    data_context = df.head(150).to_csv(index=False)

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for m in st.session_state.chat_messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    prompt = st.chat_input("e.g. Which manufacturer had the most recalls?")
    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        system = (
            "You answer ONLY from the data table below, which is what the user "
            "currently sees on the dashboard. If the answer is not in the data, "
            "say you don't have that information. Never invent numbers.\n\n"
            "DATA (CSV):\n" + data_context
        )
        api_messages = [{"role": "system", "content": system}] + st.session_state.chat_messages

        try:
            resp = _client().chat.completions.create(
                model=MODEL,
                messages=api_messages,
                reasoning_effort="low",
            )
            answer = resp.choices[0].message.content
        except Exception:
            answer = "Sorry, the assistant is unavailable right now. Please try again in a moment."

        st.session_state.chat_messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer) 