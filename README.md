# Presidential AI Challenge 25-26
Developed by Dominick Pelaia, Levi Dunn, Eli Ferency, and Hayden Hellsten for submission to the Presidential AI Challenge

## Project Overview
This project is a disaster prediction and volunteering coordination portal. It integrates:
- **UI**: Streamlit
- **Chatbot**: LLM Agent with tool calling (NWS Alerts, Google News)
- **Map**: Pydeck (utilizes LLM Agent tools to create heatmap)
- **Database**: Supabase with integration with our local model 
- **Coordination**: Volunteering management system 
- **Messaging**: Direct and global messaging through the Supabase Database
## Goal
This project is designed to provide a platform to help people quickly connect to those willing to help during natural disasters and utilize AI to facilitate improved coordination and awareness of issues

## Architecture
- `Main`: Streamlit Frontend with Pydeck map that scans for areas impacted by natural disasters
- `pages/1_Login`: Account creation and login via Supabase
- `pages/2_Chatbot`: Utilizes Hugging Face api key for summaries of reports and relevant natural disaster information
- `pages/3_Prediction`: Prediction model 
- `app/prediction`: PyTorch models
- `app/coordination`: Volunteering logic
- `app/database`: Firebase interactions

## How to Run
- Copy secrets.toml.example and rename to secrets.toml and plug in our Supabase URL and API key (for security purposes)
- pip install -r requirements.txt
- streamlit run main.py 
- Wait for initial scan in main.py
- Then if you are interested in running the chatbot you can use a Hugging Face API key 