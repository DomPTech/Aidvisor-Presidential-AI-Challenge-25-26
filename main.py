import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap
from streamlit_folium import folium_static
import uuid
from app.chatbot.chatbot import DisasterAgent

FLOODING_ICONS = {
    "💧 Water/Need": "tint",
    "🏠 Structure Damage": "house",
    "⚠️ Warning": "exclamation-triangle",
    "🚑 Medical Need": "medkit",
    "🚧 Road Block": "road",
    "📍 Default Pin": "map-pin",
}


def create_folium_map():
    initial_location = [39.8283, -98.5795]
    m = folium.Map(location=initial_location, zoom_start=4, tiles="cartodbpositron")
    np.random.seed(42)

    num_heatmap_points = 0
    low_priority_lat = np.random.normal(initial_location[0], 5, num_heatmap_points)
    low_priority_lon = np.random.normal(initial_location[1], 10, num_heatmap_points)
    heatmap_data = [[lat, lon, 1] for lat, lon in zip(low_priority_lat, low_priority_lon)]

    HeatMap(
        data=heatmap_data,
        radius=18,
        blur=18,
        gradient={0.2: 'blue', 0.8: 'red'}
    ).add_to(m)

    num_circle_points = 10
    circle_lat = np.random.normal(34.05, 1, num_circle_points)
    circle_lon = np.random.normal(-118.24, 2, num_circle_points)
    circle_data = pd.DataFrame({
        'lat': circle_lat,
        'lon': circle_lon,
        'impact_radius_m': np.random.randint(1500, 5000, num_circle_points)
    })

    for index, row in circle_data.iterrows():
        folium.Circle(
            location=[row['lat'], row['lon']],
            radius=row['impact_radius_m'],
            color="blue",
            fill=True,
            fill_opacity=0.3,
            popup=f"Fixed Impact Zone: {row['impact_radius_m'] / 1000:.1f} km"
        ).add_to(m)

    high_priority_data = pd.DataFrame({
        'lat': np.random.normal(37, 2, 5),
        'lon': np.random.normal(-100, 5, 5),
        'incident': [f"Critical Incident {i}" for i in range(5)],
        'status': ["Urgent" if i % 2 == 0 else "Severe" for i in range(5)]
    })

    for index, row in high_priority_data.iterrows():
        color = 'darkred' if row['status'] == 'Urgent' else 'red'
        icon = folium.Icon(color=color, icon='fire', prefix='fa')

        folium.Marker(
            location=[row['lat'], row['lon']],
            popup=f"Critical Incident: {row['incident']}",
            tooltip=f"{row['incident']} - {row['status']}",
            icon=icon
        ).add_to(m)

    if 'custom_incidents' in st.session_state:
        for incident in st.session_state.custom_incidents:
            selected_icon_name = incident.get('Icon', FLOODING_ICONS["📍 Default Pin"])

            folium.Marker(
                location=[incident['Latitude'], incident['Longitude']],
                popup=f"""
                    <b>{incident['Title']}</b><hr style='margin: 5px 0;'>
                    Needs: {incident['Needs']}<br>
                    Coords: ({incident['Latitude']:.2f}, {incident['Longitude']:.2f})
                """,
                tooltip=incident['Title'],
                icon=folium.Icon(color='orange', icon=selected_icon_name, prefix='fa')
            ).add_to(m)

    return m

def render_volunteering_view():
    st.header("Volunteer Coordination: Report New Resource Needs")
    st.write(
        "Manually enter the details of a new critical location, its required supplies, and select a relevant icon.")

    with st.form("new_incident_form", clear_on_submit=True):
        st.subheader("Location and Needs Details")

        title = st.text_input("Incident Title (e.g., House Flooding)", key='form_title')

        col_lat, col_lon = st.columns(2)
        with col_lat:
            latitude_str = st.text_input("Latitude (e.g., 34.05)", key='form_lat')
        with col_lon:
            longitude_str = st.text_input("Longitude (e.g., -118.24)", key='form_lon')

        icon_display_name = st.selectbox(
            "Select Icon for Incident:",
            options=list(FLOODING_ICONS.keys()),
            key='form_icon_select'
        )

        needs = st.text_area("Required Needs (e.g., Water, Generator, Medical Staff)", key='form_needs')

        submitted = st.form_submit_button("Submit New Location to Map")

        if submitted:
            try:
                latitude = float(latitude_str)
                longitude = float(longitude_str)

                if not title or not needs:
                    st.error("Please fill in the Title and Required Needs.")
                elif not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                    st.error("Invalid Latitude/Longitude range.")
                else:
                    st.session_state.custom_incidents.append({
                        "Title": title,
                        "Latitude": latitude,
                        "Longitude": longitude,
                        "Needs": needs,
                        "Icon": FLOODING_ICONS[icon_display_name],  # Store the actual Font Awesome code
                        "id": str(uuid.uuid4())
                    })
                    st.success(f"Location '{title}' submitted and marked with icon '{icon_display_name}'.")

            except ValueError:
                st.error("Latitude and Longitude must be valid numbers.")

    st.write("---")

    st.subheader("Active User-Submitted Incidents")

    if st.session_state.custom_incidents:
        df = pd.DataFrame(st.session_state.custom_incidents)
        st.dataframe(df[['Title', 'Latitude', 'Longitude', 'Needs', 'Icon']])

        if st.button("Clear All Submitted Incidents"):
            st.session_state.custom_incidents = []
            st.rerun()
    else:
        st.info("No custom incident locations have been submitted yet.")


