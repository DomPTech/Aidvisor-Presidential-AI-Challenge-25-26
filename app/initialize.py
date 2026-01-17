import streamlit as st

def init_session_state():
    hf_key_default = ''
    try:
        hf_key_default = st.secrets.get("api_keys", {}).get("HUGGINGFACE_API_KEY", '')
    except Exception as error:
        print(error)

    for key, val in [('logged_in', False), ('username', None), ('messages', []),
                    ('hf_api_key', hf_key_default), ('hf_model_id', 'deepseek-ai/DeepSeek-R1'), ('scan_results', []), 
                    ('scan_index', 0), ('scan_queries', []), ('last_scan_time', None)]:
        if key not in st.session_state: st.session_state[key] = val