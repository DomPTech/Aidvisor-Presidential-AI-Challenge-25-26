import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import uuid
import datetime
import json
import os
import h3
import requests

FLOODING_ICONS = {
    "💧 Water/Need": "tint",
    "🏠 Structure Damage": "house",
    "⚠️ Warning": "exclamation-triangle",
    "🚑 Medical Need": "medkit",
    "🚧 Road Block": "road",
    "📍 Default Pin": "map-pin",
}

DB_FILE = "data.json"
SCAN_CACHE_FILE = "scan_cache.json"

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

                if "admin" not in data["users"]:
                    data["users"]["admin"] = {"pw": "hello", "points": 1000, "history": []}

                return data
        except:
            pass
    return {"users": {"admin": {"pw": "hello", "points": 1000, "history": []}}, "group_messages": [], "dm_history": [],
            "notifications": [], "locations": []}

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

def load_scan_cache():
    if os.path.exists(SCAN_CACHE_FILE):
        try:
            with open(SCAN_CACHE_FILE, "r") as f:
                cache = json.load(f)
                if "scan_results" in cache and "last_scan_time" in cache:
                    cache["last_scan_time"] = datetime.datetime.fromisoformat(cache["last_scan_time"])
                    return cache
        except:
            pass
    return {"scan_results": [], "last_scan_time": None}

def save_scan_cache(scan_results, last_scan_time):
    cache = {
        "scan_results": scan_results,
        "last_scan_time": last_scan_time.isoformat() if last_scan_time else None
    }
    with open(SCAN_CACHE_FILE, "w") as f:
        json.dump(cache, f)

@st.cache_data(ttl=3600)
def fetch_nasa_eonet_events_for_map():
    """
    Fetch open events from NASA EONET for the heatmap.
    """
    try:
        url = "https://eonet.gsfc.nasa.gov/api/v3/events"
        params = {"status": "open", "limit": 50}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        nasa_events = []
        # Severity mapping based on EONET categories
        SEVERITY_MAPPING = {
            "Severe Storms": 10,
            "Wildfires": 9,
            "Floods": 9,
            "Earthquakes": 10,
            "Volcanoes": 8,
            "Landslides": 7,
            "Temp Extremes": 6,
            "Sea and Lake Ice": 4,
            "Drought": 5,
        }
        
        for event in data.get("events", []):
            geometries = event.get("geometry", [])
            categories = event.get("categories", [])
            
            # Determine max severity based on categories
            severity = 5 # Default base
            for cat in categories:
                cat_title = cat.get("title")
                if cat_title in SEVERITY_MAPPING:
                    severity = max(severity, SEVERITY_MAPPING[cat_title])
            
            if geometries:
                latest_geo = geometries[0]
                coords = latest_geo.get("coordinates", [])
                if len(coords) >= 2:
                    nasa_events.append({
                        "lat": coords[1],
                        "lon": coords[0],
                        "severity": severity,
                        "location": event.get("title", "NASA Alert"),
                        "text": f"NASA EONET Alert: {event.get('title')}. Source: {event.get('sources', [{}])[0].get('url', 'N/A')}",
                        "source": "NASA EONET"
                    })
        return nasa_events
    except Exception as e:
        print(f"Error fetching NASA EONET for map: {e}")
        return []

def get_badge(username):
    data = load_data()
    user_info = data["users"].get(username, {})
    points = user_info.get("points", 0)
    if username == "admin": return "🛠️ Administrator"
    if points >= 100: return "🏆 Platinum Hero"
    if points >= 50: return "🥇 Gold Responder"
    if points >= 20: return "🥈 Silver Helper"
    if points >= 5: return "🥉 Bronze Volunteer"
    return "🌱 New Member"

def create_pydeck_map(scan_results=None, nasa_events=None):
    """
    Creates a Pydeck map with a heatmap layer and picker layer for incidents.
    """
    if scan_results is None:
        scan_results = st.session_state.get("scan_results", [])
    
    # Prepare Heatmap & Interaction Data
    heatmap_data = []
    for res in scan_results:
        entry = {
            "weight": res.get("severity", 0),
            "name": res.get("location", "Unknown Location"),
            "needs": res.get("text", "No detailed report available."),
            "source": res.get("source", "Scan Result")
        }
        if "cell" in res:
            try:
                lat, lon = h3.cell_to_latlng(res["cell"])
                entry.update({"lat": lat, "lon": lon})
                heatmap_data.append(entry)
            except:
                pass
        elif "lat" in res and "lon" in res:
            entry.update({"lat": res["lat"], "lon": res["lon"]})
            heatmap_data.append(entry)
    
    # Include NASA EONET Events
    if nasa_events is None:
        nasa_events = st.session_state.get("nasa_events", [])
        
    for event in nasa_events:
        heatmap_data.append({
            "lat": event["lat"],
            "lon": event["lon"],
            "weight": event["severity"],
            "name": event['location'],
            "needs": event["text"],
            "source": event.get("source", "NASA EONET")
        })
    
    # Prepare Incident Data
    data = load_data()
    incident_data = []
    for incident in data.get("locations", []):
        incident_data.append({
            "lat": incident["Latitude"],
            "lon": incident["Longitude"],
            "name": incident["Title"],
            "needs": incident["Needs"],
            "source": "Incident Report",
            "weight": 7  # Default severity for user incidents
        })
    
    # Define Layers
    layers = []
    if heatmap_data:
        df_heatmap = pd.DataFrame(heatmap_data)
        
        # Visual Heatmap Layer (for gradient effect)
        layers.append(pdk.Layer(
            "HeatmapLayer",
            data=df_heatmap,
            get_position=["lon", "lat"],
            get_weight="weight",
            radius_pixels=50,
            intensity=1,
            threshold=0.05,
            pickable=False,
        ))
        
        # Invisible ScatterplotLayer for tooltips (preserves individual data)
        layers.append(pdk.Layer(
            "ScatterplotLayer",
            data=df_heatmap,
            get_position=["lon", "lat"],
            get_radius=100000,
            get_fill_color=[255, 0, 0, 0],  # Fully transparent
            pickable=True,
            auto_highlight=True,
        ))
    
    if incident_data:
        df_incidents = pd.DataFrame(incident_data)
        
        # Visible incident markers
        layers.append(pdk.Layer(
            "ScatterplotLayer",
            data=df_incidents,
            get_position=["lon", "lat"],
            get_radius=50000,
            get_fill_color=[255, 165, 0, 200],  # Orange
            pickable=True,
            auto_highlight=True,
        ))
    
    # View State
    view_state = pdk.ViewState(
        latitude=39.8283,
        longitude=-98.5795,
        min_zoom=1,
        max_zoom=4,
        zoom=2,
        pitch=30
    )
    
    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style=None,
        tooltip={
            "html": "<div><b>{source}</b><br>Severity: {weight}<br>Location: {name}<br>Details: {needs}</div>",
            "style": {
                "max-width": "350px",
                "max-height": "300px",
                "overflow-y": "auto",
                "word-wrap": "break-word",
                "white-space": "normal",
                "font-size": "12px",
                "padding": "10px"
            }
        }
    )