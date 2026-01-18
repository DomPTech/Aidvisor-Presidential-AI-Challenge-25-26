import streamlit as st
import re
import torch
from transformers import pipeline
from app.chatbot.tools.openfema import get_fema_disaster_declarations

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
        # Fast keyword pre-filter to avoid constant LLM inference
        self.disaster_keywords = [
            "flood", "flood", "storm", "hurricane", "tornado", "earthquake", 
            "fire", "wildfire", "emergency", "evacuation", "warning", "watch",
            "damage", "victim", "rescue", "disaster", "alert", "danger"
        ]
        
    def get_severity_score(self, text):
        """
        Calculates a severity score (0-10) based on zero-shot classification results.
        """
        # Keyword check before BERT
        if not any(kw in text.lower() for kw in self.disaster_keywords):
            return 0.0

        result = self.classifier(text, candidate_labels=self.candidate_labels)
        label_to_score = {
            "Critical Disaster": 10,
            "Moderate Warning": 5,
            "General Information": 2,
            "Not Disaster Related": 0
        }
        
        top_label = result['labels'][0]
        top_score = result['scores'][0]
        
        base_score = label_to_score[top_label]
        final_score = base_score * top_score
        
        return round(min(10, final_score), 1)

    def scan_texts(self, texts):
        """
        Scans a list of texts using batch processing for performance.
        """
        # 1. Quick Keyword Filter
        filtered_indices = []
        filtered_texts = []
        for i, text in enumerate(texts):
            if any(kw in text.lower() for kw in self.disaster_keywords):
                filtered_indices.append(i)
                filtered_texts.append(text)
        
        if not filtered_texts:
            return []

        # 2. Batch BERT Classification
        results = []
        try:
            # The transformers pipeline supports batching if passed a list
            batch_results = self.classifier(filtered_texts, candidate_labels=self.candidate_labels)
            
            # If only one text, result might not be a list of dicts but a dict
            if isinstance(batch_results, dict):
                batch_results = [batch_results]

            label_to_score = {
                "Critical Disaster": 10,
                "Moderate Warning": 5,
                "General Information": 2,
                "Not Disaster Related": 0
            }

            for i, res in enumerate(batch_results):
                top_label = res['labels'][0]
                top_score = res['scores'][0]
                severity = round(min(10, label_to_score[top_label] * top_score), 1)
                
                if severity > 0:
                    results.append({
                        "text": filtered_texts[i][:200] + "...", 
                        "severity": severity,
                    })
        except Exception as e:
            print(f"Error in batch scan: {e}")
            
        return results

    def scan_bundle_news(self, bundle):
        counties = bundle.get('counties', [])[:3]
        state = bundle.get('state', "Unknown")
        state_abbr = us_state_to_abbrev.get(state, "Unknown")

        if not state_abbr or state_abbr == "Unknown":
            return self._empty_response(bundle)

        fema_data = ""

        # Try county-specific queries first, then fall back to state
        if counties:
            for county in counties:
                fema_data = get_fema_disaster_declarations(state=state_abbr, county=county, days=30)
                if not ("No recent FEMA disaster declarations found" in fema_data or "Error" in fema_data):
                    break
        
        # If no county-specific results, try state-wide
        if not fema_data or "No recent FEMA disaster declarations found" in fema_data or "Error" in fema_data:
            fema_data = get_fema_disaster_declarations(state=state_abbr, days=30)

        if "No recent FEMA disaster declarations found" in fema_data or "Error" in fema_data:
            return self._empty_response(bundle)

        # Parse the FEMA data to extract disaster info
        lines = fema_data.split('\n')
        disasters = []
        for line in lines:
            if line.startswith('- '):
                # Extract date, title, type, id
                parts = line[2:].split(': ')
                if len(parts) >= 2:
                    date = parts[0]
                    rest = ': '.join(parts[1:])
                    # Extract incident type
                    if '(Type: ' in rest:
                        title_part, type_part = rest.split(' (Type: ')
                        incident_type = type_part.split(',')[0]
                        disasters.append({
                            'date': date,
                            'title': title_part,
                            'type': incident_type
                        })

        if not disasters:
            return self._empty_response(bundle)

        # Determine severity based on disaster types
        severity_scores = {
            'Flood': 8,
            'Hurricane': 10,
            'Tornado': 9,
            'Earthquake': 10,
            'Fire': 9,
            'Severe Storm': 7,
            'Winter Storm': 6,
            'Drought': 5,
            'Other': 4
        }

        max_severity = 0
        top_disaster = disasters[0]
        for disaster in disasters:
            incident_type = disaster['type']
            severity = severity_scores.get(incident_type, 4)
            if severity > max_severity:
                max_severity = severity
                top_disaster = disaster

        top_text = f"{top_disaster['title']} (Type: {top_disaster['type']}, Date: {top_disaster['date']})"

        output = {
            "severity": max_severity,
            "location": ", ".join(counties) if counties else state,
            "text": top_text,
            "cell": bundle.get('h3')
        }
        print("Found output: ", output)
        return output

    def _empty_response(self, bundle):
        # print("No disaster reports found for bundle: ", bundle)
        return {"severity": 0, "text": "No reports found.", "cell": bundle.get('h3')}

if __name__ == "__main__":
    scanner = DisasterScanner()
    test_texts = [
        "Major flooding reported in Nashville, TN. Severe property damage.",
        "Beautiful sunny day in California."
    ]
    print(scanner.scan_texts(test_texts))

us_state_to_abbrev = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
    "District of Columbia": "DC",
    "American Samoa": "AS",
    "Guam": "GU",
    "Northern Mariana Islands": "MP",
    "Puerto Rico": "PR",
    "United States Minor Outlying Islands": "UM",
    "Virgin Islands, U.S.": "VI",
}