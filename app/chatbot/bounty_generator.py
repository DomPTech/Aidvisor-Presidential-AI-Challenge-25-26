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

CRITICAL: Return ONLY the raw JSON array with NO markdown formatting, NO code blocks, NO explanations.
Do NOT wrap in ```json or ``` tags. Just the pure JSON array starting with [ and ending with ].
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
        
        
        print(f"\n=== AI Bounty Generator Debug ===")
        print(f"Agent client initialized: {self.agent.client is not None}")
        
        try:
            response = self.agent.get_response(prompt)
        except Exception as e:
            print(f"❌ Error calling get_response: {e}")
            import traceback
            traceback.print_exc()
            print(f"=== End Debug ===")
            return []
        
        
        # Check if response is an error message
        if response.startswith("Error:"):
            print(f"❌ API Error: {response}")
            print(f"=== End Debug ===")
            return []
        
        print(f"Raw response length: {len(response)}")
        print(f"Raw response preview: {response[:500]}...")
        
        try:
            cleaned_response = self.agent._clean_response(response)
            
            # Try to extract JSON from markdown code blocks first
            import re
            json_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', cleaned_response)
            if json_block_match:
                cleaned_response = json_block_match.group(1).strip()
                print(f"Extracted from markdown code block")
            
            print(f"Cleaned response preview: {cleaned_response[:500]}...")
            
            start_idx = cleaned_response.find('[')
            end_idx = cleaned_response.rfind(']')
            
            
            if start_idx != -1:
                # If we have a closing bracket, use it as the end
                if end_idx != -1 and end_idx > start_idx:
                    json_str = cleaned_response[start_idx:end_idx + 1]
                else:
                    # Truncated: take from start to end of string and attempt repair
                    json_str = cleaned_response[start_idx:]
                
                print(f"Attempting to parse JSON of length {len(json_str)}")
                print(f"Full JSON string: {json_str}")
                
                try:
                    result = json.loads(json_str)
                    print(f"✅ Successfully parsed {len(result)} bounties")
                    return result
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error: {e}")
                    # Attempt to repair fragment
                    repaired_json = self.repair_json_fragment(json_str)
                    if repaired_json:
                        print(f"Repaired JSON: {repaired_json}")
                        try:
                            result = json.loads(repaired_json)
                            print(f"✅ Successfully parsed {len(result)} bounties after repair")
                            return result
                        except Exception as e2:
                            print(f"❌ Failed to parse repaired JSON: {e2}")
            else:
                print(f"❌ No JSON array found in response")
            
            print(f"=== End Debug ===")
            return []
        except Exception as e:
            print(f"❌ Error parsing AI bounties: {e}")
            print(f"Raw response: {response}")
            print(f"=== End Debug ===")
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
        
        
        # For our specific schema, we are expecting an array of objects.
        # Find the last complete object '}' and truncate there
        last_object_end = cleaned.rfind('}')
        if last_object_end != -1:
            # Truncate at the last complete object
            cleaned = cleaned[:last_object_end + 1]
            
            # Validate bracket matching by counting
            open_braces = cleaned.count('{')
            close_braces = cleaned.count('}')
            open_brackets = cleaned.count('[')
            close_brackets = cleaned.count(']')
            
            # Remove extra closing braces if any
            while close_braces > open_braces and cleaned.endswith('}'):
                cleaned = cleaned[:-1].rstrip()
                close_braces = cleaned.count('}')
            
            # Add missing closing brackets for the array
            while close_brackets < open_brackets:
                cleaned += ']'
                close_brackets += 1
        
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
