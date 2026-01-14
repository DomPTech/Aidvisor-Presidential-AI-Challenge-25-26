import streamlit as st
import pandas as pd
from app.common import load_data, save_data, get_badge
from st_supabase_connection import SupabaseConnection
import datetime

st.set_page_config(page_title="Flooding Coordination - Groups", layout="wide")

with st.sidebar:
    st.session_state.hf_api_key = st.text_input("HuggingFace API Key", 
                                                value=st.session_state.get("hf_api_key", ""),
                                                type="password")

st.header("👥 Groups & Messaging")

# Initialize Supabase connection
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception as e:
    st.error(f"Failed to connect to Supabase: {e}")
    conn = None

data = load_data()
tab1, tab2, tab3 = st.tabs(["Public Chat", "Direct Messages", "🏆 Leaderboard"])

with tab1:
    if not st.session_state.get("logged_in"):
        st.warning("You must be logged in to view and participate in the group chat.")
        if st.button("Log In"):
            st.switch_page("pages/1_Login.py")
    else:
        @st.fragment(run_every=2)
        def show_messages():
            # Fetch messages from Supabase
            # Schema: id, user_id, message_text, created_at
            messages = []
            if conn:
                try:
                    response = conn.table("messages").select("*").order("created_at", desc=False).execute()
                    messages = response.data
                except Exception as e:
                    st.error(f"Error fetching messages: {e}")

            # Display messages
            current_user_id = st.session_state.get("user_id")
            
            for m in messages:
                msg_user_id = m.get("user_id")
                text = m.get("message_text", "")
                
                is_me = (msg_user_id == current_user_id)
                
                # Using 'user' icon for everyone, distinguish by name/text
                with st.chat_message("user" if is_me else "assistant"):
                    prefix = "You" if is_me else f"User {msg_user_id[:6] if msg_user_id else 'Unknown'}"
                    st.markdown(f"**{prefix}**: {text}")
        
        show_messages()

        # Chat input
        if prompt := st.chat_input("Message group..."):
            current_user_id = st.session_state.get("user_id")
            if current_user_id and conn:
                try:
                    conn.table("messages").insert({
                        "user_id": current_user_id,
                        "message_text": prompt
                    }).execute()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to send message: {e}")

with tab2:
    me = st.session_state.get("username")
    if not me:
        st.warning("Please sign in.")
    else:
        # Existing logic for Direct Messages
        active_contacts = {m['from'] for m in data["dm_history"] if m['to'] == me} | \
                          {m['to'] for m in data["dm_history"] if m['from'] == me}
        col_list, col_chat = st.columns([1, 2])

        default_index = 0
        open_target = st.session_state.get("dm_open_target")

        options_list = list(active_contacts) + ["New Message..."]
        if open_target and open_target in options_list:
            default_index = options_list.index(open_target)
        elif open_target:
            options_list = [open_target] + options_list
            default_index = 0

        recipient = col_list.radio("Conversations:", options=options_list, index=default_index)

        if recipient == "New Message...":
            recipient = col_list.selectbox("Select User:", options=[u for u in data["users"].keys() if u != me])
        
        with col_chat:
            if recipient:
                for msg in data["dm_history"]:
                    if (msg['from'] == me and msg['to'] == recipient):
                        with st.chat_message("user"):
                            st.write(msg['content'])
                    elif (msg['from'] == recipient and msg['to'] == me):
                        with st.chat_message("assistant"):
                            st.write(msg['content'])
                
                if dm_text := st.chat_input(f"Text {recipient}...", key="dm_input"):
                    data["dm_history"].append({"from": me, "to": recipient, "content": dm_text})
                    save_data(data)
                    st.rerun()

with tab3:
    # Filtered leaderboard to remove admin
    user_list = [{"User": uname, "Points": uinfo.get("points", 0), "Badge": get_badge(uname)}
                 for uname, uinfo in data["users"].items() if uname != "admin"]
    if user_list:
        st.table(pd.DataFrame(user_list).sort_values(by="Points", ascending=False).reset_index(drop=True))
    else:
        st.info("No volunteers on the leaderboard yet.")