def render_top_bar():
    #LOGO_PATH = "logo.png"

    with st.container():
        col_logo, col_title, col_map, col_chat, col_pred, col_volun, col_groups, col_login = st.columns(
            [0.5, 1.8, 1.0, 1.0, 1.0, 1.2, 1.0, 1.0])

       # with col_logo:
        #       st.image(LOGO_PATH, width=50)
         #   except FileNotFoundError:
           #     st.markdown("## 🛡️")

        with col_title:
            st.title("Flooding Portal")

        def nav_button(col, label, mode):
            with col:
                st.markdown("<div style='padding-top: 15px;'>", unsafe_allow_html=True)
                if st.button(label, key=f"nav_{mode}"):
                    st.session_state.app_mode = mode
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        nav_button(col_map, "🗺️ Map View", "Map View")
        nav_button(col_chat, "🤖 Chatbot", "Chatbot")
        nav_button(col_pred, "📈 Prediction", "Prediction")
        nav_button(col_volun, "🤝 Volunteering", "Volunteering")
        nav_button(col_groups, "👥 Groups", "Groups")

        with col_login:
            st.markdown("<div style='padding-top: 15px;'>", unsafe_allow_html=True)
            if st.session_state.logged_in:
                if st.button(f"👤 {st.session_state.username}", key="nav_profile"):
                    st.session_state.app_mode = "Profile"
                    st.rerun()
            else:
                if st.button("Login", key="nav_login"):
                    st.session_state.app_mode = "Login"
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")

def main():
    if 'app_mode' not in st.session_state:
        st.session_state.app_mode = "Map View"
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None
    if 'custom_incidents' not in st.session_state:
        st.session_state.custom_incidents = []
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'hf_api_key' not in st.session_state:
        st.session_state.hf_api_key = ""

    st.set_page_config(page_title="Flooding Prediction & Coordination", layout="wide")

    # API Settings in Sidebar
    with st.sidebar:
        st.title("Settings")
        st.session_state.hf_api_key = st.text_input(
            "HuggingFace API Key",
            value=st.session_state.hf_api_key,
            type="password",
            help="Get your key at https://huggingface.co/settings/tokens"
        )
        if not st.session_state.hf_api_key:
            st.warning("Please enter your API Key to use the Chatbot.")

    render_top_bar()

    current_mode = st.session_state.app_mode

    if current_mode == "Map View":
        st.header("Real-Time Incident Map")
        st.write(
            "This map displays the primary operational view, showing regional incident density and zones. Orange markers indicate user-submitted resource needs.")

        map_object = create_folium_map()
        folium_static(map_object, width=1000, height=600)

    elif current_mode == "Chatbot":
        st.header("AI Assistance Chatbot")
        st.write("The AI Chatbot interface provides rapid incident reporting and instruction assistance.")
        
        # Display chat messages from history on app rerun
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # React to user input
        if prompt := st.chat_input("How can I help you today?"):
            # Display user message in chat message container
            st.chat_message("user").markdown(prompt)
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})

            # Get agent response
            agent = DisasterAgent(api_token=st.session_state.hf_api_key)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    # The get_response method in chatbot.py adds the user_input to messages itself
                    # so we pass the previous history.
                    response = agent.get_response(prompt, history=st.session_state.messages[:-1])
                    st.markdown(response)
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})

    elif current_mode == "Prediction":
        st.header("Flooding Prediction Models")
        st.write("View probability models, time-series forecasts, and risk assessments for flooding events.")

    elif current_mode == "Volunteering":
        render_volunteering_view()

    elif current_mode == "Groups":
        st.header("Groups Management")
        st.write("Join or create groups to coordinate volunteering efforts.")

    elif current_mode == "Login":
        st.header("User Login")
        user_input = st.text_input("Username")
        pass_input = st.text_input("Password", type="password")
        if st.button("Submit Login"):
            if user_input and pass_input:
                st.session_state.logged_in = True
                st.session_state.username = user_input
                st.session_state.app_mode = "Map View"
                st.success(f"Welcome, {user_input}!")
                st.rerun()
            else:
                st.error("Please enter credentials.")

    elif current_mode == "Profile":
        st.header(f"User Profile: {st.session_state.username}")
        st.write("This is a placeholder for user profile information.")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.app_mode = "Map View"
            st.rerun()

if __name__ == "__main__":
    main()