import json
import datetime
import os
import streamlit as st
from app.common import load_scan_cache, save_scan_cache, SCAN_CACHE_FILE

def post_disaster_alert(location: str, summary: str, severity: int, disaster_type: str = "General"):
    """
    Posts a disaster alert to the public Bounty Board.
    
    Args:
        location (str): The location of the disaster (e.g., "Miami, FL").
        summary (str): A brief summary of the situation.
        severity (int): Severity level (1-10).
        disaster_type (str): Type of disaster (e.g. "Flood", "Hurricane", "Wildfire").
        
    Returns:
        str: Result message.
    """
    try:
        # Load existing cache
        cache = load_scan_cache()
        scan_results = cache.get("scan_results", [])
        
        # Create new entry
        new_alert = {
            "location": location,
            "text": summary,  # Using 'text' to match scanner format
            "summary": summary,
            "severity": severity,
            "disaster_type": disaster_type,
            "source": "Chatbot",
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Append and save
        scan_results.insert(0, new_alert) # Add to top
        save_scan_cache(scan_results, cache.get("last_scan_time"))
        
        # Try to update session state if available (for immediate UI update)
        try:
            if "scan_results" in st.session_state:
                st.session_state.scan_results.insert(0, new_alert)
        except:
            pass
            
        return f"Successfully posted alert for {location} to the Bounty Board."
    except Exception as e:
        return f"Failed to post alert: {str(e)}"
