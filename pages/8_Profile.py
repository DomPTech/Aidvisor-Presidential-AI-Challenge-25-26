import streamlit as st
from app.common import get_badge
from st_supabase_connection import SupabaseConnection
import csv

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

fips_to_county = get_county_lookup()
fips_list = list(fips_to_county.keys())

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
    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("First Name", value=first_name_default)
    with col2:
        last_name = st.text_input("Last Name", value=last_name_default)
        
    location = st.selectbox(
        "County",
        options=fips_list,
        format_func=lambda x: fips_to_county.get(x, "Select a County"),
        index=default_idx
    )
    bio = st.text_area("Bio", value=bio_default)
    submit_button = st.form_submit_button("Update Profile")
    
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
st.subheader("Settings")
with st.expander("🔐 Change Password"):
    new_pw = st.text_input("New Password", type="password", key="new_pw")
    confirm_pw = st.text_input("Confirm New Password", type="password", key="confirm_pw")
    if st.button("Update Password"):
        if new_pw and new_pw == confirm_pw:
            try:
                response = conn.auth.update_user({"password": new_pw})
                st.success("Password updated successfully!")
            except Exception as e:
                st.error(f"Error updating password: {str(e)}")
        else:
            st.error("Passwords do not match or field is empty.")

if st.button("🚪 Sign Out"):
    try:
        conn.auth.sign_out()
    except:
        pass
    st.session_state.logged_in = False
    st.session_state.username = None
    st.switch_page("pages/1_Login.py")