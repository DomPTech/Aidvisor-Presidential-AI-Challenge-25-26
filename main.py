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
import time
from app.chatbot.chatbot import DisasterAgent
from app.chatbot.tools.google_news import get_google_news
from app.chatbot.tools.nws_alerts import get_nws_alerts
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
                if "users" not in data: data["users"] = {}
                if "group_messages" not in data: data["group_messages"] = []
                if "dm_history" not in data: data["dm_history"] = []
                return data
        except:
            pass
    return {"users": {}, "group_messages": [], "dm_history": []}


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
    np.random.seed(42)
    num_heatmap_points = 0
    low_priority_lat = np.random.normal(initial_location[0], 5, num_heatmap_points)
    low_priority_lon = np.random.normal(initial_location[1], 10, num_heatmap_points)
    heatmap_data = [[lat, lon, 1] for lat, lon in zip(low_priority_lat, low_priority_lon)]
    HeatMap(data=heatmap_data, radius=18, blur=18, gradient={0.2: 'blue', 0.8: 'red'}).add_to(m)
    num_circle_points = 10
    circle_lat = np.random.normal(34.05, 1, num_circle_points)
    circle_lon = np.random.normal(-118.24, 2, num_circle_points)
    circle_data = pd.DataFrame(
        {'lat': circle_lat, 'lon': circle_lon, 'impact_radius_m': np.random.randint(1500, 5000, num_circle_points)})
    for index, row in circle_data.iterrows():
        folium.Circle(location=[row['lat'], row['lon']], radius=row['impact_radius_m'], color="blue", fill=True,
                      fill_opacity=0.3, popup=f"Fixed Impact Zone: {row['impact_radius_m'] / 1000:.1f} km").add_to(m)
    high_priority_data = pd.DataFrame({'lat': np.random.normal(37, 2, 5), 'lon': np.random.normal(-100, 5, 5),
                                       'incident': [f"Critical Incident {i}" for i in range(5)],
                                       'status': ["Urgent" if i % 2 == 0 else "Severe" for i in range(5)]})
    for index, row in high_priority_data.iterrows():
        color = 'darkred' if row['status'] == 'Urgent' else 'red'
        icon = folium.Icon(color=color, icon='fire', prefix='fa')
        folium.Marker(location=[row['lat'], row['lon']], popup=f"Critical Incident: {row['incident']}",
                      tooltip=row['incident'], icon=icon).add_to(m)
    if 'custom_incidents' in st.session_state:
        for incident in st.session_state.custom_incidents:
            selected_icon_name = incident.get('Icon', FLOODING_ICONS["📍 Default Pin"])
            folium.Marker(location=[incident['Latitude'], incident['Longitude']],
                          popup=f"<b>{incident['Title']}</b><hr>Needs: {incident['Needs']}", tooltip=incident['Title'],
                          icon=folium.Icon(color='orange', icon=selected_icon_name, prefix='fa')).add_to(m)
    return m


def render_volunteering_view():
    st.header("🤝 Volunteer & Donation Coordination")
    st.write("Input your information to receive AI-driven recommendations.")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("📋 Your Information")
        with st.form("volunteer_info_form"):
            location = st.text_input("Location", placeholder="e.g., Nashville, TN")
            skills = st.text_area("Your Skills")
            interests = st.multiselect("Interests",
                                       options=["On-site Volunteering", "Remote Support", "Donations", "Coordination",
                                                "Medical Assistance"], default=["On-site Volunteering"])
            col_date, col_time = st.columns(2)
            sel_date = col_date.date_input("Select Date", value=datetime.date.today())
            sel_time = col_time.time_input("Select Time", value=datetime.time(9, 0))
            availability = f"{sel_date} at {sel_time}"
            submit_info = st.form_submit_button("Get AI Recommendations")
            if submit_info:
                if not location:
                    st.error("Please provide your location.")
                else:
                    user_info = {"location": location, "skills": skills, "interests": ", ".join(interests),
                                 "availability": availability}
                    with st.spinner("Generating recommendations..."):
                        recommendation = get_recommendations(user_info, st.session_state.hf_api_key)
                        st.session_state.volunteer_recommendation = recommendation
                        data = load_data()
                        if st.session_state.username and st.session_state.username in data["users"]:
                            user_record = data["users"][st.session_state.username]
                            user_record["points"] = user_record.get("points", 0) + 10
                            if "history" not in user_record:
                                user_record["history"] = []
                            user_record["history"].append({
                                "activity": f"Volunteered at {location}",
                                "points": 10,
                                "date": str(sel_date)
                            })
                            save_data(data)
                        st.success("Recommendations generated!")
    with col2:
        st.subheader("💡 AI Recommendations")
        if 'volunteer_recommendation' in st.session_state and st.session_state.volunteer_recommendation:
            st.markdown(f"{st.session_state.volunteer_recommendation}")


