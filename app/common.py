import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import uuid
import datetime
import json
import os
import h3

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

def create_pydeck_map(scan_results=None):
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
            "needs": res.get("text", "No detailed report available.")
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
    
    # Prepare Incident Data
    data = load_data()
    incident_data = []
    for incident in data.get("locations", []):
        incident_data.append({
            "lat": incident["Latitude"],
            "lon": incident["Longitude"],
            "name": incident["Title"],
            "needs": incident["Needs"]
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
            "html": "<div>Severity: {weight}<br>Location: {name}<br>Details: {needs}</div>",
            "style": {
                "max-width": "200px",
                "word-wrap": "break-word",
                "white-space": "normal"
            }
        }
    )