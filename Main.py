import streamlit as st
from streamlit.components.v1 import html as scv1html
from streamlit_float import *
import datetime
import h3
from app.chatbot.chatbot import DisasterAgent
from app.chatbot.tools.ddg_search import get_search, get_news_search
from app.chatbot.tools.nws_alerts import get_nws_alerts
from app.chatbot.tools.openfema import get_fema_disaster_declarations, get_fema_assistance_data
from app.chatbot.tools.nasa_eonet import get_nasa_eonet_events
from app.prediction.scanner import DisasterScanner
from app.prediction.geospatial import get_h3_location_bundles
from app.common import load_scan_cache, save_scan_cache, create_pydeck_map, sign_out
import app.initialize as session_init
from st_supabase_connection import SupabaseConnection
import json

float_init()

def heatmap():
    st.set_page_config(page_title="Flooding Coordination", layout="wide")

    session_init.init_session_state()
    
    with st.sidebar:
        pass

    # Load cached scan data from disk on first run
    if not st.session_state.scan_results and not st.session_state.last_scan_time:
        cached_data = load_scan_cache()
        st.session_state.scan_results = cached_data["scan_results"]
        st.session_state.last_scan_time = cached_data["last_scan_time"]
        
        # If we loaded cached data, mark scan as complete
        if st.session_state.scan_results:
            st.session_state.scan_index = len(st.session_state.get("scan_queries", []))
    
    # Initialize scan_queries with cell-based queries if empty
    if not st.session_state.scan_queries:
        # Define US Bounding Box (Roughly)
        min_lat, max_lat = 24, 50
        min_lon, max_lon = -125, -66
        us_outline = [(min_lat, min_lon), (max_lat, min_lon), (max_lat, max_lon), (min_lat, max_lon)]
        polygon = h3.LatLngPoly(us_outline)
        cells = h3.polygon_to_cells(polygon, 2)
        
        queries = []
        # Add initial global query
        queries.append({"type": "general", "query": "active natural disasters US major emergency"})
        
        # Resolve location bundles for all cells to enable targeted news searches
        with st.spinner("Resolving initial location metadata..."):
            bundles = get_h3_location_bundles(cells)
            for bundle in bundles:
                queries.append({"type": "cell", "bundle": bundle})
            
        st.session_state.scan_queries = queries

    st.title("Disaster Heatmap")

    # Initial fetch for NASA events (if not already in session state)
    if "nasa_events" not in st.session_state:
        from app.common import fetch_nasa_eonet_events_for_map
        st.session_state.nasa_events = fetch_nasa_eonet_events_for_map()

    # Containers for persistent UI
    scan_status_container = st.empty()
    map_container = st.empty()

    # Render initial map immediately
    map_container.pydeck_chart(create_pydeck_map())

    # Check if cache is valid (less than 30 minutes old)
    cache_valid = False
    if st.session_state.last_scan_time:
        time_since_scan = datetime.datetime.now() - st.session_state.last_scan_time
        cache_valid = time_since_scan.total_seconds() < 1800  # 30 minutes = 1800 seconds
        
        if cache_valid:
            with st.sidebar:
                st.success("Using cached scan data")
                minutes_ago = int(time_since_scan.total_seconds() / 60)
                st.caption(f"Last scanned {minutes_ago} minutes ago")
                next_scan = 30 - minutes_ago
                st.caption(f"Next scan in ~{next_scan} minutes")

    # Automatic Background Scan (only if cache is invalid)
    if not cache_valid and st.session_state.scan_index < len(st.session_state.scan_queries):
        scanner = DisasterScanner()
        
        with st.sidebar:
            st.subheader("Background Scanning...")
            progress_bar = st.progress(st.session_state.scan_index / len(st.session_state.scan_queries))
            status_text = st.empty()
            if st.button("Stop Scan"):
                st.session_state.scan_index = len(st.session_state.scan_queries)
                st.rerun()

        # Starting the loop from the current index
        start_idx = st.session_state.scan_index
        for i in range(start_idx, len(st.session_state.scan_queries)):
            q_item = st.session_state.scan_queries[i]
            
            # Update status
            if q_item['type'] == 'general':
                status_text.text(f"Global: {q_item['query']}")
                raw_news = get_news_search(q_item['query'])
                texts = [line.strip() for line in raw_news.split("\n\n") if line.strip()]
                st.session_state.scan_results.extend(scanner.scan_texts(texts))
            else:
                status_text.text(f"Cell: {q_item['bundle']['h3']}")
                cell_res = scanner.scan_bundle_news(q_item['bundle'])
                if cell_res['severity'] >= 0:
                    st.session_state.scan_results.append(cell_res)
            
            # Update state and progress
            st.session_state.scan_index = i + 1
            
            # Update UI every 3 items to reduce lag (throttling)
            if i % 3 == 0 or (i + 1) == len(st.session_state.scan_queries):
                # Deduplicate results
                unique_res = {}
                for r in st.session_state.scan_results:
                    key = r.get('cell') or r.get('text')
                    unique_res[key] = r
                st.session_state.scan_results = list(unique_res.values())
                
                # Update map and progress bar live
                map_container.pydeck_chart(create_pydeck_map())
                progress_bar.progress((i + 1) / len(st.session_state.scan_queries))

        status_text.success("Initial Scan Complete")
        st.session_state.last_scan_time = datetime.datetime.now()
        save_scan_cache(st.session_state.scan_results, st.session_state.last_scan_time)

