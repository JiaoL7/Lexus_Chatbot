import streamlit as st
from bot import reply

st.set_page_config(page_title="Rule-Based Chatbot", page_icon="💬")
st.title("Rule-Based Chatbot")

if "history" not in st.session_state:
    st.session_state.history = []

for user, bot in st.session_state.history:
    st.chat_message("user").markdown(user)
    st.chat_message("assistant").markdown(bot)

prompt = st.chat_input("Type your message...")
if prompt:
    bot_answer = reply(prompt)
    st.session_state.history.append((prompt, bot_answer))
    st.chat_message("user").markdown(prompt)
    st.chat_message("assistant").markdown(bot_answer)