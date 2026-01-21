import streamlit as st

def init_session_state():
    hf_key_default = ''
    try:
        hf_key_default = st.secrets.get("api_keys", {}).get("NOVITA_API_KEY", '')
    except Exception as error:
        print(error)

    for key, val in [('logged_in', False), ('username', None), ('messages', []),
                    ('global_messages', []), ('global_chat_open', False),
                    ('hf_api_key', hf_key_default), ('hf_model_id', 'deepseek/deepseek-v3-turbo'), ('scan_results', []), 
                    ('scan_index', 0), ('scan_queries', []), ('last_scan_time', None),
                    ('access_token', None), ('refresh_token', None), ('user_info', None)]:
        if key not in st.session_state: st.session_state[key] = val