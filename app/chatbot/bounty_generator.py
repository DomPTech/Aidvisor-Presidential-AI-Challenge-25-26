import json
import os
import datetime
from .chatbot import DisasterAgent

class DisasterBountyGenerator:
    def __init__(self, api_token=None):
        self.agent = DisasterAgent(api_token=api_token)

    def generate_bounties(self, fips_code, bio, county_name="Unknown"):
        """
        Generates system bounties based on user location and bio.
        """
        # Extract state from county_name if available (format: "County Name County, ST")
        state_code = "SD" # Default fallback
        if "," in county_name:
            state_code = county_name.split(",")[-1].strip().upper()

        prompt = f"""
You are an Emergency Response Intelligence Agent. 

CONTEXT:
User Location: {county_name} (FIPS: {fips_code})
Target State: {state_code}
Current Date: {datetime.datetime.now().strftime("%Y-%m-%d")}

TASK:
1. You MUST first use `get_fema_disaster_declarations` for state='{state_code}'.
2. You MUST then use `get_news_search` or `get_search` to find news about current disasters, executive orders, or urgent relief needs in {state_code}.
3. Synthesize your findings into a list of "System Bounties".

GUIDELINES:
- Focus on ACTIVE or RECENT natural disasters (e.g., winter storms, floods, drought, wildfires).
- Look for official Executive Orders, SBA disaster loans, or Red Cross/Salvation Army response efforts.
- DO NOT invent data. If you find a real event but no phone/email, leave those fields empty.
- Every 'link' MUST be a real URL from your search results.
- Accuracy is more important than quantity.

REQUIRED SCHEMA:
[
  {{
    "title": "String (Specific Disaster + Role/Need)",
    "description": "String (Detailed summary found in news/gov data)",
    "location": "String (City, State)",
    "urgency": 1-10,
    "contact_info": {{
      "phone": "String",
      "email": "String",
      "link": "String"
    }}
  }}
]
Return ONLY the raw JSON array. No reasoning.
"""
        # We'll use the agent's tools to find info
        from .tools.ddg_search import get_news_search, get_search
        from .tools.nws_alerts import get_nws_alerts
        from .tools.openfema import get_fema_disaster_declarations
        
        self.agent.tools.update({
            "get_news_search": get_news_search,
            "get_search": get_search,
            "get_nws_alerts": get_nws_alerts,
            "get_fema_disaster_declarations": get_fema_disaster_declarations
        })
        
        response = self.agent.get_response(prompt)
        
        try:
            cleaned_response = self.agent._clean_response(response)
            start_idx = cleaned_response.find('[')
            end_idx = cleaned_response.rfind(']')
            
            if start_idx != -1:
                # If we have a closing bracket, use it as the end
                if end_idx != -1 and end_idx > start_idx:
                    json_str = cleaned_response[start_idx:end_idx + 1]
                else:
                    # Truncated: take from start to end of string and attempt repair
                    json_str = cleaned_response[start_idx:]
                
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # Attempt to repair fragment
                    repaired_json = self.repair_json_fragment(json_str)
                    if repaired_json:
                        try:
                            return json.loads(repaired_json)
                        except:
                            pass
            return []
        except Exception as e:
            print(f"Error parsing AI bounties: {e}")
            print(f"Raw response: {response}")
            return []

    def repair_json_fragment(self, json_str):
        """
        Attempts to repair a truncated JSON string by closing open brackets/braces
        and removing trailing commas or incomplete keys/values.
        """
        if not json_str:
            return ""
            
        # 1. Basic stack-based bracket closer
        stack = []
        in_string = False
        escape = False
        
        # We'll build a "valid-ish" prefix by finding the last complete object we can
        # but first let's try the simple "close everything" approach
        
        cleaned = json_str.strip()
        
        # Remove trailing comma if exists
        if cleaned.endswith(','):
            cleaned = cleaned[:-1]
            
        # Track brackets
        for char in cleaned:
            if char == '"' and not escape:
                in_string = not in_string
            elif not in_string:
                if char == '{' or char == '[':
                    stack.append(char)
                elif char == '}' or char == ']':
                    if stack:
                        stack.pop()
            
            if char == '\\' and not escape:
                escape = True
            else:
                escape = False
        
        # If we are inside a string, close it
        if in_string:
            cleaned += '"'
            
        # Now we might be in the middle of a key or value like "contact_info": {"
        # or "urgency": 2, "title": "
        
        # A more aggressive approach: if the last thing isn't a closing brace/bracket,
        # try to find the last complete object in the array.
        
        # For our specific schema, we are expecting an array of objects.
        # Let's try to truncate the string at the last complete object '}'
        last_object_end = cleaned.rfind('}')
        if last_object_end != -1:
            # Check if there's an opening [ before it
            if '[' in cleaned[:last_object_end]:
                cleaned = cleaned[:last_object_end + 1]
                # Reset stack for the new truncated string
                stack = []
                for char in cleaned:
                    if char == '[': stack.append('[')
                    elif char == ']': 
                        if stack: stack.pop()
                    elif char == '{': stack.append('{')
                    elif char == '}':
                        if stack: stack.pop()
        
        # Close remaining stack
        while stack:
            opener = stack.pop()
            if opener == '{':
                cleaned += '}'
            elif opener == '[':
                cleaned += ']'
                
        return cleaned

    def get_cached_bounties(self, user_id, fips_code, bio, county_name="Unknown", cache_dir="data/caches", force=False):
        """
        Checks for a local cache of bounties for the user. 
        Regenerates if older than 3 hours, missing, or if forced.
        """
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        cache_file = os.path.join(cache_dir, f"system_bounties_{user_id}.json")
        
        now = datetime.datetime.now()
        
        if not force and os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                try:
                    cache_data = json.load(f)
                    cached_time = datetime.datetime.fromisoformat(cache_data.get("timestamp"))
                    if (now - cached_time).total_seconds() < 3 * 3600:
                        return cache_data.get("bounties", [])
                except:
                    pass
        
        # Regenerate
        bounties = self.generate_bounties(fips_code, bio, county_name)
        if bounties:
            with open(cache_file, "w") as f:
                json.dump({
                    "timestamp": now.isoformat(),
                    "bounties": bounties
                }, f, indent=2)
        
        return bounties
