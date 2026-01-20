import streamlit as st
import certifi
import os
from st_supabase_connection import SupabaseConnection
import app.initialize as session_init

os.environ["SSL_CERT_FILE"] = certifi.where()

conn = st.connection("supabase", type=SupabaseConnection)

st.set_page_config(page_title="Flooding Coordination - Login", layout="wide")

session_init.init_session_state()

st.title("Login")
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
                st.session_state.user_id = response.user.id
                st.switch_page("pages/6_Profile.py")
            else:
                st.error("Sign in failed.")
        except Exception as e:
            st.error(f"Error: {str(e)}")