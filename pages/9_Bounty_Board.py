import streamlit as st
from st_supabase_connection import SupabaseConnection
import app.initialize as session_init
from app.common import load_scan_cache, save_scan_cache
import datetime
import uuid
import json
import os
import csv
from geopy import distance
from app.chatbot.bounty_generator import DisasterBountyGenerator

st.set_page_config(page_title="Flooding Coordination - Bounty Board", layout="wide")
session_init.init_session_state()

st.title("Disaster Bounty Board")
st.markdown("Connect with real-time needs and system-generated alerts.")

# Initialize Supabase Connection
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception as e:
    st.error(f"Failed to connect to Supabase: {e}")
    conn = None

# Helper Functions

@st.cache_data
def load_fips_coords():
    fips_to_coords = {}
    csv_path = "data/gis/us_county_latlng_with_state.csv"
    if os.path.exists(csv_path):
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                fips_to_coords[row['fips_code']] = (float(row['lat']), float(row['lng']))
    return fips_to_coords

fips_to_coords = load_fips_coords()

def load_bounties():
    """Fetch help requests from Supabase."""
    if not conn:
        return []
    try:
        user_id = st.session_state.get("user_id")
        if user_id:
            response = conn.table("help_requests").select("*").neq("poster_id", user_id).order("created_at", desc=True).execute()
            # Filter out bounties where user is already a volunteer or applicant
            filtered_data = [
                b for b in response.data 
                if st.session_state.get("user_id") not in (b.get('current_volunteers') or []) 
                and st.session_state.get("user_id") not in (b.get('applicants') or [])
            ]
            return filtered_data
        else:
            response = conn.table("help_requests").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching bounties: {e}")
        return []

def post_bounty(content, lat, lon, disaster_type, urgency):
    """Post a new help request to Supabase."""
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("You must be logged in to post.")
        return False
    
    if not conn:
        st.error("Database connection unavailable.")
        return False

    try:
        conn.table("help_requests").insert({
            "poster_id": user_id,
            "content": content,
            "lat": lat,
            "long": lon,
            "disaster_type": disaster_type,
            "urgency": urgency,
        }).execute()
        return True
    except Exception as e:
        st.error(f"Failed to post bounty: {e}")
        return False


def apply_for_bounty(bounty_id, current_applicants):
    """Add current user to applicants list."""
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.warning("Please log in to apply.")
        return False
    
    if not conn:
        return False
    
    # Handle None case
    if current_applicants is None:
        current_applicants = []
        
    if user_id in current_applicants:
        st.info("You already applied!")
        return False

    updated_applicants = current_applicants + [user_id]
    
    try:
        conn.table("help_requests").update({"applicants": updated_applicants}).eq("id", bounty_id).execute()
        return True
    except Exception as e:
        st.error(f"Failed to apply: {e}")
        return False

@st.dialog("Bounty Details")
def show_bounty_details(b):
    user_id = st.session_state.get("user_id")
    
    st.subheader(f"{b['disaster_type']} - Urgency: {b['urgency']}/10")
    st.write(b['content'])
    st.markdown(f"**Location:** {b['lat']}, {b['long']}")
    st.caption(f"Posted: {b['created_at']}")
    
    volunteers = b.get('current_volunteers', []) or []
    if volunteers:
        st.write(f"**Active Volunteers:** {len(volunteers)}")
    
    st.divider()
    
    col1, col2 = st.columns(2)

    is_creator = user_id == b['poster_id']
    
    with col1:
        if not is_creator and st.button("📩 DM Creator", key=f"dm_{b['id']}"):
            st.switch_page("pages/5_Groups.py", query_params={"dm_id": b['poster_id']})
            
    with col2:
        applicants = b.get('applicants', []) or []
        is_applicant = user_id in applicants
        is_volunteer = user_id in volunteers
        
        if is_creator:
            st.info("You posted this bounty. Go to Profile to manage.")
        elif is_volunteer:
            st.success("You are volunteering!")
        elif is_applicant:
            st.info("Application Pending")
        else:
            if user_id:
                if st.button("Apply to Help", key=f"apply_{b['id']}", use_container_width=True):
                    if apply_for_bounty(b['id'], applicants):
                        st.success("Applied successfully!")
                        st.rerun()
            else:
                if st.button("Log in to Apply", key=f"login_apply_{b['id']}", use_container_width=True):
                    st.switch_page("pages/1_Login.py")

