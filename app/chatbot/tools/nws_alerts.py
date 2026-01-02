import requests

def get_nws_alerts(lat, lon):
    """
    Fetch active weather alerts from the National Weather Service (NWS) API for a given location.
    
    Args:
        lat (float): Latitude of the location.
        lon (float): Longitude of the location.
        
    Returns:
        str: A summary of active alerts or a "no alerts" message.
    """
    try:
        # User-Agent is required by NWS API
        headers = {
            "User-Agent": "FlashFloodPredictionApp/1.0 (contact: dominick@example.com)"
        }
        url = f"https://api.weather.gov/alerts/active?point={lat},{lon}"
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        features = data.get("features", [])
        
        if not features:
            return f"No active NWS alerts for the location ({lat}, {lon})."
            
        alert_summaries = []
        for feature in features:
            properties = feature.get("properties", {})
            event = properties.get("event", "Unknown Event")
            headline = properties.get("headline", "No Headline")
            severity = properties.get("severity", "Unknown Severity")
            area = properties.get("areaDesc", "Unknown Area")
            description = properties.get("description", "No Description")
            
            alert_summaries.append(
                f"Event: {event}\nSeverity: {severity}\nArea: {area}\nHeadline: {headline}"
            )
            
        return "\n\n---\n\n".join(alert_summaries)
        
    except Exception as e:
        return f"Error fetching NWS alerts: {str(e)}"

if __name__ == "__main__":
    # Test with a location (e.g., Nashville, TN)
    print(get_nws_alerts(36.1627, -86.7816))