def chatbot_widget():
    # Create floating chat widget container
    chat_widget_container = st.container()

    with chat_widget_container:
        # Toggle button
        with st.expander("Talk with chatbot..."):
            # Chat interface when open
            st.markdown("### 🤖 Disaster Assistant")
            
            # Chat messages container with scrollable area
            chat_messages_container = st.container(height=400)
            with chat_messages_container:
                if not st.session_state.global_messages:
                    st.info("👋 Hello! I'm your disaster assistant. Ask me about current disasters, alerts, or emergency information.")
                else:
                    for msg in st.session_state.global_messages:
                        with st.chat_message(msg["role"]):
                            st.markdown(msg["content"])
            
            # Chat input
            user_input = st.chat_input("Ask about disasters, alerts, or emergencies...", key="global_chat_input")
            
            if user_input:
                # Add user message
                st.session_state.global_messages.append({"role": "user", "content": user_input})
                
                # Initialize agent if needed
                if st.session_state.global_agent is None:
                    st.session_state.global_agent = DisasterAgent(
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
                
                # Get response from agent
                with st.spinner("Thinking..."):
                    response = st.session_state.global_agent.get_response(
                        user_input,
                        history=[
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.global_messages[:-1]
                        ]
                    )
                
                # Add assistant response
                st.session_state.global_messages.append({"role": "assistant", "content": response})
                st.rerun()
            
            # Clear chat button
            if st.button("🗑️ Clear Chat", key="clear_global_chat", width="stretch"):
                st.session_state.global_messages = []
                st.session_state.global_agent = None
                st.rerun()

    if st.context.theme.type == "dark":
        bg_color = "#0E1117"
    else:
        bg_color = "#FFFFFF"

    # Float the chat widget to bottom left
    chat_widget_container.float(
        "bottom: 20px; right: 20px; width: 400px;"
        f"background-color: {bg_color};"
        "z-index: 1000;"
    )

def scroll_to_heatmap_widget():
    scroll_to_heatmap_container = st.container()
    
    with scroll_to_heatmap_container:
        with st.container(border=True):
            st.markdown(":material/south: **View Heatmap**")

    scroll_to_heatmap_container.float(
        "bottom: 75px; right: 20px; "
        "width: 160px; "
        "border-radius: 10px; "
        "box-shadow: 0 4px 12px rgba(0,0,0,0.1); "
        "transition: all 0.5s ease-in-out; "
        "animation: bounce 2s infinite;"
    )

def main():
    head_col1, head_col2 = st.columns([1.5, 5], vertical_alignment="center")
    
    with head_col1:
        try:
            st.image("Images/Presidential_Ai_Challenge_Logo.png", width=160)
        except:
            # Fallback icon if image is missing
            st.warning("⚠️ Logo missing")

    with head_col2:  
        st.markdown("<h1><span class='title' style='color: lightblue;'>Ai</span>dvisor</h1>", unsafe_allow_html=True)
        st.header("The Future of Disaster Response")
        st.markdown(
            "#### Connecting communities with AI-coordination to save lives, time, and money."
        )

    st.divider()

    st.markdown("### :material/chart_data: The Cost of Uncoordinated Chaos")
    st.write("Disasters are expensive, but the logistics gap—wasted time and unused skills—costs even more.")

    with st.container(border=True):
        m1, m2, m3 = st.columns(3)
        
        with m1:
            st.metric(
                label="2024 Disaster Costs (US)",
                value="$182.7 Billion",
                delta="4th Costliest Year on Record",
                delta_color="inverse",
                help="Source: NOAA NCEI 2024 Billion-Dollar Disaster Report (Jan 2025 Update)"
            )
        
        with m2:
            st.metric(
                label="Value of a Volunteer Hour",
                value="$34.79 / hr",
                delta="+3.9% from 2023",
                help="Source: Independent Sector & Do Good Institute (April 2025 Release)"
            )
        
        with m3:
            st.metric(
                label="Wasted Volunteer Capacity",
                value="65% Unused",
                delta="Offers of help rejected/lost",
                delta_color="inverse",
                help="Source: Red Cross & GWU Research on Spontaneous Unaffiliated Volunteers (SUV). Most walk-in volunteers are turned away due to lack of coordination systems."
            )

    st.info(
        "**How :blue-background[Aidvisor] Solves It:**\n\n"
        "Instead of turning volunteers away, :blue-background[Aidvisor] treats relief work as **'Bounties'** and uses AI to aggregate and distill fragmented information from agencies, shelters, and community groups—so volunteers see only clear, relevant tasks with the skills, time, and instructions they need. Our matching engine then routes verified volunteers to the right bounties and keeps coordination synchronized in real time. By connecting helpers and organizations on a national platform, we reduce duplication, increase utilization, and unlock the estimated :green[$34.79/hr] value of every neighbor—closing the current :red[65%] utilization gap and maximizing impact where it matters most."
    )
    scroll_to_heatmap_widget()
    heatmap()

pages = [
    st.Page(main, title="Home", icon=":material/home:"),
    st.Page("pages/1_Login.py", title="Login", icon=":material/login:"),
    st.Page("pages/9_Bounty_Board.py", title="Bounty Board", icon=":material/assignment:"),
    st.Page("pages/2_Chatbot.py", title="Chatbot", icon=":material/chat:"),
    st.Page("pages/5_Groups.py", title="Groups", icon=":material/groups:"),
    st.Page("pages/10_Audio_Recorder.py", title="Audio Recorder", icon=":material/mic:"),
    st.Page("pages/8_Profile.py", title="Profile", icon=":material/person:"),
]

pg = st.navigation(pages)

if pg.title != "Login":
    # Create a single-row layout with two columns: left empty, right for button
    _, col_right = st.columns([9, 1])  # adjust ratio for spacing

    with col_right:
        if not st.session_state.get("user_id"):
            if st.button("Login"):
                st.switch_page("pages/1_Login.py")
        else:
            conn = st.connection("supabase", type=SupabaseConnection)
            if st.button("Logout"):
                try:
                    conn.auth.sign_out()
                except:
                    pass
                sign_out()

# Initialize chat state
if "global_messages" not in st.session_state:
    st.session_state.global_messages = []
if "global_chat_open" not in st.session_state:
    st.session_state.global_chat_open = False
if "global_agent" not in st.session_state:
    st.session_state.global_agent = None


if pg.title != "Login" and st.session_state.get("user_id") != None:
    chatbot_widget()

pg.run()
