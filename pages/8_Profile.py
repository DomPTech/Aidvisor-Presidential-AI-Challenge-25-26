import streamlit as st
from app.common import get_badge
from st_supabase_connection import SupabaseConnection

conn = st.connection("supabase", type=SupabaseConnection)

st.set_page_config(page_title="Flooding Coordination - Profile", layout="wide")

with st.sidebar:
    st.session_state.hf_api_key = st.text_input("HuggingFace API Key", value=st.session_state.hf_api_key,
                                                type="password")

# Load user data from Supabase auth
try:
    user_response = conn.auth.get_user()
    if user_response:
        user = user_response.user
        user_email = user.email
        user_info = {"points": 0, "history": []}  # Custom data not stored in auth; set defaults
    else:
        st.error("User not authenticated, please log in.")
        st.stop()
except Exception as e:
    st.error(f"Error retrieving user: {str(e)}")
    st.stop()

st.header(f"Profile: {user_email}")
st.subheader(f"Badge: {get_badge(user_email)}")
st.write(f"Total Points: {user_info.get('points', 0)}")

st.divider()
st.subheader("Settings")
with st.expander("🔐 Change Password"):
    new_pw = st.text_input("New Password", type="password", key="new_pw")
    confirm_pw = st.text_input("Confirm New Password", type="password", key="confirm_pw")
    if st.button("Update Password"):
        if new_pw and new_pw == confirm_pw:
            try:
                response = conn.auth.update_user({"password": new_pw})
                st.success("Password updated successfully!")
            except Exception as e:
                st.error(f"Error updating password: {str(e)}")
        else:
            st.error("Passwords do not match or field is empty.")

if st.button("🚪 Sign Out"):
    try:
        conn.auth.sign_out()
    except:
        pass
    st.session_state.logged_in = False
    st.session_state.username = None
    st.switch_page("pages/1_Login.py")