@st.cache_data
def get_county_name(fips_code):
    import csv
    if not fips_code: return "Unknown"
    try:
        with open("data/gis/us_county_latlng_with_state.csv", mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['fips_code'].strip() == str(fips_code):
                    return f"{row['name']} County, {row['state']}"
    except:
        pass
    return "Unknown"

col_community, col_alerts = st.columns([1, 1])

# Fetch data early to ensure fast rendering
bounties = load_bounties()

# Get user coords for filtering
user_id = st.session_state.get("user_id")
user_coords = None
if user_id and conn:
    try:
        profile_response = conn.table("profiles").select("fips_code").eq("id", user_id).execute()
        if profile_response.data:
            user_fips = profile_response.data[0].get('fips_code')
            user_coords = fips_to_coords.get(str(user_fips))
    except:
        pass

# 1. Community Bounties (Supabase) - Show these first on the left
with col_community:
    row_header = st.columns([3, 1])
    row_header[0].subheader(":material/sos: Community Bounties")
    
    # "Post Request" Button
    with row_header[1]:
        if st.button("Post", icon=":material/add:"):
            @st.dialog("Post Help Request")
            def item_dialog():
                with st.form("new_bounty_form"):
                    b_content = st.text_area("What do you need help with?")
                    c1, c2 = st.columns(2)
                    b_lat = c1.number_input("Latitude", value=0.0, format="%.4f")
                    b_lon = c2.number_input("Longitude", value=0.0, format="%.4f")
                    b_type = st.selectbox("Type", ["Flood", "Fire", "Medical", "Supplies", "Rescue", "Other"])
                    b_urgency = st.slider("Urgency (1-10)", 1, 10, 5)
                    
                    if st.form_submit_button("Submit Request"):
                        if post_bounty(b_content, b_lat, b_lon, b_type, b_urgency):
                            st.success("Posted!")
                            st.rerun()
            
            item_dialog()

    st.caption("Real-time requests from users.")
    
    @st.fragment
    def render_community_bounties():
        # Filtering UI
        c_filt1, c_filt2 = st.columns(2)
        with c_filt1:
            use_search = st.toggle("Enable Search", value=True)
        with c_filt2:
            use_radius = st.toggle("Enable Distance Filter", value=False) if user_coords else False
        
        search_query = ""
        if use_search:
            search_query = st.text_input("🔍 Search Bounties", placeholder="Search by content or type...", label_visibility="collapsed")
        
        radius_km = None
        if use_radius and user_coords:
            radius_km = st.slider("📍 Search Radius (km)", min_value=1, max_value=5000, value=1000)
        
        # Apply Filtering
        filtered_bounties = []
        for b in bounties:
            # Search filter
            if use_search and search_query:
                query = search_query.lower()
                content = b.get('content', '').lower()
                d_type = b.get('disaster_type', '').lower()
                if query not in content and query not in d_type:
                    continue
                    
            # Distance filter
            if use_radius and radius_km and user_coords:
                b_coords = (b.get('lat'), b.get('long'))
                if b_coords[0] is not None and b_coords[1] is not None:
                    try:
                        dist = distance.distance(user_coords, b_coords).km
                        if dist > radius_km:
                            continue
                        b['distance_val'] = dist
                    except:
                        pass
            elif not use_radius and user_coords:
                b_coords = (b.get('lat'), b.get('long'))
                if b_coords[0] is not None and b_coords[1] is not None:
                    try:
                        dist = distance.distance(user_coords, b_coords).km
                        b['distance_val'] = dist
                    except:
                        pass
            
            filtered_bounties.append(b)

        if not filtered_bounties:
            st.info("No active help requests.")
        else:
            for b in filtered_bounties:
                b_id = b['id']
                volunteers = b.get('current_volunteers', []) or []
                applicants = b.get('applicants', []) or []
                
                card_color = "red" if b['urgency'] > 7 else "orange" if b['urgency'] > 4 else "green"
                
                with st.container(border=True):
                    c_main, c_act = st.columns([6, 2])
                    with c_main:
                        st.markdown(f"**:{card_color}[{b['disaster_type'].upper()}]** • Urgency: {b['urgency']}/10")
                        st.write(b['content'][:100] + ("..." if len(b['content']) > 100 else ""))
                        dist_str = f" • {b['distance_val']:.1f}km away" if 'distance_val' in b else ""
                        st.caption(f"📍 {b['lat']}, {b['long']}{dist_str} • {len(volunteers)} volunteers")
                    
                    with c_act:
                        if st.button("View", key=f"view_{b_id}"):
                            show_bounty_details(b)
    
    render_community_bounties()

# 2. AI System Bounties - Show these on the right
with col_alerts:
    row_ai = st.columns([3, 1])
    row_ai[0].subheader("🤖 AI System Bounties")
    
    user_id = st.session_state.get("user_id")
    
    if user_id:
        with row_ai[1]:
            if st.button("", icon=":material/refresh:", help="Force Regenerate AI Bounties", key="refresh_ai_bounties"):
                if "force_refresh_ai" not in st.session_state:
                    st.session_state.force_refresh_ai = False
                st.session_state.force_refresh_ai = True

    st.caption("Intelligently generated based on your location and profile.")
    
    @st.fragment
    def render_ai_bounties():
        user_id = st.session_state.get("user_id")
        
        if not user_id:
            st.info("Log in to see personalized AI bounties.")
        else:
            force_refresh = st.session_state.get("force_refresh_ai", False)
            if force_refresh:
                st.session_state.force_refresh_ai = False
            
            try:
                profile = conn.table("profiles").select("fips_code, bio").eq("id", user_id).execute()
                if profile.data:
                    fips = profile.data[0].get('fips_code')
                    bio = profile.data[0].get('bio', '')
                    county_name = get_county_name(fips)
                    
                    with st.spinner("AI is monitoring sources..."):
                        generator = DisasterBountyGenerator(api_token=st.session_state.get("hf_api_key"))
                        system_bounties = generator.get_cached_bounties(user_id, fips, bio, county_name, force=force_refresh)
                    
                    if not system_bounties:
                        st.info("No AI-suggested bounties for your area right now.")
                    else:
                        for i, sb in enumerate(system_bounties):
                            with st.expander(f"System: {sb.get('title', 'Bounty')}", expanded=i==0):
                                st.write(sb.get('description', ''))
                                st.write(f"**Location:** {sb.get('location', 'Unknown')}")
                                st.progress(sb.get('urgency', 5) / 10, text=f"Urgency: {sb.get('urgency', 5)}/10")
                                
                                contact = sb.get('contact_info', {})
                                if contact:
                                    st.markdown("---")
                                    if contact.get('phone'):
                                        st.markdown(f"📞 **Phone:** [{contact['phone']}](tel:{contact['phone']})")
                                    if contact.get('email'):
                                        st.markdown(f"📧 **Email:** [{contact['email']}](mailto:{contact['email']})")
                                    if contact.get('link'):
                                        st.link_button("🌐 More Info", contact['link'], use_container_width=True)
                else:
                    st.warning("Profile not found. Please set up your profile.")
            except Exception as e:
                st.error(f"Error loading AI bounties: {e}")
    
    render_ai_bounties()


