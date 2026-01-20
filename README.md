# Presidential AI Challenge 25-26
Developed by Dominick Pelaia, Levi Dunn, Eli Ferency, and Hayden Hellsten for submission to the Presidential AI Challenge
## Goal
This project is designed to provide a platform to help people quickly connect to those willing to help during natural disasters and utilize AI to facilitate improved coordination and awareness of issues.
## Project Overview
This project is a disaster prediction and volunteering coordination portal. It integrates:
- **UI**: Streamlit
- **Chatbot**: Deepseek V3 Turbo LLM Agent with tool calling (NWS Alerts, Google News) and RAG (Retrieval Augmented Generation) significantly increasing the efficacy of our queries
- **Map**: Pydeck (utilizes LLM Agent tools and BERT sentiment analysis to create heatmap)
- **Coordination**: Volunteering management system trough Supabase and AI recommendations
- **Database**: Supabase 
- **Messaging**: Direct and global messaging through the Supabase Database
- **Automatic Bounty Generation**: PocketSphinx for audio recording and transcription that is then fed into the chatbot; the chatbot then fits the information and user profile into the correct JSON format so it can be published

## Current Architecture
- `Main` (Home): Streamlit Frontend with Pydeck map that scans for areas impacted by natural disasters with BERT model
- `pages/1_Login`: Account creation and login via Supabase
- `app/9_Bounty Board`: Request aid, apply to help, and receive personalized recommendations
- `pages/2_Chatbot`: Utilizes Novita API key for summaries of reports and relevant natural disaster information through tool calling of APIs such as NASA, FEMA, NWS, and DuckDuckGo Search
- `pages/5_Groups`: Global messaging, direct messaging, and leaderboards through Supabase database
- `app/10_Audio_Recorder`: Records audio, uses PocketSphinx to transcribe audio, feeds text into a chatbot that turns data into a JSON; the user can then choose to either submit it or edit a request 
- `app/8_profile`: User profile shows skills, bio, and badge, and it allows for bounty management and password changes

## How to Run
### Setup
- Run the following commands from the directory where you want to install the project:
```bash
git clone https://github.com/DomPTech/AIdvisor-Presidential-AI-Challenge-25-26
cd AIdvisor-Presidential-AI-Challenge-25-26
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
pip install -r requirements.txt

```
*(The `cp` command copies the example secrets file so that you can conveniently paste in your own keys.)*
- Then, plug in our Supabase URL, API key, and Novita API Key into `secrets.toml`.
### Running the App
- Run the following command in the project directory:
```bash
streamlit run Main.py
```
- Wait for initial scan in `Main.py` to finish.

## Initial Idea
### Initial Project Idea
![Project Diagram](/Images/V1diagram.jpg)
### Refined Project Idea
![Project Diagram](/Images/V2%20Presidential%20AI%20Challenge%20Diagram.png)
- While developing our app, we ultimately decided to scope its capabilities to providing assistance in existing disasters rather than anticipating new ones. Accordingly, we removed features such as the disaster prediction tab in order to focus on this intention.
## Final Diagram
![Project Diagram](/Images/Presidential%20AI%20Challenge%20Overall%20Framework.png)
