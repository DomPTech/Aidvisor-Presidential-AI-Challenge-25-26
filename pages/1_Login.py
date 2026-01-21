import streamlit as st
import certifi
import os
from st_supabase_connection import SupabaseConnection
import app.initialize as session_init
import app.auth as auth

os.environ["SSL_CERT_FILE"] = certifi.where()

# Initialize Session
session_init.init_session_state()

st.title("Login")
t1, t2 = st.tabs(["Sign In", "Create Account"])
with t2:
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_password")
    if st.button("Register"):
        success, msg = auth.sign_up(email, password)
        if success:
            st.success(msg)
        else:
            st.error(msg)

with t1:
    email = st.text_input("Email", key="signin_email")
    password = st.text_input("Password", type="password", key="signin_password")
    if st.button("Sign In"):
        success, msg = auth.login(email, password)
        if success:
            st.switch_page("pages/6_Profile.py")
        else:
            st.error(msg)