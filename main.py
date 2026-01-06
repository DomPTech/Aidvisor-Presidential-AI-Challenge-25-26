import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import uuid
import datetime
import json
import os
from app.chatbot.chatbot import DisasterAgent
from app.chatbot.tools.google_news import get_google_news
from app.chatbot.tools.nws_alerts import get_nws_alerts
from app.chatbot.tools.openfema import get_fema_disaster_declarations, get_fema_assistance_data
from app.coordination.volunteering import get_recommendations

FLOODING_ICONS = {
    "💧 Water/Need": "tint",
    "🏠 Structure Damage": "house",
    "⚠️ Warning": "exclamation-triangle",
    "🚑 Medical Need": "medkit",
    "🚧 Road Block": "road",
    "📍 Default Pin": "map-pin",
}

DB_FILE = "data.json"


def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                if "notifications" not in data: data["notifications"] = []
                if "locations" not in data: data["locations"] = []
                if "users" not in data: data["users"] = {}
                if "group_messages" not in data: data["group_messages"] = []
                if "dm_history" not in data: data["dm_history"] = []
                return data
        except:
            pass
    return {"users": {}, "group_messages": [], "dm_history": [], "notifications": [], "locations": []}


def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)


def get_badge(username):
    data = load_data()
    user_info = data["users"].get(username, {})
    points = user_info.get("points", 0)
    if points >= 100: return "🏆 Platinum Hero"
    if points >= 50: return "🥇 Gold Responder"
    if points >= 20: return "🥈 Silver Helper"
    if points >= 5: return "🥉 Bronze Volunteer"
    return "🌱 New Member"


def create_folium_map():
    initial_location = [39.8283, -98.5795]
    m = folium.Map(location=initial_location, zoom_start=4, tiles="cartodbpositron")

    data = load_data()
    for incident in data.get("locations", []):
        selected_icon_name = incident.get('Icon', "map-pin")
        requester = incident.get('User', 'Anonymous')
        folium.Marker(
            location=[incident['Latitude'], incident['Longitude']],
            popup=f"<b>{incident['Title']}</b><hr>Needs: {incident['Needs']}<br>User: {requester}",
            tooltip=incident['Title'],
            icon=folium.Icon(color='orange', icon=selected_icon_name, prefix='fa')
        ).add_to(m)

    np.random.seed(42)
    num_heatmap_points = 0
    low_priority_lat = np.random.normal(initial_location[0], 5, num_heatmap_points)
    low_priority_lon = np.random.normal(initial_location[1], 10, num_heatmap_points)
    heatmap_data = [[lat, lon, 1] for lat, lon in zip(low_priority_lat, low_priority_lon)]
    HeatMap(data=heatmap_data, radius=18, blur=18, gradient={0.2: 'blue', 0.8: 'red'}).add_to(m)

    return m


