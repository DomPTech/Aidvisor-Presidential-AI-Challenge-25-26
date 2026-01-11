import sys
import os
from unittest.mock import MagicMock

# Mock streamlit before importing geospatial
sys.modules['streamlit'] = MagicMock()
import streamlit as st
st.cache_resource = lambda x: x
st.cache_data = lambda x: x

import h3
import geopandas as gpd
from shapely.geometry import Point, Polygon
from app.prediction.geospatial import get_h3_location_bundles

def test_h3_bundles_real_data():
    # H3 index for Nashville, TN roughly
    lat, lon = 36.1627, -86.7816
    h3_index = h3.latlng_to_cell(lat, lon, 6)
    
    print(f"Testing H3 index {h3_index} for Nashville, TN ({lat}, {lon})")
    
    bundles = get_h3_location_bundles([h3_index])
    bundle = bundles[0]
    
    print(f"Resulting Bundle: {bundle}")
    
    # Assertions based on expected data
    assert bundle['state'] == 'Tennessee', f"Expected Tennessee, got {bundle['state']}"
    assert 'Davidson' in bundle['counties'], f"Expected Davidson in counties, got {bundle['counties']}"
    # Nashville-Davidson Urbanized Area might be the name in NAME20
    assert any('Nashville' in c for c in bundle['cities']), f"Expected Nashville in cities, got {bundle['cities']}"
    assert bundle['region'] == 'Southeast', f"Expected Southeast region, got {bundle['region']}"

if __name__ == "__main__":
    try:
        test_h3_bundles_real_data()
        print("Success: H3 bundle lookup works with real shapefiles!")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
