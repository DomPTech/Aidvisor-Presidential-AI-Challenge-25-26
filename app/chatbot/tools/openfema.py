from numpy import rint
import requests
import json
from datetime import datetime, timedelta

def get_fema_disaster_declarations(state=None, county=None, days=360):
    """
    Fetch disaster declarations from OpenFEMA.
    """
    base_url = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"
    
    # Calculate date filter
    # Use a longer window by default if none specified
    date_limit = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%dT00:00:00.000Z')
    filters = [f"declarationDate ge '{date_limit}'"]
    
    if state:
        filters.append(f"state eq '{state.upper()}'")
    if county:
        # Format county as 'County Name (County)' for exact match
        if "County" in county:
            county_name = county.replace(" County", "")
            designated_area = f"{county_name} (County)"
        elif "Parish" in county:
            county_name = county.replace(" Parish", "")
            designated_area = f"{county_name} (Parish)"
        else:
            designated_area = county
        filters.append(f"designatedArea eq '{designated_area}'")
        
    filter_query = " and ".join(filters)
    url = f"{base_url}?$filter={filter_query}&$top=10&$orderby=declarationDate desc"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        declarations = data.get('DisasterDeclarationsSummaries', [])
        if not declarations:
            return {
                "summary": f"No recent FEMA disaster declarations found for {state or ''} {county or ''}.",
                "visuals": None
            }
        
        # Deduplicate by disaster number since multiple counties can be in one declaration
        seen_disasters = set()
        result = "Recent FEMA Disaster Declarations:\n"
        count = 0
        for dec in declarations:
            dec_id = dec.get('disasterNumber')
            if dec_id in seen_disasters:
                continue
            seen_disasters.add(dec_id)
            
            date = dec.get('declarationDate', 'N/A')[:10]
            title = dec.get('declarationTitle', 'N/A')
            incident = dec.get('incidentType', 'N/A')
            result += f"- {date}: {title} (Type: {incident}, ID: {dec_id})\n"
            count += 1
            if count >= 5: break
            
        return {
            "summary": result,
            "visuals": None # Generic declarations don't need a specific map/chart yet
        }
    except Exception as e:
        return {
            "summary": f"Error fetching FEMA declarations: {str(e)}",
            "visuals": None
        }

def get_fema_assistance_data(state, county=None):
    """
    Fetch summary assistance data to gauge community need using the Housing Assistance Owners (v2) dataset.
    """
    base_url = "https://www.fema.gov/api/open/v2/HousingAssistanceOwners"
    
    filters = [f"state eq '{state.upper()}'"]
    if county:
        filters.append(f"substringof('{county}', county)")
        
    filter_query = " and ".join(filters)
    # Order by disasterNumber descending to get most recent aid data
    url = f"{base_url}?$filter={filter_query}&$top=10&$orderby=disasterNumber desc"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        summaries = data.get('HousingAssistanceOwners', [])
        if not summaries:
            return {
                "summary": f"No FEMA housing assistance data found for {state} {county or ''}.",
                "visuals": None
            }
            
        result = f"Recent FEMA Housing Assistance Data (Owners) for {state}:\n"
        chart_data = []
        # Records are by Zip code, so we aggregate or show top zip codes
        for item in summaries[:5]:
            county_name = item.get('county', 'Unknown County')
            city = item.get('city', 'Unknown City')
            zip_code = item.get('zipCode', 'N/A')
            approved = item.get('totalApprovedIhpAmount', 0)
            valid_reg = item.get('validRegistrations', 0)
            disaster = item.get('disasterNumber', 'N/A')
            
            if approved > 0 or valid_reg > 0:
                label = f"{city} ({zip_code})"
                result += f"- {label}, {county_name}: ${approved:,.2f} approved for {valid_reg} registrations (Disaster: {disaster}).\n"
                chart_data.append({
                    "Location": label,
                    "Approved Funding ($)": approved,
                    "Registrations": valid_reg
                })
        
        return {
            "summary": result,
            "visuals": {
                "type": "chart",
                "data": chart_data
            } if chart_data else None
        }
    except Exception as e:
        return {
            "summary": f"Error fetching FEMA assistance data: {str(e)}",
            "visuals": None
        }

if __name__ == "__main__":
    # Test queries
    print(get_fema_disaster_declarations(state='TN', days=120))
    print(get_fema_assistance_data(state='NC'))
