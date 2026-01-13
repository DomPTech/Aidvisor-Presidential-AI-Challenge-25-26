import streamlit as st
from app.common import load_data, save_data

st.set_page_config(page_title="Flooding Coordination - Notifications", layout="wide")

with st.sidebar:
    st.session_state.hf_api_key = st.text_input("HuggingFace API Key", value=st.session_state.hf_api_key,
                                                type="password")

st.header("Notifications")
data = load_data()
my_notifs = [n for n in data.get("notifications", []) if n["to"] == st.session_state.username]
for n in reversed(my_notifs): st.warning(f"**{n['from']}**: {n['message']}")
if st.button("Mark Read"):
    for n in data["notifications"]:
        if n["to"] == st.session_state.username: n["read"] = True
    save_data(data);
    st.rerun()