import streamlit as st
import pandas as pd
from app.chatbot.tools.ddg_search import get_news_search
from app.prediction.scanner import DisasterScanner
from app.common import save_scan_cache
import app.initialize as session_init

st.set_page_config(page_title="Flooding Coordination - Prediction", layout="wide")

session_init.init_session_state()

with st.sidebar:
    st.session_state.hf_api_key = st.text_input("Novita API Key", value=st.session_state.hf_api_key,
                                                type="password")

st.header("🔍 Real-time Disaster Scanning")
st.write("Scan recent news and weather alerts using local BERT model to identify severity and locations.")

col1, col2 = st.columns([1, 1])
with col1:
    scan_query = st.text_input("Search Location/Topic for Scan", value="Flooding in Tennessee")
    if st.button("🚀 Start Deep Scan"):
        with st.spinner("Fetching data and running BERT analysis..."):
            # Fetch data from tools
            recent_news = get_news_search(scan_query)
            
            # Extract texts to scan
            texts_to_scan = [line.strip() for line in recent_news.split("\n\n") if line.strip()]
            
            # Instantiate Local Scanner
            scanner = DisasterScanner()
            results = scanner.scan_texts(texts_to_scan)
            
            if results:
                st.session_state.scan_results = results
                st.session_state.last_scan_time = pd.Timestamp.now()
                save_scan_cache(st.session_state.scan_results, st.session_state.last_scan_time)
                st.success(f"Scan complete! Found {len(results)} relevant incidents with coordinates.")
                for res in results[:3]:
                    st.info(f"📍 Found {res['severity']} severity alert at ({res['lat']}, {res['lon']})")
            else:
                st.warning("Scan complete, but no specific coordinates could be extracted from the texts.")

if st.session_state.scan_results:
    st.divider()
    st.subheader("📊 Scan Results")
    df = pd.DataFrame(st.session_state.scan_results)
    # Display available columns dynamically
    display_cols = [col for col in ["severity", "lat", "lon", "location", "text"] if col in df.columns]
    st.dataframe(df[display_cols] if display_cols else df, use_container_width=True)
    
    if st.button("🗺️ View on Map"):
        st.switch_page("Main.py")