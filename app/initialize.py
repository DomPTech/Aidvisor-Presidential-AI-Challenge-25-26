import streamlit as st

def init_session_state():
    for key, val in [('logged_in', False), ('username', None), ('messages', []),
                    ('hf_api_key', ''), ('hf_model_id', 'deepseek-ai/DeepSeek-R1'), ('scan_results', []), 
                    ('scan_index', 0), ('scan_queries', []), ('last_scan_time', None)]:
        if key not in st.session_state: st.session_state[key] = val