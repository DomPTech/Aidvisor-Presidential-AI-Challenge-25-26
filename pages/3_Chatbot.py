import streamlit as st
from app.chatbot.chatbot import DisasterAgent
from app.chatbot.tools.ddg_search import get_search, get_news_search
from app.chatbot.tools.nws_alerts import get_nws_alerts
from app.chatbot.tools.openfema import get_fema_disaster_declarations, get_fema_assistance_data
from app.chatbot.tools.nasa_eonet import get_nasa_eonet_events
import app.initialize as session_init
from st_supabase_connection import SupabaseConnection
from typing import Generator

try:
    import pandas as pd
    import plotly.express as px
    HAS_VISUALS = True
except ImportError:
    HAS_VISUALS = False

st.set_page_config(page_title="Disaster Chatbot", layout="wide")

session_init.init_session_state()

prompt = None

st.title("Disaster Chatbot")

user_id = st.session_state.get("user_id")
if user_id is None:
    st.error("You must be logged in.")
    st.stop()

# Sidebar controls
with st.sidebar:
    if st.button(":material/add: New Chat", width="stretch"):
        st.session_state.messages = []
        if "agent" in st.session_state:
            del st.session_state["agent"]
        st.rerun()

@st.cache_data
def load_county_data():
    try:
        df = pd.read_csv("data/gis/us_county_latlng_with_state.csv", dtype={"fips_code": str})
        return df
    except Exception as e:
        st.error(f"Error loading county data: {e}")
        return None

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
                    st.plotly_chart(fig, width="stretch")
        else:
            st.markdown(content)

def handle_chat(new_prompt):
    prompt = new_prompt
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display the user message immediately
    render_message("user", prompt)
    
    agent = get_agent()
    
    with st.chat_message("assistant"):
        # 1. Initialize placeholders for streaming
        status_placeholder = st.empty()
        text_placeholder = st.empty()
        
        full_response_text = ""
        collected_visuals = []
        
        # Add a check to ensure history is only built if there are previous messages
        history_data = []
        if len(st.session_state.messages) > 1:
            history_data = [
                {"role": m["role"], "content": m["content"]["text"] if isinstance(m["content"], dict) else m["content"]}
                for m in st.session_state.messages[:-1]
            ]

        # Call the stream with the safer history_data
        res_generator = agent.get_response_stream(
            prompt, 
            history=history_data, 
            return_raw=True
        )
        
        # Iterate through the generator
        for chunk in res_generator:
            if chunk["type"] == "status":
                # Update a small status line (e.g., "Using tool: get_search...")
                status_placeholder.markdown(f"*{chunk['data']}*")
                
            elif chunk["type"] == "text":
                # Clear status when text starts flowing
                status_placeholder.empty()
                full_response_text += chunk["data"]
                text_placeholder.markdown(full_response_text + "▌")
            
            elif chunk["type"] == "visual":
                visual = chunk["data"]
                collected_visuals.append(visual)
                
                # Render visual immediately as it's yielded
                if not HAS_VISUALS:
                    st.warning("Install `plotly` and `pandas` to see maps.")
                else:
                    if visual["type"] == "map":
                        st.map(pd.DataFrame(visual["data"]))
                    elif visual["type"] == "chart":
                        df = pd.DataFrame(visual["data"])
                        fig = px.bar(df, x="Location", y="Approved Funding ($)", title="Funding")
                        st.plotly_chart(fig)

        # Final Polish: remove the cursor from the text
        text_placeholder.markdown(full_response_text)
                
    # Store in history (matching the structure your agent expects)
    st.session_state.messages.append({
        "role": "assistant", 
        "content": {"text": full_response_text, "visuals": collected_visuals}
    })

# Display chat history
if st.session_state.messages:
    for msg in st.session_state.messages:
        render_message(msg["role"], msg["content"])

try:
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception as e:
    st.error(f"Failed to connect to Supabase: {e}")
    conn = None

# Create a placeholder for the welcome screen
welcome_placeholder = st.empty()

# Suggestion buttons if no messages
if not st.session_state.messages and not prompt:    
    # Render the content INSIDE the placeholder container
    with welcome_placeholder.container():
        st.space(size="large")
        
        st.markdown(
            "<span style='font-weight:lighter; font-size: 4.5vw; line-height: 1.2;'>What can I help you with today?</span>", 
            text_alignment="center", 
            unsafe_allow_html=True
        )
        
        st.write("") 

        col1, col2, col3 = st.columns(3)
        
        # Capture the button clicks into variables
        with col1:
            btn_flood = st.button("🌊 How do I prepare for a flood?", width="stretch")
        with col2:
            btn_fema = st.button("💰 Explain FEMA funding process", width="stretch")
        with col3:
            btn_alerts = st.button("📢 Current disaster alerts", width="stretch")
            
        st.space("stretch")

    # Check variables and CLEAR the placeholder immediately if clicked
    if btn_flood:
        welcome_placeholder.empty()
        handle_chat("How do I prepare for a flood?")
        st.rerun()

    if btn_fema:
        welcome_placeholder.empty()
        handle_chat("Explain the FEMA funding process")
        st.rerun()

    if btn_alerts:
        welcome_placeholder.empty()
        profile = conn.table("profiles").select("fips_code").eq("id", user_id).execute()
        fips = profile.data[0].get('fips_code')
        
        # Look up coordinates in CSV
        county_df = load_county_data()
        lat, lon = None, None
        if county_df is not None and fips:
            # Normalize FIPS to 5 digits if needed
            fips_str = str(fips).zfill(5)
            match = county_df[county_df['fips_code'] == fips_str]
            if not match.empty:
                lat = match.iloc[0]['lat']
                lon = match.iloc[0]['lng']

        if lat and lon:
            handle_chat(f"What are the current disaster alerts at latitude {lat} and longitude {lon}?")
        else:
            handle_chat(f"What are the current disaster alerts in the area with FIPS code {fips}?")
        st.rerun()

# Chat input
if prompt := st.chat_input("Help?"):
    welcome_placeholder.empty()
    handle_chat(prompt)
    st.rerun()