def render_volunteering_view():
    st.header("🤝 Volunteer & Donation Coordination")
    data = load_data()

    st.subheader("🤖 AI Area Recommendations")
    if 'volunteer_recommendation' in st.session_state and st.session_state.volunteer_recommendation:
        st.markdown(f"{st.session_state.volunteer_recommendation}")
    else:
        st.info("Fill out the information below to see personalized recommendations.")

    st.divider()
    action_mode = st.selectbox("Select Action:", ["Volunteer & Help", "Request Assistance", "Manage My Requests"])
    col1, col2 = st.columns([1, 1])

    if action_mode == "Volunteer & Help":
        with col1:
            st.subheader("📋 Your Information")
            with st.form("volunteer_info_form"):
                location = st.text_input("Location", placeholder="e.g., Nashville, TN")
                comments = st.text_area("Comments")
                interests = st.multiselect("Interests", options=["On-site", "Remote", "Donations", "Medical"],
                                           default=["On-site"])
                col_date, col_time = st.columns(2)
                sel_date = col_date.date_input("Select Date", value=datetime.date.today())
                sel_time = col_time.time_input("Select Time", value=datetime.time(9, 0))

                b_col1, b_col2 = st.columns(2)
                submit_info = b_col1.form_submit_button("Get AI Recommendations")
                submit_volunteer = b_col2.form_submit_button("Volunteer & Help")

                if submit_info:
                    if not location:
                        st.error("Provide location.")
                    else:
                        user_info = {"location": location, "comments": comments, "interests": ", ".join(interests),
                                     "availability": f"{sel_date} at {sel_time}"}
                        with st.spinner("Generating..."):
                            rec = get_recommendations(user_info, st.session_state.hf_api_key)
                            st.session_state.volunteer_recommendation = rec
                            st.rerun()

                if submit_volunteer:
                    if not location:
                        st.error("Provide location.")
                    elif st.session_state.username:
                        data["users"][st.session_state.username]["points"] += 10
                        data["users"][st.session_state.username]["history"].append({
                            "activity": f"Volunteered at {location}", "points": 10, "date": str(sel_date)
                        })
                        save_data(data)
                        st.success("Successfully volunteered!")
                        st.rerun()

        with col2:
            st.subheader("📍 Nearby Requests")
            st_folium(create_folium_map(), width=550, height=450, key="vol_map_browse")

    elif action_mode == "Request Assistance":
        with col1:
            st.subheader("➕ Post a Help Request")
            with st.form("request_assistance_form"):
                req_title = st.text_input("Incident Title")
                req_needs = st.text_area("Specific Needs")
                req_cat = st.selectbox("Category", options=list(FLOODING_ICONS.keys()))
                lat = st.session_state.get('clicked_lat', 39.8283)
                lon = st.session_state.get('clicked_lon', -98.5795)
                st.write(f"Map Location: {lat:.4f}, {lon:.4f}")

                if st.form_submit_button("Post Request"):
                    if req_title and st.session_state.username:
                        new_incident = {
                            "id": str(uuid.uuid4()), "Title": req_title, "Needs": req_needs,
                            "Icon": FLOODING_ICONS[req_cat], "Latitude": lat, "Longitude": lon,
                            "User": st.session_state.username, "Timestamp": str(datetime.datetime.now())
                        }
                        data["locations"].append(new_incident)
                        save_data(data)
                        st.success("Request saved!")
                        st.rerun()
        with col2:
            st.subheader("📍 Click Map to Set Location")
            map_data = st_folium(create_folium_map(), width=550, height=450, key="vol_map_request")
            if map_data.get("last_clicked"):
                st.session_state.clicked_lat = map_data["last_clicked"]["lat"]
                st.session_state.clicked_lon = map_data["last_clicked"]["lng"]
                st.rerun()

    elif action_mode == "Manage My Requests":
        st.subheader("✅ Resolve Your Requests")
        my_requests = [loc for loc in data["locations"] if loc.get("User") == st.session_state.username]
        if not my_requests:
            st.info("No active requests.")
        else:
            for req in my_requests:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"**{req['Title']}**")
                    c1.caption(f"Needs: {req['Needs']}")
                    if c2.button("Resolve ✅", key=req['id']):
                        data["locations"] = [l for l in data["locations"] if l.get("id") != req['id']]
                        save_data(data)
                        st.success("Resolved!")
                        st.rerun()


def render_groups_view():
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
            recipient = col_list.radio("Conversations:", options=list(active_contacts) + ["New Message..."])
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
        user_list = [{"User": uname, "Points": uinfo.get("points", 0), "Badge": get_badge(uname)} for uname, uinfo in
                     data["users"].items()]
        if user_list: st.table(pd.DataFrame(user_list).sort_values(by="Points", ascending=False).reset_index(drop=True))


