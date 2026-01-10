import h3
import json
import math
import streamlit as st

def get_h3_cell(lat, lon, resolution=6):
    """
    Returns the H3 cell index for a given lat/lon and resolution.
    """
    return h3.latlng_to_cell(lat, lon, resolution)

def get_distance(lat1, lon1, lat2, lon2):
    """
    Haversine distance between two points in km.
    """
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@st.cache_data
def fill_global_grid(scan_results_json, resolution=3):
    """
    Generates a dense grid of H3 cells and predicts severity for each using IDW.
    Note: scan_results matches a list of dicts, but we pass JSON string for caching.
    """
    scan_results = json.loads(scan_results_json)
    # Define US Bounding Box (Roughly)
    min_lat, max_lat = 24, 50
    min_lon, max_lon = -125, -66
    
    # Get all H3 cells in a polygon covering the US
    us_outline = [
        (min_lat, min_lon), (max_lat, min_lon), 
        (max_lat, max_lon), (min_lat, max_lon)
    ]
    # In H3 v4, we use LatLngPoly
    polygon = h3.LatLngPoly(us_outline)
    cells = h3.polygon_to_cells(polygon, resolution)
    
    # Apply IDW for each cell
    filled_data = []
    
    if not scan_results:
        # If no results, just return empty grid with 0 severity
        for cell in cells:
            filled_data.append({
                "cell": cell, 
                "severity": 0, 
                "count": 0,
                "location": "No data",
                "disaster": "None detected"
            })
        return filled_data

    for cell in cells:
        cell_lat, cell_lon = h3.cell_to_latlng(cell)
        
        # IDW Calculation
        numerator = 0
        denominator = 0
        power = 2
        
        found_exact = False
        for res in scan_results:
            dist = get_distance(cell_lat, cell_lon, res['lat'], res['lon'])
            if dist < 1.0: # Close enough to be exact
                severity = res['severity']
                found_exact = True
                break
            
            w = 1.0 / (dist ** power)
            numerator += w * res['severity']
            denominator += w
            
        if found_exact:
            predicted_severity = severity
        else:
            predicted_severity = numerator / denominator if denominator > 0 else 0
            
        # Find nearest incident for tooltip info
        nearest_inc = min(scan_results, key=lambda x: get_distance(cell_lat, cell_lon, x['lat'], x['lon']))
        dist_to_nearest = get_distance(cell_lat, cell_lon, nearest_inc['lat'], nearest_inc['lon'])
        
        # Only show metadata if within a reasonable range (e.g. 500km)
        location_name = nearest_inc.get('location', 'Unknown') if dist_to_nearest < 500 else "N/A"
        disaster_text = nearest_inc.get('text', 'No nearby reports') if dist_to_nearest < 500 else "No nearby reports"

        filled_data.append({
            "cell": cell,
            "severity": round(predicted_severity, 1),
            "count": 1,
            "location": location_name,
            "disaster": disaster_text
        })
        
    return filled_data

@st.cache_data
def get_h3_geojson(cell_data_json):
    """
    Converts aggregated H3 cell data to GeoJSON for Folium.
    """
    cell_data = json.loads(cell_data_json)
    features = []
    for data in cell_data:
        cell = data['cell']
        severity = data['severity']
        
        boundary = h3.cell_to_boundary(cell)
        polygon = [[lon, lat] for lat, lon in boundary]
        polygon.append(polygon[0])
        
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [polygon]
            },
            "properties": {
                "severity": severity,
                "fill_color": get_color_for_severity(severity),
                "location": data.get("location", "N/A"),
                "disaster": data.get("disaster", "None")
            }
        })
    return {
        "type": "FeatureCollection",
        "features": features
    }

def get_color_for_severity(severity):
    """
    Maps severity (0-10) to a smooth gradient.
    Uses a vibrant heatmap palette.
    """
    # Yellow -> Orange -> Red
    if severity >= 8: return "#800026" # Dark Red
    if severity >= 6: return "#E31A1C" # Red
    if severity >= 4: return "#FD8D3C" # Orange
    if severity >= 2: return "#FEB24C" # Light Orange
    return "#FFEDA0" # Pale Yellow

if __name__ == "__main__":
    # Test
    test_results = [
        {"lat": 36.16, "lon": -86.78, "severity": 8.5, "location": "Nashville, TN", "text": "Severe flooding in Nashville area."},
        {"lat": 34.05, "lon": -118.24, "severity": 4.0, "location": "Los Angeles, CA", "text": "Moderate storm warnings."}
    ]
    test_json = json.dumps(test_results)
    filled = fill_global_grid(test_json)
    geojson = get_h3_geojson(json.dumps(filled))
    # Print a feature to verify properties
    print(json.dumps(geojson['features'][0], indent=2))
