import streamlit as st
import datetime
import h3
from app.chatbot.chatbot import DisasterAgent
from app.chatbot.tools.ddg_search import get_news_search
from app.prediction.scanner import DisasterScanner
from app.prediction.geospatial import get_h3_location_bundles
from app.common import load_scan_cache, save_scan_cache, create_pydeck_map

def main():
    st.set_page_config(page_title="Flooding Coordination", layout="wide")

    # Initialize session state
    for key, val in [('logged_in', False), ('username', None), ('messages', []),
                     ('hf_api_key', ''), ('hf_model_id', 'deepseek-ai/DeepSeek-R1'), ('scan_results', []), 
                     ('scan_index', 0), ('scan_queries', []), ('last_scan_time', None)]:
        if key not in st.session_state: st.session_state[key] = val
    
    with st.sidebar:
        st.session_state.hf_api_key = st.text_input("HuggingFace API Key", value=st.session_state.hf_api_key,
                                                    type="password")

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
                st.divider()
                st.success("Using cached scan data")
                minutes_ago = int(time_since_scan.total_seconds() / 60)
                st.caption(f"Last scanned {minutes_ago} minutes ago")
                next_scan = 30 - minutes_ago
                st.caption(f"Next scan in ~{next_scan} minutes")

    # Automatic Background Scan (only if cache is invalid)
    if not cache_valid and st.session_state.scan_index < len(st.session_state.scan_queries):
        scanner = DisasterScanner()
        
        with st.sidebar:
            st.divider()
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


if __name__ == "__main__":
    main()