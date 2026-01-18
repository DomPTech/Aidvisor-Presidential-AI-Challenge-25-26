import requests
import streamlit as st

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_nasa_eonet_events(limit=10, days=20, status='open'):
    """
    Fetch natural events from the NASA EONET v3 API.
    
    Args:
        limit (int): Maximum number of events to return.
        days (int): Number of days to look back.
        status (str): Status of the events ('open' or 'closed').
        
    Returns:
        str: A formatted summary of the latest events.
    """
    try:
        url = "https://eonet.gsfc.nasa.gov/api/v3/events"
        params = {
            "limit": limit,
            "days": days,
            "status": status
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        events = data.get("events", [])
        
        if not events:
            return {
                "summary": f"No {status} natural events found in the last {days} days.",
                "visuals": None
            }
            
        summaries = []
        map_data = []
        for event in events:
            title = event.get("title", "Unknown Event")
            categories = ", ".join([cat.get("title", "") for cat in event.get("categories", [])])
            source = ", ".join([src.get("id", "") for src in event.get("sources", [])])
            link = event.get("sources", [{}])[0].get("url", "No source link available")
            
            # Get latest geometry (location)
            geometries = event.get("geometry", [])
            location_info = "Location data unavailable"
            lat, lon = None, None
            if geometries:
                latest_geo = geometries[0]
                coords = latest_geo.get("coordinates", [])
                date = latest_geo.get("date", "Unknown Date")
                if len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
                    location_info = f"Coordinates: {lat}, {lon} (Lat/Lon) at {date}"
                    map_data.append({"lat": lat, "lon": lon, "name": title})
            
            summaries.append(
                f"Event: {title}\n"
                f"Categories: {categories}\n"
                f"Source: {source}\n"
                f"{location_info}\n"
                f"More info: {link}"
            )
            
        return {
            "summary": "\n\n---\n\n".join(summaries),
            "visuals": {
                "type": "map",
                "data": map_data
            } if map_data else None
        }
        
    except Exception as e:
        return {
            "summary": f"Error fetching NASA EONET events: {str(e)}",
            "visuals": None
        }

if __name__ == "__main__":
    # Test fetch
    print(get_nasa_eonet_events(limit=3))
