import streamlit as st
import pandas as pd
from app.common import load_data, save_data, get_badge
from st_supabase_connection import SupabaseConnection
import datetime
import app.initialize as session_init

st.set_page_config(page_title="Flooding Coordination - Groups", layout="wide")

session_init.init_session_state()

st.title("Groups & Messaging")

try:
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception as e:
    st.error(f"Failed to connect to Supabase: {e}")
    conn = None

data = load_data()
profiles = {}
if conn:
    try:
        prof_res = conn.table("profiles").select("id, first_name, last_name").execute()
        for p in prof_res.data:
            fn = p.get('first_name', '')
            ln = p.get('last_name', '')
            full = f"{fn} {ln}".strip()
            profiles[p['id']] = full if full else None
    except Exception as e:
        st.error(f"Error fetching profiles: {e}")

query_params = st.query_params
dm_id = query_params.get("dm_id", None)

tab1, tab2, tab3 = st.tabs(["Public Chat", "Direct Messages", "Leaderboard"], default="Public Chat" if not dm_id else "Direct Messages")

with tab1:
    if not st.session_state.get("logged_in"):
        st.warning("You must be logged in to view and participate in the group chat.")
    else:
        @st.fragment(run_every=2)
        def show_messages():
            messages = []
            if conn:
                try:
                    response = conn.table("messages").select("*").order("created_at", desc=False).execute()
                    messages = response.data
                except Exception as e:
                    st.error(f"Error fetching messages: {e}")

            current_user_id = st.session_state.get("user_id")

            with st.container(height=400):
                for m in messages:
                    msg_user_id = m.get("user_id")
                    text = m.get("message_text", "")

                    is_me = (msg_user_id == current_user_id)

                    user_name = profiles.get(msg_user_id)
                    if user_name:
                        prefix = "You" if is_me else user_name
                    else:
                        prefix = "You" if is_me else f"User {msg_user_id[:6] if msg_user_id else 'Unknown'}"

                    with st.chat_message("🧑‍💻" if is_me else "🙋"):
                        st.markdown(f"**{prefix}**: {text}")

        show_messages()

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
    me_id = st.session_state.get("user_id")
    if not me_id:
        st.warning("Please sign in.")
    else:
        col_list, col_chat = st.columns([1, 2])

        with col_list:
            all_users = []
            if conn:
                try:
                    user_res = conn.table("profiles").select("id, first_name, last_name").execute()
                    all_users = user_res.data
                except:
                    all_users = [{"id": k, "first_name": k, "last_name": ""} for k in data["users"].keys()]

            user_options = {}
            id_to_user = {}
            for u in all_users:
                if u["id"] != me_id:
                    fn = u.get('first_name', '')
                    ln = u.get('last_name', '')
                    full = f"{fn} {ln}".strip()
                    if full:
                        user_options[full] = u["id"]
                    else:
                        user_options[u["id"]] = u["id"]
                    id_to_user[u["id"]] = full if full else u["id"]
            
            default_name = None            
            if dm_id:
                print("DM ID:", dm_id)
                recipient_id = dm_id[0]
                for name, uid in user_options.items():
                    if uid == recipient_id:
                        default_name = name
                        break
                    
            index = list(id_to_user.keys()).index(dm_id) if dm_id else None
            print(index)
                    
            recipient_name = st.selectbox("Find User to DM:", options=list(user_options.keys()), index=index, placeholder="Search/Select a user...")
            recipient_id = user_options.get(recipient_name)

        with col_chat:
            if recipient_id:
                @st.fragment(run_every=2)
                def show_dms(target_id, target_name):
                    dm_messages = []
                    if conn:
                        try:
                            res = conn.table("direct_messages").select("*").or_(
                                f"and(sender_id.eq.{me_id},recipient_id.eq.{target_id}),"
                                f"and(sender_id.eq.{target_id},recipient_id.eq.{me_id})"
                            ).order("created_at", desc=False).execute()
                            dm_messages = res.data
                        except Exception as e:
                            st.error(f"Error loading messages: {e}")

                    with st.container(height=400):
                        for msg in dm_messages:
                            sender_id = msg["sender_id"]
                            is_me = sender_id == me_id
                            sender_name = profiles.get(sender_id)
                            if sender_name:
                                prefix = "You" if is_me else sender_name
                            else:
                                prefix = "You" if is_me else f"User {sender_id[:6]}"
                            with st.chat_message("🧑‍💻" if is_me else "🙋"):
                                st.write(f"**{prefix}**: {msg['message_text']}")


                show_dms(recipient_id, recipient_name)

                if dm_text := st.chat_input(f"Text {recipient_name}...", key="dm_input"):
                    if conn:
                        try:
                            conn.table("direct_messages").insert({
                                "sender_id": me_id,
                                "recipient_id": recipient_id,
                                "message_text": dm_text
                            }).execute()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to send: {e}")

with tab3:
    user_list = [{"User": uname, "Points": uinfo.get("points", 0), "Badge": get_badge(uname)}
                 for uname, uinfo in data["users"].items() if uname != "admin"]
    if user_list:
        st.table(pd.DataFrame(user_list).sort_values(by="Points", ascending=False).reset_index(drop=True))
    else:
        st.info("No volunteers on the leaderboard yet.")