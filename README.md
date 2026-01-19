# Presidential AI Challenge 25-26
Developed by Dominick Pelaia, Levi Dunn, Eli Ferency, and Hayden Hellsten for submission to the Presidential AI Challenge

## Project Overview
This project is a disaster prediction and volunteering coordination portal. It integrates:
- **UI**: Streamlit
- **Chatbot**: QWEN-3 8B LLM Agent with tool calling (NWS Alerts, Google News)
- **Map**: Pydeck (utilizes LLM Agent tools and BERT sentiment analysis to create heatmap)
- **Database**: Supabase 
- **Coordination**: Volunteering management system 
- **Messaging**: Direct and global messaging through the Supabase Database
## Goal
This project is designed to provide a platform to help people quickly connect to those willing to help during natural disasters and utilize AI to facilitate improved coordination and awareness of issues.

## Architecture
- `Main`(Home): Streamlit Frontend with Pydeck map that scans for areas impacted by natural disasters with BERT model
- `pages/1_Login`: Account creation and login via Supabase
- `app/9_Bounty Board`: Request aid, apply to help, and receive personalized recommendations
- `pages/2_Chatbot`: Utilizes Hugging Face api key for summaries of reports and relevant natural disaster information through tool calling of API's such as NASA, FEMA, NWS, and Duck Duck Go Search
- `pages/5_Groups`: Global messaging, direct messaging, and leaderboards through Supabase database
- `app/10_Audio_Recorder`: Records audio, uses PocketSphinx to transcribe audio, feeds text into a chatbot that turns data into a json that user can choose to either submit or edit a request 
- `app/8_profile`: User profile with skills, bio, and badge, managing bounties, showing current bounties that user volunteered and applied for, and change password.

## How to Run
- Copy `secrets.toml.example` and rename to `secrets.toml` and plug in our `Supabase URL`, `API key`, and 'Hugging Face API Key' (for security purposes)
- `pip install -r requirements.txt`
- `streamlit run Main.py`
- Wait for initial scan in `Main.py`

## Initial Idea
- Initial Project Idea
![Project Diagram](/Images/V1diagram.jpg)
- Second Project Idea
![Project Diagram](/Images/V2Presidential%20AI%20Challenge%20Overall%20Framework.jpg)