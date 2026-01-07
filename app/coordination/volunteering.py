from app.chatbot.chatbot import DisasterAgent
from app.chatbot.tools.google_news import get_google_news
from app.chatbot.tools.openfema import get_fema_disaster_declarations, get_fema_assistance_data

def get_volunteer_opportunities():
    """
    Placeholder to get volunteer opportunities.
    """
    return ["Opportunity 1", "Opportunity 2"]

def get_recommendations(user_info, hf_api_key, hf_model_id="deepseek-ai/DeepSeek-R1"):
    """
    Get AI-driven volunteer and donation recommendations based on user info.
    """
    if not hf_api_key:
        return "Please provide a HuggingFace API Key in the settings sidebar to get recommendations."
    
    tools = {
        "get_google_news": get_google_news,
        "get_fema_disaster_declarations": get_fema_disaster_declarations,
        "get_fema_assistance_data": get_fema_assistance_data
    }
    agent = DisasterAgent(model_id=hf_model_id, api_token=hf_api_key, tools=tools)
    
    location = user_info.get('location', 'N/A')
    distance = user_info.get('distance', 'N/A')
    
    prompt = f"""
    The user has provided the following information for volunteer/donation efforts:
    - Location: {location}
    - Search Radius: {distance} miles
    - Skills: {user_info.get('skills', 'N/A')}
    - Interests: {user_info.get('interests', 'N/A')}
    - Availability: {user_info.get('availability', 'N/A')}

    Based on this information and your knowledge of disaster-prone areas or ongoing relief efforts (you can use your internal knowledge if no specific tool data is available, but act as a coordination expert), provide recommendations focusing on areas in and around {location} within a {distance} mile radius.
    
    Provide:
    1. Recommended areas of most concern/need of volunteer efforts.
    2. Specific donation needs in those areas.
    3. How the user's specific skills could be used.
    4. Include Adresses and use most needed areas in the present, don't use the past
    
    Keep the response concise, structured with headers, and encouraging.
    """
    
    response = agent.get_response(prompt)
    return response
