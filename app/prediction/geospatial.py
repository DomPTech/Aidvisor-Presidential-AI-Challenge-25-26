import h3
import json
import math
import streamlit as st
import geopandas as gpd
from shapely.geometry import Point, Polygon

_gis_cache = {}

def get_h3_cell(lat, lon, resolution=6):
    """
    Returns the H3 cell index for a given lat/lon and resolution.
    """
    return h3.latlng_to_cell(lat, lon, resolution)

@st.cache_resource
def get_gis_data():
    """
    Loads and caches GIS shapefiles into memory.
    """
    global _gis_cache
    if _gis_cache:
        return _gis_cache

    try:
        # Load Census shapefiles from organized data directory
        _gis_cache["states"] = gpd.read_file("data/gis/states/states.shp") if not _gis_cache.get("states") else _gis_cache["states"]
        _gis_cache["counties"] = gpd.read_file("data/gis/counties/counties.shp") if not _gis_cache.get("counties") else _gis_cache["counties"]
        _gis_cache["cities"] = gpd.read_file("data/gis/cities/cities.shp") if not _gis_cache.get("cities") else _gis_cache["cities"]
        
        # Ensure CRS is consistent (EPSG:4326 for lat/lon)
        for key in ["states", "counties", "cities"]:
            if not _gis_cache[key].empty and _gis_cache[key].crs != "EPSG:4326":
                _gis_cache[key] = _gis_cache[key].to_crs("EPSG:4326")
    except Exception as e:
        st.error(f"Error loading GIS data: {e}")
        # Fallback to empty GDFs to prevent crashes
        if "states" not in _gis_cache: _gis_cache["states"] = gpd.GeoDataFrame(columns=['geometry', 'NAME', 'STUSPS'])
        if "counties" not in _gis_cache: _gis_cache["counties"] = gpd.GeoDataFrame(columns=['geometry', 'NAME'])
        if "cities" not in _gis_cache: _gis_cache["cities"] = gpd.GeoDataFrame(columns=['geometry', 'NAME'])

    return _gis_cache

