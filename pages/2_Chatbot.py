import streamlit as st
from app.chatbot.chatbot import DisasterAgent
from app.chatbot.tools.ddg_search import get_search, get_news_search
from app.chatbot.tools.nws_alerts import get_nws_alerts
from app.chatbot.tools.openfema import get_fema_disaster_declarations, get_fema_assistance_data
from app.chatbot.tools.nasa_eonet import get_nasa_eonet_events
import app.initialize as session_init

try:
    import pandas as pd
    import plotly.express as px
    HAS_VISUALS = True
except ImportError:
    HAS_VISUALS = False

st.set_page_config(page_title="Disaster Chatbot", layout="wide")

session_init.init_session_state()

st.title("🤖 Disaster Chatbot")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        content = msg["content"]
        if isinstance(content, dict):
            st.markdown(content.get("text", ""))
            for visual in content.get("visuals", []):
                if not HAS_VISUALS:
                    st.warning("Install `plotly` and `pandas` to see maps and charts: `pip install plotly pandas`")
                    continue
                if visual["type"] == "map":
                    df = pd.DataFrame(visual["data"])
                    st.map(df)
                elif visual["type"] == "chart":
                    df = pd.DataFrame(visual["data"])
                    fig = px.bar(df, x="Location", y="Approved Funding ($)", 
                                 title="FEMA Approved Funding by Location",
                                 hover_data=["Registrations"])
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown(content)

if prompt := st.chat_input("Help?"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    agent = DisasterAgent(model_id=st.session_state.hf_model_id,
                          api_token=st.session_state.hf_api_key,
                          tools={
                              "get_search": get_search,
                              "get_news_search": get_news_search, 
                              "get_nws_alerts": get_nws_alerts,
                              "get_fema_disaster_declarations": get_fema_disaster_declarations,
                              "get_fema_assistance_data": get_fema_assistance_data,
                              "get_nasa_eonet_events": get_nasa_eonet_events
                          })
    with st.chat_message("assistant"):
        with st.spinner("Consulting disaster databases..."):
            res = agent.get_response(prompt, history=[
                {"role": m["role"], "content": m["content"]["text"] if isinstance(m["content"], dict) else m["content"]}
                for m in st.session_state.messages[:-1]
            ], return_raw=True)
        
        st.markdown(res["text"])
        for visual in res.get("visuals", []):
            if not HAS_VISUALS:
                st.warning("Install `plotly` and `pandas` to see maps and charts: `pip install plotly pandas`")
                break
            if visual["type"] == "map":
                df = pd.DataFrame(visual["data"])
                st.map(df)
            elif visual["type"] == "chart":
                df = pd.DataFrame(visual["data"])
                fig = px.bar(df, x="Location", y="Approved Funding ($)", 
                             title="FEMA Approved Funding by Location",
                             hover_data=["Registrations"])
                st.plotly_chart(fig, use_container_width=True)
                
    st.session_state.messages.append({"role": "assistant", "content": res})