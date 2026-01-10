import streamlit as st
import re
import torch
from transformers import pipeline
from geopy.geocoders import Nominatim
import time
import ssl
import certifi
from geotext import GeoText

@st.cache_resource
def get_classifier():
    # Using a small, fast zero-shot classification model
    # This is locally instantiated and doesn't need an API key for classification
    return pipeline(
        "zero-shot-classification", 
        model="typeform/distilbert-base-uncased-mnli",
        device=0 if torch.cuda.is_available() else -1
    )

class DisasterScanner:
    def __init__(self):
        # Create a custom SSL context using certifi's certificates
        ctx = ssl.create_default_context(cafile=certifi.where())
        self.geolocator = Nominatim(
            user_agent="disaster_scanner_app",
            ssl_context=ctx,
            timeout=10 # Increased timeout
        )
        self.classifier = get_classifier()
        self.candidate_labels = ["Critical Disaster", "Moderate Warning", "General Information", "Not Disaster Related"]
        self.last_geocode_time = 0 # For rate limiting
        self.geocode_cache = {} # Cache to avoid duplicate API calls

    def _safe_geocode(self, query):
        """
        Safely geocodes a query with rate limiting and caching.
        """
        # Check Cache
        if query in self.geocode_cache:
            print(f"DEBUG: Using cached result for '{query}'")
            return self.geocode_cache[query]

        # Rate Limiting
        now = time.time()
        # Respect Nominatim's 1 req/s limit
        if now - self.last_geocode_time < 1.1:
            time.sleep(1.1 - (now - self.last_geocode_time))
            
        try:
            print(f"DEBUG: Attempting geocode for '{query}'...")
            location = self.geolocator.geocode(query)
            self.last_geocode_time = time.time()
            if location:
                print(f"DEBUG: Geocoding SUCCESS: {location.latitude}, {location.longitude}")
                coords = (location.latitude, location.longitude)
                self.geocode_cache[query] = coords # Update Cache
                return coords
            else:
                print(f"DEBUG: Geocoding FAILED for '{query}'")
                self.geocode_cache[query] = None # Cache failures too
        except Exception as e:
            print(f"DEBUG: Geocoding ERROR for '{query}': {e}")
            
        return None
        
    def get_severity_score(self, text):
        """
        Calculates a severity score (0-10) based on zero-shot classification results.
        """
        result = self.classifier(text, candidate_labels=self.candidate_labels)
        label_to_score = {
            "Critical Disaster": 10,
            "Moderate Warning": 5,
            "General Information": 2,
            "Not Disaster Related": 0
        }
        
        # Weighted average or top label score
        top_label = result['labels'][0]
        top_score = result['scores'][0]
        
        base_score = label_to_score[top_label]
        # Adjust score by confidence
        final_score = base_score * top_score
        
        return round(min(10, final_score), 1)

    def extract_location(self, text):
        """
        Attempts to extract geographic coordinates or a location name from text.
        Returns (lat, lon, label) or None.
        """
        # Look for explicit coordinates (Lat, Lon)
        coord_pattern = r"([-+]?\d*\.\d+),\s*([-+]?\d*\.\d+)"
        match = re.search(coord_pattern, text)
        if match:
            return float(match.group(1)), float(match.group(2)), f"{match.group(1)}, {match.group(2)}"

        # Use GeoText for city extraction
        places = GeoText(text).cities
        if places:
            coords = self._safe_geocode(places[0] + ", USA")
            if coords:
                return coords[0], coords[1], places[0]
        
        # Look for city, state patterns
        patterns = [
            r"in\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*,\s*[A-Z]{2})", # Nashville, TN
            r"near\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*,\s*[A-Z][a-z]+(?:\s[A-Z][a-z]+)*)", # Chicago, Illinois
            r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\s+(?:Disaster|Emergency|Warning|Alert)", # Tennessee Disaster
            r"across\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)", # across Tennessee
            r"state\s+of\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)" # state of Georgia
        ]
        
        # State abbreviations to help extraction
        states = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]
        
        # Check patterns
        for pattern in patterns:
            loc_match = re.search(pattern, text)
            if loc_match:
                location_string = loc_match.group(1)
                coords = self._safe_geocode(location_string + ", USA")
                if coords:
                    return coords[0], coords[1], location_string

        # Last ditch: look for any [City], [ST] or strictly [State Name]
        for st_abbr in states:
            if f" {st_abbr}" in text or f" {st_abbr}," in text:
                coords = self._safe_geocode(st_abbr + ", USA")
                if coords:
                    return coords[0], coords[1], st_abbr
                
        return None

    def scan_texts(self, texts):
        """
        Scans a list of texts and returns a list of results with severity and coordinates.
        """
        results = []
        for text in texts:
            severity = self.get_severity_score(text)
            loc_info = self.extract_location(text)
            
            if severity > 0 and loc_info:
                lat, lon, label = loc_info
                results.append({
                    "text": text[:150] + "...", # A bit more text for tooltips
                    "severity": severity,
                    "lat": lat,
                    "lon": lon,
                    "location": label
                })
        return results

if __name__ == "__main__":
    # Quick test
    scanner = DisasterScanner()
    test_texts = [
        "Major flooding reported in Nashville, TN (36.16, -86.78). Severe property damage.",
        "Beautiful sunny day in California.",
        "Flash flood warning for Cook County, IL near Chicago, IL."
    ]
    print(scanner.scan_texts(test_texts))