def render_top_bar():
    data = load_data()
    unread = len([n for n in data.get("notifications", []) if
                  n["to"] == st.session_state.username and not n["read"]]) if st.session_state.username else 0
    noti_label = f"🔔 ({unread})" if unread > 0 else "🔔"
    cols = st.columns([1.8, 1.0, 1.0, 1.0, 1.2, 1.0, 1.0, 0.8])
    cols[0].title("Flooding Portal")
    if cols[1].button("🗺️ Map"): st.session_state.app_mode = "Map View"; st.rerun()
    if cols[2].button("🤖 Chat"): st.session_state.app_mode = "Chatbot"; st.rerun()
    if cols[3].button("📈 Predict"): st.session_state.app_mode = "Prediction"; st.rerun()
    if cols[4].button("🤝 Volunteer"): st.session_state.app_mode = "Volunteering"; st.rerun()
    if cols[5].button("👥 Groups"): st.session_state.app_mode = "Groups"; st.rerun()
    if cols[6].button(noti_label): st.session_state.app_mode = "Notifications"; st.rerun()
    with cols[7]:
        if st.session_state.logged_in:
            if st.button(f"👤 {st.session_state.username}"): st.session_state.app_mode = "Profile"; st.rerun()
        else:
            if st.button("Login"): st.session_state.app_mode = "Login"; st.rerun()
    st.markdown("---")


def main():
    for key, val in [('app_mode', 'Map View'), ('logged_in', False), ('username', None), ('messages', []),
                     ('hf_api_key', '')]:
        if key not in st.session_state: st.session_state[key] = val
    st.set_page_config(page_title="Flooding Coordination", layout="wide")
    with st.sidebar:
        st.session_state.hf_api_key = st.text_input("HuggingFace API Key", value=st.session_state.hf_api_key,
                                                    type="password")
    render_top_bar()
    mode = st.session_state.app_mode
    if mode == "Map View":
        st_folium(create_folium_map(), width=1000, height=600)
    elif mode == "Chatbot":
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        if prompt := st.chat_input("Help?"):
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            agent = DisasterAgent(api_token=st.session_state.hf_api_key,
                                  tools={
                                      "get_google_news": get_google_news, 
                                      "get_nws_alerts": get_nws_alerts,
                                      "get_fema_disaster_declarations": get_fema_disaster_declarations,
                                      "get_fema_assistance_data": get_fema_assistance_data
                                  })
            with st.chat_message("assistant"):
                res = agent.get_response(prompt, history=st.session_state.messages[:-1])
                st.markdown(res)
            st.session_state.messages.append({"role": "assistant", "content": res})
    elif mode == "Prediction":
        st.header("Prediction Models")
    elif mode == "Volunteering":
        render_volunteering_view()
    elif mode == "Groups":
        render_groups_view()
    elif mode == "Notifications":
        st.header("Notifications")
        data = load_data()
        my_notifs = [n for n in data.get("notifications", []) if n["to"] == st.session_state.username]
        for n in reversed(my_notifs): st.warning(f"**{n['from']}**: {n['message']}")
        if st.button("Mark Read"):
            for n in data["notifications"]:
                if n["to"] == st.session_state.username: n["read"] = True
            save_data(data);
            st.rerun()
    elif mode == "Login":
        data = load_data()
        t1, t2 = st.tabs(["Sign In", "Create Account"])
        with t2:
            nu, npw = st.text_input("New User"), st.text_input("New Password", type="password")
            if st.button("Register") and nu not in data["users"]:
                data["users"][nu] = {"pw": npw, "points": 0, "history": []}
                save_data(data);
                st.success("Created!")
        with t1:
            u, p = st.text_input("User"), st.text_input("Password", type="password")
            if st.button("Sign In") and u in data["users"] and data["users"][u]["pw"] == p:
                st.session_state.logged_in, st.session_state.username, st.session_state.app_mode = True, u, "Map View";
                st.rerun()
    elif mode == "Profile":
        data = load_data()
        user_info = data["users"].get(st.session_state.username, {})
        st.header(f"Profile: {st.session_state.username} ({get_badge(st.session_state.username)})")
        st.write(f"Points: {user_info.get('points', 0)}")
        if st.button("Sign Out"): st.session_state.logged_in = False; st.session_state.app_mode = "Map View"; st.rerun()


if __name__ == "__main__":
    main()