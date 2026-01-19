from .chatbot import DisasterAgent

class DisasterBountyMatcher:
    """Matches users with disaster bounties using AI analysis."""
    
    def __init__(self, api_token=None):
        """
        Initialize the bounty matcher.
        
        Args:
            api_token: Hugging Face API token for the inference API
        """
        self.agent = DisasterAgent(api_token=api_token)
    
    def find_best_match(
        self, 
        user_profile: dict, 
        bounties: list,
        county_name: str = "Unknown"
    ) -> str:
        """
        Find the best bounty match for a user using AI analysis.
        
        Args:
            user_profile: User data including bio, skills, fips_code
            bounties: List of anonymized bounties with id, disaster_type, urgency, etc.
            county_name: User's county name for context
            
        Returns:
            The anonymized ID of the best matching bounty, or None if no match
        """
        if not bounties:
            return None
        
        # Prepare the prompt for the AI
        prompt = self._create_matching_prompt(user_profile, bounties, county_name)
        
        print(f"\n=== AI Bounty Matcher Debug ===")
        print(f"Agent client initialized: {self.agent.client is not None}")
        print(f"Number of bounties to match: {len(bounties)}")
        
        try:
            response = self.agent.get_response(prompt)
        except Exception as e:
            print(f"❌ Error calling get_response: {e}")
            import traceback
            traceback.print_exc()
            print(f"=== End Debug ===")
            # Fallback to rule-based matching
            return self._fallback_match(bounties)
        
        # Check if response is an error message
        if response.startswith("Error:"):
            print(f"❌ API Error: {response}")
            print(f"=== End Debug ===")
            return self._fallback_match(bounties)
        
        print(f"Raw response length: {len(response)}")
        print(f"Raw response: {response}")
        
        try:
            # Extract the bounty ID from the response
            best_id = self._parse_response(response, bounties)
            
            if best_id:
                print(f"✅ Successfully matched to bounty: {best_id}")
            else:
                print(f"⚠️ No match found in response, using fallback")
                best_id = self._fallback_match(bounties)
            
            print(f"=== End Debug ===")
            return best_id
            
        except Exception as e:
            print(f"❌ Error parsing AI response: {e}")
            print(f"Raw response: {response}")
            print(f"=== End Debug ===")
            return self._fallback_match(bounties)
    
    def _create_matching_prompt(
        self, 
        user_profile: dict, 
        bounties: list,
        county_name: str
    ) -> str:
        """Create a prompt for the AI to analyze bounties."""
        
        user_bio = user_profile.get('bio', 'No bio provided')
        user_skills = user_profile.get('skills', []) or []
        skills_str = ', '.join(user_skills) if user_skills else 'No specific skills listed'
        
        # Format bounties for the prompt
        bounty_descriptions = []
        for i, b in enumerate(bounties, 1):
            dist_str = f", {b['distance_km']:.1f}km away" if b.get('distance_km') else ""
            bounty_descriptions.append(
                f"ID: {b['id']}\n"
                f"  Type: {b['disaster_type']}\n"
                f"  Urgency: {b['urgency']}/10\n"
                f"  Description: {b['content'][:200]}\n"
                f"  Distance: {dist_str if dist_str else 'Unknown'}\n"
                f"  Current volunteers: {b.get('volunteers_count', 0)}\n"
                f"  Applicants: {b.get('applicants_count', 0)}"
            )
        
        bounties_text = "\n\n".join(bounty_descriptions)
        
        prompt = f"""You are a disaster response coordinator AI. Your job is to match volunteers with help requests based on their skills, location, and the urgency of needs.

USER PROFILE:
Location: {county_name}
Bio: {user_bio}
Skills: {skills_str}

AVAILABLE BOUNTIES:
{bounties_text}

TASK:
Analyze the user's profile and the available bounties. Consider:
1. Distance (closer is better, but urgent needs override distance)
2. Urgency level (higher urgency = higher priority)
3. User skills matching the disaster type and need
4. Current volunteer coverage (under-served needs are priority)

CRITICAL: Respond with ONLY the ID of the best matching bounty. No explanation, no formatting, just the ID string.

Example valid responses:
a1b2c3d4e5f6g7h8
9f8e7d6c5b4a3210

Choose the single best match now and respond with ONLY its ID:"""
        
        return prompt
    
    def _parse_response(self, response: str, bounties: list) -> str:
        """Extract the bounty ID from the AI response."""
        
        # Clean the response
        cleaned = self.agent._clean_response(response).strip()
        
        # Remove common prefixes
        prefixes = ["BEST_MATCH:", "ID:", "Bounty ID:", "Match:", "Best match:"]
        for prefix in prefixes:
            if prefix in cleaned:
                parts = cleaned.split(prefix)
                if len(parts) > 1:
                    cleaned = parts[1].strip()
                    break
        
        # Get first line/word
        cleaned = cleaned.split('\n')[0].strip()
        cleaned = cleaned.split()[0].strip() if cleaned.split() else cleaned
        
        # Remove any remaining punctuation
        cleaned = cleaned.strip('.,!?;:"\'')
        
        # Validate that this ID exists in our bounty list
        valid_ids = [b['id'] for b in bounties]
        
        # Direct match
        if cleaned in valid_ids:
            return cleaned
        
        # Try to find any valid bounty ID mentioned anywhere in the response
        for valid_id in valid_ids:
            if valid_id in response:
                return valid_id
        
        return None
    
    def _fallback_match(self, bounties: list) -> str:
        """
        Fallback matching strategy when AI fails.
        Prioritizes: urgency > proximity > volunteer coverage
        """
        if not bounties:
            return None
        
        # Score each bounty
        scored = []
        for b in bounties:
            score = 0
            
            # Urgency is most important (0-100 points)
            score += b.get('urgency', 0) * 10
            
            # Proximity bonus (up to 30 points, closer = better)
            if b.get('distance_km') is not None:
                dist = b['distance_km']
                if dist < 10:
                    score += 30
                elif dist < 50:
                    score += 20
                elif dist < 100:
                    score += 10
                elif dist < 500:
                    score += 5
            
            # Under-served bonus (up to 20 points)
            volunteers = b.get('volunteers_count', 0)
            applicants = b.get('applicants_count', 0)
            total_help = volunteers + applicants
            
            if total_help == 0:
                score += 20
            elif total_help == 1:
                score += 10
            elif total_help == 2:
                score += 5
            
            scored.append((score, b['id']))
        
        # Return the highest scoring bounty
        scored.sort(reverse=True)
        return scored[0][1] if scored else None