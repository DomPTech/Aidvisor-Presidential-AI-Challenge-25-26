import streamlit as st
from app.common import load_data, save_data, get_badge

st.set_page_config(page_title="Flooding Coordination - Profile", layout="wide")

with st.sidebar:
    st.session_state.hf_api_key = st.text_input("HuggingFace API Key", value=st.session_state.hf_api_key,
                                                type="password")

data = load_data()
user_info = data["users"].get(st.session_state.username, {})
st.header(f"Profile: {st.session_state.username}")
st.subheader(f"Badge: {get_badge(st.session_state.username)}")
st.write(f"Total Points: {user_info.get('points', 0)}")

st.divider()
st.subheader("Settings")
with st.expander("🔐 Change Password"):
    new_pw = st.text_input("New Password", type="password")
    confirm_pw = st.text_input("Confirm New Password", type="password")
    if st.button("Update Password"):
        if new_pw and new_pw == confirm_pw:
            data["users"][st.session_state.username]["pw"] = new_pw
            save_data(data)
            st.success("Password updated successfully!")
        else:
            st.error("Passwords do not match or field is empty.")

if st.button("🚪 Sign Out"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.switch_page("pages/8_Login.py")