import streamlit as st
import os
import json
import requests
import pandas as pd
import numpy as np
from time import sleep

# ------------------------------
# CONFIG
# ------------------------------
LLM_MODEL = 'gemini-2.5-flash-preview-09-2025'

st.set_page_config(layout="wide", page_title="Flooding Prevention & Community Hub")

# ------------------------------
# HELPER: AI CONTENT GENERATOR
# ------------------------------
def llm_generate_content(prompt):
    """Calls Gemini API and returns (text, sources)."""

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return "Missing API Key. Please enter one.", []

    system_prompt = (
        "Provide consise actionable analysis based on the user's  query."
        "Use provided community data and real-time inputs to create your response."
        "You are a disaster relief operations analyst. Your main role is coordinate respone efforts to severe hurricanes, manage aid, "
        "and provide relief for firstly the most affected communities as well as focusing secondly on lower income and impoverished communities."
        "Format this in an easily understandable format, ideally as a list of necessary relief actions, locations, and corresponding explanations."
        "Be friendly in your response, as well as stressing the urgency of certain tasks and use great clarity in how they should be accomplished."
    )

    context_data = {
        "resources_count": len(st.session_state.resources),
        "volunteers_count": len(st.session_state.volunteers),
        "recent_resources": st.session_state.resources[-3:],
        "recent_volunteers": st.session_state.volunteers[-3:]
    }

    full_prompt = (
        f"Context from the Community Hub: {context_data}\n\n"
        f"User Query: {prompt}"
    )

    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "tools": [{"google_search": {}}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
    }

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{LLM_MODEL}:generateContent?key={api_key}"
    )

    try:
        response = requests.post(
            url,
            headers={'Content-Type': 'application/json'},
            data=json.dumps(payload),
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        candidate = data.get("candidates", [{}])[0]
        text = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")

        # Extract sources if provided
        sources = []
        metadata = candidate.get("groundingMetadata", {})
        if metadata and metadata.get("groundingAttributions"):
            for a in metadata["groundingAttributions"]:
                uri = a.get("web", {}).get("uri")
                title = a.get("web", {}).get("title")
                if uri and title:
                    sources.append({"uri": uri, "title": title})

        return text, sources

    except Exception as e:
        return f"Error contacting AI service: {e}", []


# ------------------------------
# HELPER: Add simulated geo data
# ------------------------------
def add_location_data(df):
    """Adds lat/lon offsets around a central coordinate."""
    if df.empty:
        return df

    center_lat = 35.9606
    center_lon = -83.9207

    df["lat"] = center_lat + np.random.uniform(-0.1, 0.1, len(df))
    df["lon"] = center_lon + np.random.uniform(-0.1, 0.1, len(df))
    return df


# ------------------------------
# SESSION STATE INITIALIZATION
# ------------------------------
if "resources" not in st.session_state:
    st.session_state.resources = [
        {'Item': 'Sandbags (500)', 'Location': 'Northside Warehouse', 'User': 'user-a7f4', 'Type': 'resource'},
        {'Item': 'Water bottles', 'Location': 'South End Community Center', 'User': 'user-b1e2', 'Type': 'resource'},
    ]

if "volunteers" not in st.session_state:
    st.session_state.volunteers = [
        {'Skills': 'Heavy Machinery/Cleanup', 'Availability': 'Weekend', 'User': 'user-c8g6', 'Type': 'volunteer'},
        {'Skills': 'First Aid Certified', 'Availability': 'Mon-Wed', 'User': 'user-d9h7', 'Type': 'volunteer'},
    ]

# Combine for map
combined_df = pd.DataFrame(st.session_state.resources + st.session_state.volunteers)
combined_df = add_location_data(combined_df)

# ------------------------------
# FIX: ADD VALID COLORS FOR MAP
# ------------------------------
color_map = {
    "resource": "#1f77b4",   # blue
    "volunteer": "#ff7f0e",  # orange
}

combined_df["color"] = combined_df["Type"].map(color_map)

# ------------------------------
# STREAMLIT UI
# ------------------------------

st.title("🌊 Flooding Prevention & Community Hub")

# --- API KEY ---
api_key_input = st.text_input(
    "Gemini API Key",
    type="password",
    help="Enter your Gemini API Key to enable the AI generator."
)

if api_key_input:
    os.environ["OPENAI_API_KEY"] = api_key_input
else:
    st.info("AI features will activate once you enter your API key.")

# ----------------------------------
# COLUMNS LAYOUT
# ----------------------------------
col1, col2 = st.columns([2, 1])

# ----------------------------------
# LEFT COLUMN — MAP + AI REPORT
# ----------------------------------
with col1:
    st.header("Resource & Volunteer Map")

    if not combined_df.empty:
        st.map(combined_df, latitude="lat", longitude="lon", color="color", zoom=10)
    else:
        st.info("No map data available.")

    st.subheader("AI Data & Report Generator")

    ai_query = st.text_area(
        "Ask for a Report",
        placeholder="Example: Summarize current resource needs and urgent actions."
    )

    if st.button("Generate Report"):
        if not api_key_input:
            st.error("Please enter your API key first.")
        elif not ai_query:
            st.warning("Please enter a query.")
        else:
            with st.spinner("Generating report..."):
                text, sources = llm_generate_content(ai_query)

            st.markdown("### AI Analysis")
            st.info(text)

            if sources:
                st.markdown("#### Sources")
                for src in sources:
                    st.markdown(f"🔗 [{src['title']}]({src['uri']})")


# ----------------------------------
# RIGHT COLUMN — FORMS + FEED
# ----------------------------------
with col2:
    # Resource form
    with st.container():
        st.markdown("## 🧰 Contribute Resources")

        with st.form("resource_form", clear_on_submit=True):
            item = st.text_input("Item Needed/Offered")
            location = st.text_input("Location")
            submitted = st.form_submit_button("Submit Resource")

            if submitted:
                if item and location:
                    st.session_state.resources.append({
                        'Item': item,
                        'Location': location,
                        'User': 'user-' + os.urandom(4).hex(),
                        'Type': 'resource'
                    })
                    st.success("Resource added!")
                    st.rerun()
                else:
                    st.error("Please fill out all fields.")

    # Volunteer form
    with st.container():
        st.markdown("## 🤝 Volunteer Sign-Up")

        with st.form("volunteer_form", clear_on_submit=True):
            skills = st.text_input("Skills/Equipment")
            availability = st.text_input("Availability")
            submitted = st.form_submit_button("Sign Up")

            if submitted:
                if skills and availability:
                    st.session_state.volunteers.append({
                        'Skills': skills,
                        'Availability': availability,
                        'User': 'user-' + os.urandom(4).hex(),
                        'Type': 'volunteer'
                    })
                    st.success("Volunteer added!")
                    st.rerun()
                else:
                    st.error("Please fill out all fields.")

    # Live Feed
    st.subheader("📡 Live Activity Feed")

    st.markdown("### Resources")
    if st.session_state.resources:
        df_res = pd.DataFrame(st.session_state.resources[::-1])
        st.dataframe(df_res[['Item', 'Location', 'User']], hide_index=True, use_container_width=True)
    else:
        st.info("No resources posted yet.")

    st.markdown("### Volunteers")
    if st.session_state.volunteers:
        df_vol = pd.DataFrame(st.session_state.volunteers[::-1])
        st.dataframe(df_vol[['Skills', 'Availability', 'User']], hide_index=True, use_container_width=True)
    else:
        st.info("No volunteers yet.")

# Footer
st.caption("*This demo uses session state to simulate real-time updates.*")