def render_groups_view():
    st.header("👥 Groups & Messaging")
    data = load_data()
    tab1, tab2, tab3 = st.tabs(["Public Chat", "Direct Messages", "🏆 Leaderboard"])
    me = st.session_state.username

    with tab1:
        for m in data["group_messages"]:
            with st.chat_message("user"):
                st.write(f"**{m['u']}** ({get_badge(m['u'])}): {m['c']}")
        if p := st.chat_input("Message group...", key="public_chat_input"):
            data["group_messages"].append({"u": me or "Guest", "c": p})
            save_data(data)
            st.rerun()

    with tab2:
        if not me:
            st.warning("Please sign in to view messages.")
        else:
            active_contacts = set()
            for m in data["dm_history"]:
                if m['from'] == me: active_contacts.add(m['to'])
                if m['to'] == me: active_contacts.add(m['from'])

            contact_options = []
            user_last_read = data["users"].get(me, {}).get("last_read_times", {})

            for contact in active_contacts:
                unread_count = 0
                last_read = user_last_read.get(contact, 0)
                for msg in data["dm_history"]:
                    if msg['from'] == contact and msg['to'] == me:
                        if msg.get('timestamp', 0) > last_read:
                            unread_count += 1
                label = f"{contact} ({unread_count} new)" if unread_count > 0 else contact
                contact_options.append({"label": label, "id": contact})

            col_list, col_chat = st.columns([1, 2])
            with col_list:
                st.subheader("My Conversations")
                display_labels = [c["label"] for c in contact_options] + ["New Message..."]
                selection = st.radio("Select a chat:", options=display_labels)
                recipient = next((c["id"] for c in contact_options if c["label"] == selection), None)
                if selection == "New Message...":
                    recipient = st.selectbox("Start chat with:", options=[u for u in data["users"].keys() if u != me])

            with col_chat:
                st.subheader(f"Chat with {recipient}")
                if recipient and recipient != "New Message...":
                    if "last_read_times" not in data["users"][me]: data["users"][me]["last_read_times"] = {}
                    data["users"][me]["last_read_times"][recipient] = time.time()
                    save_data(data)

                chat_container = st.container(height=400)
                with chat_container:
                    if recipient:
                        for msg in data["dm_history"]:
                            if (msg['from'] == me and msg['to'] == recipient):
                                with st.chat_message("user"):
                                    st.write(msg['content'])
                            elif (msg['from'] == recipient and msg['to'] == me):
                                with st.chat_message("assistant"):
                                    st.write(msg['content'])

                if dm_text := st.chat_input(f"Text {recipient}...", key="dm_chat_input"):
                    data["dm_history"].append(
                        {"from": me, "to": recipient, "content": dm_text, "timestamp": time.time()})
                    save_data(data)
                    st.rerun()

    with tab3:
        st.subheader("Top Contributors")
        user_list = [{"User": uname, "Points": uinfo.get("points", 0), "Badge": get_badge(uname)} for uname, uinfo in
                     data["users"].items()]
        if user_list:
            st.table(pd.DataFrame(user_list).sort_values(by="Points", ascending=False).reset_index(drop=True))


