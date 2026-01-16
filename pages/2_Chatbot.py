import streamlit as st
from app.chatbot.chatbot import DisasterAgent
from app.chatbot.tools.ddg_search import get_search, get_news_search
from app.chatbot.tools.nws_alerts import get_nws_alerts
from app.chatbot.tools.openfema import get_fema_disaster_declarations, get_fema_assistance_data
from app.chatbot.tools.bounty_tools import post_disaster_alert
import app.initialize as session_init

st.set_page_config(page_title="Flooding Coordination - Chatbot", layout="wide")

session_init.init_session_state()

with st.sidebar:
    st.session_state.hf_api_key = st.text_input("HuggingFace API Key", value=st.session_state.hf_api_key,
                                                type="password")

st.title("🤖 Disaster Chatbot")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("Help?"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    agent = DisasterAgent(model_id=st.session_state.hf_model_id,
                          api_token=st.session_state.hf_api_key,
                          tools={
                              "get_search": get_search,
                              "get_news_search": get_news_search, 
                              "get_nws_alerts": get_nws_alerts,
                              "get_fema_disaster_declarations": get_fema_disaster_declarations,
                              "get_fema_assistance_data": get_fema_assistance_data,
                              "post_disaster_alert": post_disaster_alert
                          })
    with st.chat_message("assistant"):
        res = agent.get_response(prompt, history=st.session_state.messages[:-1])
        st.markdown(res)
    st.session_state.messages.append({"role": "assistant", "content": res})