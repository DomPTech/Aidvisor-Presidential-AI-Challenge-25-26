import streamlit as st
from app.common import get_badge
from st_supabase_connection import SupabaseConnection
import csv
import app.initialize as session_init

conn = st.connection("supabase", type=SupabaseConnection)

st.set_page_config(page_title="Flooding Coordination - Profile", layout="wide")

@st.cache_data
def get_county_lookup():
    f_to_c = {}
    with open("data/gis/us_county_latlng_with_state.csv", mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            f_to_c[row['fips_code'].strip()] = f"{row['name']} County, {row['state']}"
    return f_to_c

@st.cache_data
def get_user_name(user_id):
    """Fetch user's name from profile by ID"""
    try:
        profile = conn.table("profiles").select("first_name, last_name").eq("id", user_id).execute()
        if profile.data:
            first = profile.data[0].get('first_name', '')
            last = profile.data[0].get('last_name', '')
            return f"{first} {last}".strip() or user_id[:8]  # Return truncated ID if no name
        return user_id[:8]
    except:
        return user_id[:8]

fips_to_county = get_county_lookup()
fips_list = list(fips_to_county.keys())

session_init.init_session_state()

with st.sidebar:
    st.session_state.hf_api_key = st.text_input("HuggingFace API Key", value=st.session_state.hf_api_key,
                                                type="password")

# Load user data from Supabase auth
try:
    user_response = conn.auth.get_user()
    if user_response:
        user = user_response.user
        user_email = user.email
        user_id = user.id
        user_info = {"points": 0, "history": []}  # Custom data not stored in auth; set defaults
        
        first_name_default = ''
        last_name_default = ''
        location_default = ''
        bio_default = ''

        # Fetch profile data
        profile_response = conn.table("profiles").select("*").eq("id", user_id).execute()
        if profile_response.data:
            first_name_default = profile_response.data[0].get('first_name', '')
            last_name_default = profile_response.data[0].get('last_name', '')
            location_default = profile_response.data[0].get('fips_code', 0)
            bio_default = profile_response.data[0].get('bio', '')
            
            try:
                default_idx = fips_list.index(str(location_default))
            except ValueError:
                default_idx = 0
    else:
        st.error("User not authenticated, please log in.")
        st.stop()
except Exception as e:
    st.error(f"Error retrieving user: {str(e)}")
    st.stop()

st.header(f"Profile: {user_email}")
st.subheader(f"Badge: {get_badge(user_email)}")
st.write(f"Total Points: {user_info.get('points', 0)}")

with st.form("update_profile_form"):
    st.markdown("**Personal Information**")
    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("First Name", value=first_name_default)
    with col2:
        last_name = st.text_input("Last Name", value=last_name_default)
    
    st.markdown("**Location & Bio**")
    location = st.selectbox(
        "County",
        options=fips_list,
        format_func=lambda x: fips_to_county.get(x, "Select a County"),
        index=default_idx
    )
    bio = st.text_area("Bio", value=bio_default, height=100)
    
    st.divider()
    
    col1, col2 = st.columns([1, 4])
    with col1:
        submit_button = st.form_submit_button("Save Profile", use_container_width=True)
    
if submit_button: 
    if user_id:
        # Data to update
        updates = {
            "first_name": first_name,
            "last_name": last_name,
            "bio": bio,
            "fips_code": int(location),
        }
        
        # Execute the update
        # .eq() ensures only the row matching the user's ID is updated
        # RLS must allow this operation
        try:
            response, count = conn.table("profiles").update(updates).eq("id", user_id).execute()
            st.success("Profile updated successfully!")
        except Exception as e:
            st.error(f"An error occurred: {e}")
            
    else:
        st.warning("Please enter a name and ensure user is logged in.")
        
st.divider()
st.subheader("Manage My Bounties")

@st.dialog("Edit Bounty")
def edit_bounty_dialog(bounty):
    """Dialog for editing a bounty"""
    with st.form("edit_bounty_form", clear_on_submit=True):
        st.markdown("**Bounty Details**")
        
        col1, col2 = st.columns(2)
        with col1:
            new_disaster_type = st.text_input("Disaster Type", value=bounty.get('disaster_type', ''))
        with col2:
            new_urgency = st.slider("Urgency Level", 1, 10, bounty.get('urgency', 5))
        
        new_content = st.text_area("Description", value=bounty.get('content', ''), height=120)
        
        st.markdown("**Location**")
        col1, col2 = st.columns(2)
        with col1:
            new_lat = st.number_input("Latitude", value=float(bounty.get('lat', 0)), format="%.4f")
        with col2:
            new_lon = st.number_input("Longitude", value=float(bounty.get('long', 0)), format="%.4f")
        
        st.divider()
        st.markdown("**Actions**")
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if st.form_submit_button("Save Changes", type="primary", use_container_width=True):
                try:
                    conn.table("help_requests").update({
                        "disaster_type": new_disaster_type,
                        "urgency": new_urgency,
                        "content": new_content,
                        "lat": new_lat,
                        "long": new_lon,
                    }).eq("id", bounty['id']).execute()
                    st.success("Bounty updated successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating bounty: {e}")
        
        with col2:
            if st.form_submit_button("Cancel", use_container_width=True):
                pass
        
        with col3:
            if st.form_submit_button("Delete", use_container_width=True):
                try:
                    conn.table("help_requests").delete().eq("id", bounty['id']).execute()
                    st.success("Bounty deleted!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting bounty: {e}")

# @st.dialog("Send Message")
# def send_dm_dialog(recipient_id, recipient_name):
#     """Dialog for sending a DM to an applicant/volunteer"""
#     st.write(f"Sending message to: **{recipient_name}**")
#     with st.form("send_dm_form", clear_on_submit=True):
#         message_content = st.text_area("Message", placeholder="Type your message here...")
        
#         if st.form_submit_button("Send Message"):
#             if message_content.strip():
#                 try:
#                     # Create a message record in the database
#                     conn.table("messages").insert({
#                         "sender_id": user_id,
#                         "recipient_id": recipient_id,
#                         "content": message_content,
#                         "created_at": "now()"
#                     }).execute()
#                     st.success("Message sent!")
#                 except Exception as e:
#                     st.error(f"Error sending message: {e}")
#             else:
#                 st.warning("Message cannot be empty.")

try:
    # Fetch requests posted by user
    my_bounties = conn.table("help_requests").select("*").eq("poster_id", user_id).execute()
    if not my_bounties.data:
        st.info("You haven't posted any help requests.")
    else:
        for b in my_bounties.data:
            with st.expander(f"**{b['disaster_type']}** • Posted {b['created_at'][:10]} • Urgency: {b.get('urgency', 5)}/10", expanded=True):
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.write(b['content'])
                with col2:
                    if st.button("Edit", icon=":material/settings:", key=f"edit_{b['id']}", use_container_width=True):
                        edit_bounty_dialog(b)
                
                applicants = b.get('applicants', []) or []
                current_vols = b.get('current_volunteers', []) or []
                
                st.caption(f"**{len(current_vols)}** volunteer(s) currently assigned")
                
                # Edit button - Primary action
                st.divider()
                col1, col2 = st.columns([1, 4])
                
                # Pending applicants section
                if applicants:
                    st.markdown("**Pending Applicants**")
                    for app_id in applicants:
                        applicant_name = get_user_name(app_id)
                        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                        with c1:
                            st.write(f"👤 {applicant_name}")
                        
                        with c2:
                            if st.button("Accept", key=f"acc_{b['id']}_{app_id}", use_container_width=True):
                                new_applicants = [x for x in applicants if x != app_id]
                                if app_id not in current_vols:
                                    new_volunteers = current_vols + [app_id]
                                else:
                                    new_volunteers = current_vols
                                
                                conn.table("help_requests").update({
                                    "applicants": new_applicants, 
                                    "current_volunteers": new_volunteers
                                }).eq("id", b['id']).execute()
                                st.rerun()
                        
                        with c3:
                            if st.button("Reject", key=f"rej_{b['id']}_{app_id}", use_container_width=True):
                                new_applicants = [x for x in applicants if x != app_id]
                                conn.table("help_requests").update({
                                    "applicants": new_applicants
                                }).eq("id", b['id']).execute()
                                st.rerun()
                        
                        with c4:
                            if st.button("Message", key=f"dm_{b['id']}_{app_id}", use_container_width=True):
                                st.switch_page("pages/5_Groups.py", query_params={"dm_id": app_id})
                else:
                    st.caption("No pending applicants.")
                
                # Current volunteers section
                if current_vols:
                    st.divider()
                    st.markdown("**Current Volunteers**")
                    for vol_id in current_vols:
                        volunteer_name = get_user_name(vol_id)
                        c1, c2, c3 = st.columns([3, 1, 1])
                        with c1:
                            st.write(f"👤 {volunteer_name}")
                        
                        with c2:
                            if st.button("Message", key=f"dm_vol_{b['id']}_{vol_id}", use_container_width=True):
                                st.switch_page("pages/5_Groups.py", query_params={"dm_id": vol_id})
                        
                        with c3:
                            if st.button("Remove", type="primary", key=f"kick_{b['id']}_{vol_id}", use_container_width=True):
                                @st.dialog("Confirm Removal")
                                def confirm_kick():
                                    st.write(f"Are you sure you want to remove **{volunteer_name}** from this bounty?")
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if st.button("Confirm", key=f"confirm_kick_{b['id']}_{vol_id}", use_container_width=True):
                                            new_volunteers = [x for x in current_vols if x != vol_id]
                                            conn.table("help_requests").update({
                                                "current_volunteers": new_volunteers
                                            }).eq("id", b['id']).execute()
                                            st.success(f"{volunteer_name} has been removed!")
                                            st.rerun()
                                    with col2:
                                        if st.button("Cancel", key=f"cancel_kick_{b['id']}_{vol_id}", use_container_width=True):
                                            st.info("Cancelled")
                                
                                confirm_kick()

except Exception as e:
    st.error(f"Error fetching bounties: {e}")

st.divider()
st.subheader("Settings")

# Password section
with st.expander("🔐 Change Password"):
    new_pw = st.text_input("New Password", type="password", key="new_pw")
    confirm_pw = st.text_input("Confirm Password", type="password", key="confirm_pw")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Update Password", key="update_pw", use_container_width=True):
            if new_pw and new_pw == confirm_pw:
                try:
                    response = conn.auth.update_user({"password": new_pw})
                    st.success("Password updated successfully!")
                except Exception as e:
                    st.error(f"Error updating password: {str(e)}")
            else:
                st.error("Passwords do not match or field is empty.")

# Sign out section
st.divider()
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    if st.button("Sign Out", key="signout", use_container_width=True):
        try:
            conn.auth.sign_out()
        except:
            pass
        st.session_state.logged_in = False
        st.session_state.username = None
        st.seession_state.user_id = None
        st.switch_page("pages/1_Login.py")