def render_top_bar():
    col_title, col_map, col_chat, col_pred, col_volun, col_groups, col_login = st.columns(
        [1.8, 1.0, 1.0, 1.0, 1.2, 1.0, 1.0])
    with col_title:
        st.title("Flooding Portal")

    def nav_button(col, label, mode):
        if col.button(label, key=f"nav_{mode}"):
            st.session_state.app_mode = mode;
            st.rerun()

    nav_button(col_map, "🗺️ Map View", "Map View")
    nav_button(col_chat, "🤖 Chatbot", "Chatbot")
    nav_button(col_pred, "📈 Prediction", "Prediction")
    nav_button(col_volun, "🤝 Volunteering", "Volunteering")
    nav_button(col_groups, "👥 Groups", "Groups")
    with col_login:
        if st.session_state.logged_in:
            if st.button(f"👤 {st.session_state.username}"): st.session_state.app_mode = "Profile"; st.rerun()
        else:
            if st.button("Login"): st.session_state.app_mode = "Login"; st.rerun()
    st.markdown("---")


def main():
    if 'app_mode' not in st.session_state: st.session_state.app_mode = "Map View"
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'username' not in st.session_state: st.session_state.username = None
    if 'custom_incidents' not in st.session_state: st.session_state.custom_incidents = []
    if 'messages' not in st.session_state: st.session_state.messages = []
    if 'hf_api_key' not in st.session_state: st.session_state.hf_api_key = ""

    st.set_page_config(page_title="Flooding Portal", layout="wide")
    with st.sidebar:
        st.title("Settings")
        st.session_state.hf_api_key = st.text_input("HuggingFace API Key", value=st.session_state.hf_api_key,
                                                    type="password")

    render_top_bar()
    mode = st.session_state.app_mode

    if mode == "Map View":
        st.header("Real-Time Incident Map")
        st_folium(create_folium_map(), width=1000, height=600)
    elif mode == "Chatbot":
        st.header("AI Assistance Chatbot")
        for message in st.session_state.messages:
            with st.chat_message(message["role"]): st.markdown(message["content"])
        if prompt := st.chat_input("How can I help?"):
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            agent = DisasterAgent(api_token=st.session_state.hf_api_key,
                                  tools={"get_google_news": get_google_news, "get_nws_alerts": get_nws_alerts})
            with st.chat_message("assistant"):
                response = agent.get_response(prompt, history=st.session_state.messages[:-1])
                st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
    elif mode == "Prediction":
        st.header("Flooding Prediction Models")
    elif mode == "Volunteering":
        render_volunteering_view()
    elif mode == "Groups":
        render_groups_view()
    elif mode == "Login":
        data = load_data()
        t1, t2 = st.tabs(["Sign In", "Create Account"])
        with t2:
            st.info("Password must be at least 6 characters.")
            nu = st.text_input("New Username", key="reg_u")
            npw = st.text_input("New Password", type="password", key="reg_p")
            if st.button("Register"):
                if nu and len(npw) >= 6:
                    if nu not in data["users"]:
                        data["users"][nu] = {"pw": npw, "points": 0, "history": [], "last_read_times": {}}
                        save_data(data)
                        # AUTO LOGIN
                        st.session_state.logged_in = True
                        st.session_state.username = nu
                        st.session_state.app_mode = "Map View"
                        st.rerun()
                    else:
                        st.error("Username already exists.")
                else:
                    st.error("Please provide a username and a password (min 6 chars).")
        with t1:
            u = st.text_input("Username", key="log_u")
            p = st.text_input("Password", type="password", key="log_p")
            if st.button("Sign In"):
                if u in data["users"] and data["users"][u]["pw"] == p:
                    st.session_state.logged_in = True
                    st.session_state.username = u
                    st.session_state.app_mode = "Map View"
                    st.rerun()
                else:
                    st.error("Incorrect username or password.")
    elif mode == "Profile":
        data = load_data()
        user_info = data["users"].get(st.session_state.username, {})
        st.header(f"Profile: {st.session_state.username}")
        st.subheader(f"Rank: {get_badge(st.session_state.username)}")
        st.write(f"Total Points: {user_info.get('points', 0)}")
        with st.expander("📜 My Activity History"):
            for item in reversed(user_info.get("history", [])):
                st.write(f"**{item['date']}**: {item['activity']} (+{item['points']} pts)")
        if st.button("Sign Out"):
            st.session_state.logged_in = False;
            st.session_state.app_mode = "Map View";
            st.rerun()


if __name__ == "__main__":
    main()