import streamlit as st
import re
import torch
from transformers import pipeline
from geopy.geocoders import Nominatim
import time
import ssl
import certifi
from geotext import GeoText
from app.chatbot.tools.ddg_search import get_news_search

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
        self.classifier = get_classifier()
        self.candidate_labels = ["Critical Disaster", "Moderate Warning", "General Information", "Not Disaster Related"]
        
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

    def scan_texts(self, texts):
        """
        Scans a list of texts and returns a list of results with severity and coordinates.
        """
        results = []
        for text in texts:
            severity = self.get_severity_score(text)
            
            if severity > 0:
                # We often don't have coordinates in the text, so we return severity and the text
                results.append({
                    "text": text[:200] + "...", 
                    "severity": severity,
                })
        return results

    def scan_bundle_news(self, bundle):
        """
        Searches news using location bundle data and returns an aggregated result.
        """
        city_name = bundle['cities'][0] if bundle['cities'] else ""
        county_name = bundle['counties'][0] if bundle['counties'] else ""
        state_name = bundle['state']
        
        # Construct multiple queries for better coverage
        queries = []
        if city_name:
            queries.append(f"disaster emergency alert {city_name}, {state_name}")
        if county_name:
            queries.append(f"disaster {county_name} County, {state_name}")
        queries.append(f"disaster emergency alert {state_name}")
        
        max_severity = 0
        top_text = "No disaster reports found."
        location_found = f"{city_name or county_name or state_name}"
        
        for query in queries[:2]: # Limit to top 2 queries for speed
            try:
                raw_news = get_news_search(query)
                if "No recent results" in raw_news:
                    continue
                
                texts = [line.strip() for line in raw_news.split("\n\n") if line.strip()]
                results = self.scan_texts(texts)
                
                if results:
                    local_max = max(r['severity'] for r in results)
                    if local_max > max_severity:
                        max_severity = local_max
                        top_text = results[0]['text']
                        break # Found something relevant
            except Exception as e:
                print(f"DEBUG: News scan error for {query}: {e}")
        
        return {
            "severity": max_severity,
            "text": top_text,
            "location": location_found,
            "cell": bundle['h3']
        }

    def scan_location_news(self, lat, lon):
        """
        Legacy method for backward compatibility.
        """
        # This would ideally call get_h3_location_bundles but we don't want cyclic imports
        # For now, just a placeholder or a simple query
        query = f"disaster emergency alert {lat}, {lon}"
        try:
            raw_news = get_news_search(query)
            texts = [line.strip() for line in raw_news.split("\n\n") if line.strip()]
            results = self.scan_texts(texts)
            if not results: return {"severity": 0, "text": "No news", "location": f"{lat}, {lon}"}
            return {"severity": max(r['severity'] for r in results), "text": results[0]['text'], "location": f"{lat}, {lon}"}
        except:
            return {"severity": 0, "text": "Error", "location": f"{lat}, {lon}"}

if __name__ == "__main__":
    scanner = DisasterScanner()
    test_texts = [
        "Major flooding reported in Nashville, TN. Severe property damage.",
        "Beautiful sunny day in California."
    ]
    print(scanner.scan_texts(test_texts))
