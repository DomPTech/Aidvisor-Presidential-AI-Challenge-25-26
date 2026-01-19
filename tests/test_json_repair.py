from app.chatbot.bounty_generator import DisasterBountyGenerator
import json

def test_repair():
    bg = DisasterBountyGenerator()
    
    # Test case 1: Truncated mid-object
    fragment1 = '[{"title": "Disaster 1"}, {"title": "Disaster 2", "description": "'
    repaired1 = bg.repair_json_fragment(fragment1)
    print(f"Fragment 1: {fragment1}")
    print(f"Repaired 1: {repaired1}")
    try:
        parsed1 = json.loads(repaired1)
        print(f"Parsed 1: {parsed1}")
        assert len(parsed1) == 1
        assert parsed1[0]["title"] == "Disaster 1"
    except Exception as e:
        print(f"Failed 1: {e}")

    # Test case 2: Truncated mid-key
    fragment2 = '[{"title": "Disaster 1"}, {"title": "Disaster 2", "contact_info": {"'
    repaired2 = bg.repair_json_fragment(fragment2)
    print(f"\nFragment 2: {fragment2}")
    print(f"Repaired 2: {repaired2}")
    try:
        parsed2 = json.loads(repaired2)
        print(f"Parsed 2: {parsed2}")
        assert len(parsed2) == 1
    except Exception as e:
        print(f"Failed 2: {e}")

    # Test case 3: Truncated with a trailing comma
    fragment3 = '[{"title": "Disaster 1"}, '
    repaired3 = bg.repair_json_fragment(fragment3)
    print(f"\nFragment 3: {fragment3}")
    print(f"Repaired 3: {repaired3}")
    try:
        parsed3 = json.loads(repaired3)
        print(f"Parsed 3: {parsed3}")
        assert len(parsed3) == 1
    except Exception as e:
        print(f"Failed 3: {e}")

    # Test case 4: The specific case from the error
    fragment4 = '[{"title": "FEMA Disaster Funding Available for Tennessee (Past Disasters)", "description": "FEMA announced nearly $9 million in federal funding is now available to communities in Tennessee affected by Tropical Storm Helene and other past disasters.", "location": "Knox County, Tennessee", "urgency": 3, "contact_info": {"phone": "", "email": "", "link": "https://www.hstoday.us/subject-matter-areas/emergency-preparedness/fema-makes-available-almost-9-million-in-funding-for-tennessee/"}}, {"title": "Tennessee Disaster Recovery Funding for Hurricane Helene", "description": "Federal officials allocated $116 million to North Carolina for Hurricane Helene recovery, but no specific Tennessee disaster funding was mentioned in news searches.", "location": "Statewide, Tennessee", "urgency": 2, "contact_info": {"'
    repaired4 = bg.repair_json_fragment(fragment4)
    print(f"\nFragment 4 (Long): {fragment4[-50:]}")
    print(f"Repaired 4: {repaired4[-50:]}")
    try:
        parsed4 = json.loads(repaired4)
        print(f"Parsed 4 length: {len(parsed4)}")
        assert len(parsed4) == 1
    except Exception as e:
        print(f"Failed 4: {e}")

if __name__ == "__main__":
    test_repair()
