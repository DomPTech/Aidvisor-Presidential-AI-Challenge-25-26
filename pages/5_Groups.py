import streamlit as st
import pandas as pd
from app.common import load_data, save_data, get_badge

st.set_page_config(page_title="Flooding Coordination - Groups", layout="wide")

with st.sidebar:
    st.session_state.hf_api_key = st.text_input("HuggingFace API Key", value=st.session_state.hf_api_key,
                                                type="password")

st.header("👥 Groups & Messaging")
data = load_data()
tab1, tab2, tab3 = st.tabs(["Public Chat", "Direct Messages", "🏆 Leaderboard"])
with tab1:
    for m in data["group_messages"]:
        with st.chat_message("user"): st.write(f"**{m['u']}** ({get_badge(m['u'])}): {m['c']}")
    if p := st.chat_input("Message group..."):
        data["group_messages"].append({"u": st.session_state.username or "Guest", "c": p})
        save_data(data)
        st.rerun()
with tab2:
    me = st.session_state.username
    if not me:
        st.warning("Please sign in.")
    else:
        active_contacts = {m['from'] for m in data["dm_history"] if m['to'] == me} | {m['to'] for m in
                                                                                      data["dm_history"] if
                                                                                      m['from'] == me}
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
            for msg in data["dm_history"]:
                if (msg['from'] == me and msg['to'] == recipient):
                    with st.chat_message("user"):
                        st.write(msg['content'])
                elif (msg['from'] == recipient and msg['to'] == me):
                    with st.chat_message("assistant"):
                        st.write(msg['content'])
            if dm_text := st.chat_input(f"Text {recipient}..."):
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