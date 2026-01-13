import streamlit as st
import datetime
import uuid
from app.coordination.volunteering import get_recommendations
from app.common import load_data, save_data, create_pydeck_map, FLOODING_ICONS

st.set_page_config(page_title="Flooding Coordination - Volunteering", layout="wide")

with st.sidebar:
    st.session_state.hf_api_key = st.text_input("HuggingFace API Key", value=st.session_state.hf_api_key,
                                                type="password")

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
    target_loc_name = ""
    target_user = None
    target_needs = "Unspecified"

    with col2:
        st.subheader("📍 Nearby Requests")
        st.pydeck_chart(create_pydeck_map())
        st.caption("Note: Interactive selection is currently limited in Pydeck view.")

    if "vol_selected_loc" in st.session_state:
        target_loc_name = st.session_state.vol_selected_loc
        target_user = st.session_state.vol_selected_user
        target_needs = st.session_state.get("vol_selected_needs", "Unspecified")

    with col1:
        st.subheader("📋 Your Information")
        with st.form("volunteer_info_form"):
            location = st.text_input("Location / Request", value=target_loc_name, placeholder="e.g., Nashville, TN")
            comments = st.text_area("Comments / What you are bringing")
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

                    if target_user:
                        data["notifications"].append({
                            "from": st.session_state.username,
                            "to": target_user,
                            "message": f"{st.session_state.username} volunteered for your request '{location}'! Comment: {comments}",
                            "read": False,
                            "timestamp": str(datetime.datetime.now())
                        })

                    data["notifications"].append({
                        "from": "System",
                        "to": st.session_state.username,
                        "message": f"Reminder: You volunteered for {location}. They need: '{target_needs}'. You offered: '{comments}'.",
                        "read": False,
                        "timestamp": str(datetime.datetime.now())
                    })

                    save_data(data)
                    st.success("Successfully volunteered!")

                    if target_user:
                        st.session_state.dm_recipient_target = target_user
                        st.session_state.show_dm_button = True
                    st.rerun()

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
        st.subheader("📍 Help Location")
        st.pydeck_chart(create_pydeck_map())
        st.caption("Note: Location selection currently disabled in Pydeck view. Use Prediction tab for new incident scanning.")

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