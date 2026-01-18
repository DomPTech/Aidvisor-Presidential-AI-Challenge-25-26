import streamlit as st
from app.chatbot.chatbot import DisasterAgent
from app.chatbot.tools.ddg_search import get_search, get_news_search
from app.chatbot.tools.nws_alerts import get_nws_alerts
from app.chatbot.tools.openfema import get_fema_disaster_declarations, get_fema_assistance_data
from app.chatbot.tools.nasa_eonet import get_nasa_eonet_events
import app.initialize as session_init
from st_supabase_connection import SupabaseConnection

try:
    import pandas as pd
    import plotly.express as px
    HAS_VISUALS = True
except ImportError:
    HAS_VISUALS = False

st.set_page_config(page_title="Disaster Chatbot", layout="wide")

session_init.init_session_state()

st.title("🤖 Disaster Chatbot")

user_id = st.session_state.get("user_id")
if user_id is None:
    st.error("You must be logged in.")

    if st.button("Go to login"):
        st.switch_page("pages/1_Login.py")
    st.stop()

try:
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception as e:
    st.error(f"Failed to connect to Supabase: {e}")
    conn = None

# Sidebar controls
with st.sidebar:
    if st.button(":material/add: New Chat", use_container_width=True):
        st.session_state.messages = []
        if "agent" in st.session_state:
            del st.session_state["agent"]
        st.rerun()

def get_agent():
    if "agent" not in st.session_state:
        st.session_state.agent = DisasterAgent(
            model_id=st.session_state.hf_model_id,
            api_token=st.session_state.hf_api_key,
            tools={
                "get_search": get_search,
                "get_news_search": get_news_search, 
                "get_nws_alerts": get_nws_alerts,
                "get_fema_disaster_declarations": get_fema_disaster_declarations,
                "get_fema_assistance_data": get_fema_assistance_data,
                "get_nasa_eonet_events": get_nasa_eonet_events
            }
        )
    return st.session_state.agent

def render_message(role, content):
    with st.chat_message(role):
        if isinstance(content, dict):
            text = content.get("text", "")
            st.markdown(text)
            for visual in content.get("visuals", []):
                if not HAS_VISUALS:
                    st.warning("Install `plotly` and `pandas` to see maps and charts: `pip install plotly pandas`")
                    continue
                if visual["type"] == "map":
                    df = pd.DataFrame(visual["data"])
                    st.map(df)
                elif visual["type"] == "chart":
                    df = pd.DataFrame(visual["data"])
                    fig = px.bar(df, x="Location", y="Approved Funding ($)", 
                                 title="FEMA Approved Funding by Location",
                                 hover_data=["Registrations"])
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown(content)

def handle_chat(prompt):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display the user message immediately
    render_message("user", prompt)
    
    agent = get_agent()
    with st.chat_message("assistant"):
        with st.spinner("Consulting disaster databases..."):
            res = agent.get_response(prompt, history=[
                {"role": m["role"], "content": m["content"]["text"] if isinstance(m["content"], dict) else m["content"]}
                for m in st.session_state.messages[:-1]
            ], return_raw=True)
        
        # Helper to render visuals and text from response
        st.markdown(res["text"])
        for visual in res.get("visuals", []):
            if not HAS_VISUALS:
                st.warning("Install `plotly` and `pandas` to see maps and charts: `pip install plotly pandas`")
                break
            if visual["type"] == "map":
                df = pd.DataFrame(visual["data"])
                st.map(df)
            elif visual["type"] == "chart":
                df = pd.DataFrame(visual["data"])
                fig = px.bar(df, x="Location", y="Approved Funding ($)", 
                             title="FEMA Approved Funding by Location",
                             hover_data=["Registrations"])
                st.plotly_chart(fig, use_container_width=True)
                
    st.session_state.messages.append({"role": "assistant", "content": res})

# Display chat history
if st.session_state.messages:
    for msg in st.session_state.messages:
        render_message(msg["role"], msg["content"])

# Suggestion buttons if no messages
if not st.session_state.messages:
    st.space(size="large")
    
    st.markdown(
        "<span style='font-weight:lighter; font-size: 4.5vw; line-height: 1.2;'>What can I help you with today?</span>", 
        text_alignment="center", 
        unsafe_allow_html=True
    )
    
    st.write("") 

    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🌊 How do I prepare for a flood?", use_container_width=True):
            handle_chat("How do I prepare for a flood?")
            st.rerun()

    with col2:
        if st.button("💰 Show me FEMA assistance data for my location", use_container_width=True):
            profile = conn.table("profiles").select("fips_code").eq("id", user_id).execute()
            fips = profile.data[0].get('fips_code')

            handle_chat(f"What is the FEMA assistance data for the area with FIPS code {fips}?")
            st.rerun()

    with col3:
        if st.button("📢 Current disaster alerts", use_container_width=True):
            profile = conn.table("profiles").select("fips_code").eq("id", user_id).execute()
            fips = profile.data[0].get('fips_code')

            handle_chat(f"What are the current disaster alerts in the area with FIPS code {fips}?")
            st.rerun()
            
    st.space("stretch")

# Chat input
if prompt := st.chat_input("Help?"):
    handle_chat(prompt)
    st.rerun()