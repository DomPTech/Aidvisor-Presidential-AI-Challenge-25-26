import streamlit as st
from app.common import load_data, save_data
from streamlit_gsheets import GSheetsConnection
import certifi
import os

os.environ["SSL_CERT_FILE"] = certifi.where()

st.set_page_config(page_title="Flooding Coordination - Login", layout="wide")

if "GOOGLE_SHEET_URL" not in st.secrets:
    st.error("Please add your Google Sheet URL to the secrets.toml file.")
    st.stop()
url = st.secrets["GOOGLE_SHEET_URL"]

conn = st.connection("gsheets", type=GSheetsConnection)

data = conn.read(spreadsheet=url, usecols=list(range(0, 7)))
st.dataframe(data)

with st.sidebar:
    st.session_state.hf_api_key = st.text_input("HuggingFace API Key", value=st.session_state.hf_api_key,
                                                type="password")

st.header("🔑 Login")
data = load_data()
t1, t2 = st.tabs(["Sign In", "Create Account"])
with t2:
    nu, npw = st.text_input("New User"), st.text_input("New Password", type="password")
    if st.button("Register") and nu not in data["users"]:
        data["users"][nu] = {"pw": npw, "points": 0, "history": []}
        save_data(data);
        st.success("Created!")
with t1:
    u, p = st.text_input("User"), st.text_input("Password", type="password")
    if st.button("Sign In") and u in data["users"] and data["users"][u]["pw"] == p:
        st.session_state.logged_in, st.session_state.username = True, u
        st.switch_page("main.py")