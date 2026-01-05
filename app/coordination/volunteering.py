from app.chatbot.chatbot import DisasterAgent

def get_volunteer_opportunities():
    """
    Placeholder to get volunteer opportunities.
    """
    return ["Opportunity 1", "Opportunity 2"]

def get_recommendations(user_info, hf_api_key):
    """
    Get AI-driven volunteer and donation recommendations based on user info.
    """
    if not hf_api_key:
        return "Please provide a HuggingFace API Key in the settings sidebar to get recommendations."
    
    agent = DisasterAgent(api_token=hf_api_key)
    
    prompt = f"""
    The user has provided the following information for volunteer/donation efforts:
    - Location: {user_info.get('location', 'N/A')}
    - Skills: {user_info.get('skills', 'N/A')}
    - Interests: {user_info.get('interests', 'N/A')}
    - Availability: {user_info.get('availability', 'N/A')}

    Based on this information or ongoing relief efforts (you can use your internal knowledge if no specific tool data is available, but act as a coordination expert), provide:
    1. Recommended areas of most concern/need of volunteer efforts.
    2. Specific donation needs in those areas.
    3. How the user's specific skills could be used.
    4. Include Adresses and use most needed areas in the present, don't use the past
    
    Keep the response concise, structured with headers, and encouraging.
    """
    
    response = agent.get_response(prompt)
    return response
