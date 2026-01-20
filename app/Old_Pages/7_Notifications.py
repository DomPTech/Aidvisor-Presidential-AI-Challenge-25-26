import streamlit as st
from app.common import load_data, save_data
from st_supabase_connection import SupabaseConnection
import app.initialize as session_init

st.set_page_config(page_title="Flooding Coordination - Notifications", layout="wide")

try:
    conn = st.connection("supabase", type=SupabaseConnection)
except:
    conn = None

session_init.init_session_state()

unread_count = 0
if conn and st.session_state.get("user_id"):
    try:
        unread_res = conn.table("direct_messages").select("id", count="exact").eq("recipient_id",
                                                                                  st.session_state.user_id).eq("read",
                                                                                                               False).execute()
        unread_count = unread_res.count if unread_res.count else 0
    except:
        pass

st.header(f"🔔 Notifications ({unread_count})")

with st.sidebar:
    st.session_state.hf_api_key = st.text_input("Novita API Key", value=st.session_state.get("hf_api_key", ""),
                                                type="password")

profiles = {}
if conn:
    try:
        prof_res = conn.table("profiles").select("id, first_name, last_name").execute()
        for p in prof_res.data:
            fn = p.get('first_name', '')
            ln = p.get('last_name', '')
            full = f"{fn} {ln}".strip()
            profiles[p['id']] = full if full else p['id']
    except:
        pass

data = load_data()
my_notifs = [n for n in data.get("notifications", []) if
             n["to"] == st.session_state.username and not n.get("read", False)]

if conn and st.session_state.get("user_id"):
    try:
        res = conn.table("direct_messages").select("*").eq("recipient_id", st.session_state.user_id).eq("read",
                                                                                                        False).execute()
        for dm in res.data:
            sender_id = dm["sender_id"]
            sender_name = profiles.get(sender_id, f"User {sender_id[:6]}")
            my_notifs.append({
                "from": f"DM from {sender_name}",
                "message": dm["message_text"],
                "read": False
            })
    except:
        pass

for n in reversed(my_notifs):
    st.warning(f"**{n['from']}**: {n['message']}")

if st.button("Mark Read"):
    new_notifs = []
    for n in data.get("notifications", []):
        if n["to"] == st.session_state.username:
            n["read"] = True
        else:
            new_notifs.append(n)
    data["notifications"] = new_notifs
    save_data(data)

    if conn and st.session_state.get("user_id"):
        try:
            conn.table("direct_messages").update({"read": True}).eq("recipient_id", st.session_state.user_id).execute()
        except:
            pass
    st.rerun()