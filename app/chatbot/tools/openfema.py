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
        # Match 'County Name (County)' format which is common in designatedArea
        filters.append(f"substringof('{county}', designatedArea)")
        
    filter_query = " and ".join(filters)
    url = f"{base_url}?$filter={filter_query}&$top=10&$orderby=declarationDate desc"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        declarations = data.get('DisasterDeclarationsSummaries', [])
        if not declarations:
            return f"No recent FEMA disaster declarations found for {state or ''} {county or ''}."
        
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
            
        return result
    except Exception as e:
        return f"Error fetching FEMA declarations: {str(e)}"

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
            return f"No FEMA housing assistance data found for {state} {county or ''}."
            
        result = f"Recent FEMA Housing Assistance Data (Owners) for {state}:\n"
        # Records are by Zip code, so we aggregate or show top zip codes
        for item in summaries[:5]:
            county_name = item.get('county', 'Unknown County')
            city = item.get('city', 'Unknown City')
            zip_code = item.get('zipCode', 'N/A')
            approved = item.get('totalApprovedIhpAmount', 0)
            valid_reg = item.get('validRegistrations', 0)
            disaster = item.get('disasterNumber', 'N/A')
            if approved > 0 or valid_reg > 0:
                result += f"- {city}, {county_name} (Zip: {zip_code}): ${approved:,.2f} approved for {valid_reg} registrations (Disaster: {disaster}).\n"
        
        return result
    except Exception as e:
        return f"Error fetching FEMA assistance data: {str(e)}"

if __name__ == "__main__":
    # Test queries
    print(get_fema_disaster_declarations(state='TN', days=120))
    print(get_fema_assistance_data(state='NC'))
