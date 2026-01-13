import streamlit as st
import certifi
import os
from st_supabase_connection import SupabaseConnection

os.environ["SSL_CERT_FILE"] = certifi.where()

conn = st.connection("supabase", type=SupabaseConnection)

st.set_page_config(page_title="Flooding Coordination - Login", layout="wide")

with st.sidebar:
    st.session_state.hf_api_key = st.text_input("HuggingFace API Key", value=st.session_state.hf_api_key,
                                                type="password")

st.header("🔑 Login")
t1, t2 = st.tabs(["Sign In", "Create Account"])
with t2:
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_password")
    if st.button("Register"):
        try:
            response = conn.auth.sign_up({"email": email, "password": password})
            if response.user:
                st.success("Account created! You can now sign in.")
            else:
                st.error("Sign up failed.")
        except Exception as e:
            st.error(f"Error: {str(e)}")
with t1:
    email = st.text_input("Email", key="signin_email")
    password = st.text_input("Password", type="password", key="signin_password")
    if st.button("Sign In"):
        try:
            response = conn.auth.sign_in_with_password({"email": email, "password": password})
            if response.user:
                st.session_state.logged_in = True
                st.session_state.username = response.user.email
                st.switch_page("pages/8_Profile.py")
            else:
                st.error("Sign in failed.")
        except Exception as e:
            st.error(f"Error: {str(e)}")