@st.cache_data
def get_h3_location_bundles(h3_indexes):
    """
    Takes an array of H3 cell indexes and returns an array of location bundles.
    """
    gis_data = get_gis_data()
    states_gdf = gis_data["states"]
    counties_gdf = gis_data["counties"]
    cities_gdf = gis_data["cities"]
    
    # State to Region Mapping (Standard US Regions)
    state_to_region = {
        'AL': 'Southeast', 'AK': 'West', 'AZ': 'Southwest', 'AR': 'Southeast', 'CA': 'West',
        'CO': 'West', 'CT': 'Northeast', 'DE': 'Northeast', 'FL': 'Southeast', 'GA': 'Southeast',
        'HI': 'West', 'ID': 'West', 'IL': 'Midwest', 'IN': 'Midwest', 'IA': 'Midwest',
        'KS': 'Midwest', 'KY': 'Southeast', 'LA': 'Southeast', 'ME': 'Northeast', 'MD': 'Northeast',
        'MA': 'Northeast', 'MI': 'Midwest', 'MN': 'Midwest', 'MS': 'Southeast', 'MO': 'Midwest',
        'MT': 'West', 'NE': 'Midwest', 'NV': 'West', 'NH': 'Northeast', 'NJ': 'Northeast',
        'NM': 'Southwest', 'NY': 'Northeast', 'NC': 'Southeast', 'ND': 'Midwest', 'OH': 'Midwest',
        'OK': 'Southwest', 'OR': 'West', 'PA': 'Northeast', 'RI': 'Northeast', 'SC': 'Southeast',
        'SD': 'Midwest', 'TN': 'Southeast', 'TX': 'Southwest', 'UT': 'West', 'VT': 'Northeast',
        'VA': 'Southeast', 'WA': 'West', 'WV': 'Southeast', 'WI': 'Midwest', 'WY': 'West',
        'DC': 'Northeast', 'PR': 'Territory', 'GU': 'Territory', 'VI': 'Territory', 'AS': 'Territory', 'MP': 'Territory'
    }
    
    bundles = []
    
    for h3_index in h3_indexes:
        # Get boundary of H3 cell for intersection
        boundary = h3.cell_to_boundary(h3_index)
        poly = Polygon([(lon, lat) for lat, lon in boundary])
        
        # State Lookup (Centroid based for simplicity/speed of primary state)
        cell_lat, cell_lon = h3.cell_to_latlng(h3_index)
        centroid_point = Point(cell_lon, cell_lat)
        
        state_name = "Unknown"
        region = "Unknown"
        
        if not states_gdf.empty:
            intersecting_states = states_gdf[states_gdf.intersects(centroid_point)]
            if not intersecting_states.empty:
                state_row = intersecting_states.iloc[0]
                state_name = state_row.get('NAME', 'Unknown')
                state_code = state_row.get('STUSPS', '')
                region = state_to_region.get(state_code, 'Unknown')
        
        # Counties Lookup (Area intersection)
        counties = []
        if not counties_gdf.empty:
            intersecting_counties = counties_gdf[counties_gdf.intersects(poly)]
            counties = intersecting_counties['NAME'].tolist() if 'NAME' in intersecting_counties.columns else []
            
        # Cities Lookup (Area intersection)
        cities = []
        if not cities_gdf.empty:
            intersecting_cities = cities_gdf[cities_gdf.intersects(poly)]
            cities = intersecting_cities['NAME20'].tolist() if 'NAME20' in intersecting_cities.columns else []
            
        bundles.append({
            "h3": h3_index,
            "state": state_name,
            "counties": counties,
            "cities": cities,
            "region": region
        })
        
    return bundles

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
        
        # Check for direct cell data first
        direct_match = next((res for res in scan_results if res.get('cell') == cell), None)
        
        # Hierarchical Check: If no direct match, check if any parent (up to res 1) matches
        if not direct_match:
            for r in range(resolution - 1, 0, -1):
                parent = h3.cell_to_parent(cell, r)
                direct_match = next((res for res in scan_results if res.get('cell') == parent), None)
                if direct_match:
                    break
        
        if direct_match:
            predicted_severity = direct_match['severity']
            location_name = direct_match.get('location', 'Unknown')
            disaster_text = direct_match.get('text', 'No report')
        else:
            # IDW Calculation
            numerator = 0
            denominator = 0
            # Higher power (3 or 4) for sharper decay, making localized peaks more prominent
            power = 3
            
            found_exact = False
            # Filter results that have lat/lon (point data)
            point_results = [res for res in scan_results if 'lat' in res and 'lon' in res]
            
            for res in point_results:
                dist = get_distance(cell_lat, cell_lon, res['lat'], res['lon'])
                if dist < 0.5: # Sharper threshold for exact match
                    severity = res['severity']
                    found_exact = True
                    exact_res = res
                    break
                
                w = 1.0 / (dist ** power)
                numerator += w * res['severity']
                denominator += w
                
            if found_exact:
                predicted_severity = severity
                location_name = exact_res.get('location', 'Unknown')
                disaster_text = exact_res.get('text', 'No report')
            elif denominator > 0:
                predicted_severity = numerator / denominator
                # Find nearest incident for tooltip info
                nearest_inc = min(scan_results, key=lambda x: get_distance(cell_lat, cell_lon, x['lat'], x['lon']) if 'lat' in x else float('inf'))
                dist_to_nearest = get_distance(cell_lat, cell_lon, nearest_inc['lat'], nearest_inc['lon']) if 'lat' in nearest_inc else float('inf')
                
                location_name = nearest_inc.get('location', 'Unknown') if dist_to_nearest < 500 else "N/A"
                disaster_text = nearest_inc.get('text', 'No nearby reports') if dist_to_nearest < 500 else "No nearby reports"
            else:
                predicted_severity = 0
                location_name = "N/A"
                disaster_text = "No data"

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
