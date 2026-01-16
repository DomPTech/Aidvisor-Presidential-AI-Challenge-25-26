import streamlit as st
from st_supabase_connection import SupabaseConnection
# import wgpu
# import wgpu.utils
import csv
from geopy import distance
import app.initialize as session_init

web_gpu_available = True
# try:
#     # Get default adapter (might be software)
#     adapter = wgpu.utils.get_default_device().adapter
#     print(f"WebGPU Adapter Found: {adapter.info['name']}")
# except Exception as e:
#     print(f"WebGPU not available via wgpu-py: {e}")
#     web_gpu_available = False

st.set_page_config(page_title="Flooding Coordination - Database Chatbot", layout="wide")

session_init.init_session_state()

# Initialize Session State
if "messages_db" not in st.session_state:
    st.session_state.messages_db = []
if "hf_api_key" not in st.session_state:
    st.session_state.hf_api_key = ""

st.title("💾 Database Chatbot")

# Sidebar Configuration
with st.sidebar:
    st.header("Configuration")
    mode = st.radio("Execution Mode", ["Heuristics", "Local (WebGPU)"], index=0)
    
    if mode == "Heuristics":
        st.info("Heuristics Mode: Coming soon.")
    else:
        st.info("Local Mode: Runs entirely in your browser using WebGPU. Privacy-focused and free.")
        st.warning("Requires a high-performance GPU and a compatible browser (e.g., Chrome/Edge 113+).")

conn = st.connection("supabase", type=SupabaseConnection)

fips_to_coords = {}
with open("data/gis/us_county_latlng_with_state.csv", mode='r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        fips_to_coords[row['fips_code']] = (float(row['lat']), float(row['lng']))

user_response = conn.auth.get_user()
if user_response:
    user = user_response.user
    user_id = user.id
    profile_response = conn.table("profiles").select("*").eq("id", user_id).execute()

# --- HEURISTICS MODE IMPLEMENTATION ---
if mode == "Heuristics":
    users = conn.table("profiles").select("*").neq("id", user_id).execute().data #user id needs to be fixed not defined
    
    user_fips = profile_response.data[0].get('fips_code', 0)
    user_coords = fips_to_coords.get(str(user_fips), 'Unknown')
    st.write(f"Your Coordinates: {user_coords}")
    st.write("")
    radius_km = st.slider("Search Radius (km)", min_value=1, max_value=3000, value=500)

    for user in users:
        fips_code = user.get('fips_code', 0)

        if fips_code:
            coords = fips_to_coords.get(str(fips_code), 'Unknown')

            # Calculate distance
            dist = distance.distance(coords, user_coords).km
            
            # 3. Only display if within the selected radius
            if dist <= radius_km:
                with st.expander(f"{user.get('first_name', '')} {user.get('last_name', '')}"):
                    st.write(f"**Distance:** {dist:.2f} km away")
                    st.write(f"**FIPS:** {fips_code}")
                    st.write(f"**Bio:** {user.get('bio', 'No bio provided.')}")  
                    
                    if st.button("Contact", key=f"contact_{user['id']}"):
                        st.switch_page("pages/5_Groups.py", query_params={"dm_id": user['id']})
                            
    st.info("Heuristics mode is coming soon. Check back later!")


# --- LOCAL MODE IMPLEMENTATION ---
else: # mode == "Local (WebGPU)"
    # Fetch Supabase credentials from secrets
    try:
        sb_url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
        sb_key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
    except Exception as e:
        st.error(f"Supabase secrets not found or invalid structure: {e}. Please check .streamlit/secrets.toml")
        st.stop()
        
    if not web_gpu_available:
        st.text("⚠️ WebGPU is not available on this system via wgpu-py. Please ensure you are using a compatible browser and have a suitable GPU.")
        st.stop()
        
    # We define the HTML/JS component here.
    # Note: We are injecting the Supabase keys directly into the client-side code.
    # accessible to anyone who views the page source. This is generally acceptable for 
    # the 'anon' key (public), but we must ensure the `exec_sql` RPC function in Postgres
    # is secure (readonly) and RLS polices are in place if accessing tables directly.
    
    components_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>WebGPU Chatbot</title>
        <script type="module">
            import {{ CreateMLCEngine }} from "https://esm.run/@mlc-ai/web-llm";
            import {{ createClient }} from "https://esm.run/@supabase/supabase-js";

            // Supabase Configuration
            const SUPABASE_URL = "{sb_url}";
            const SUPABASE_KEY = "{sb_key}";
            const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);
            
            // DOM Elements
            const $ = (selector) => document.querySelector(selector);
            const initBtn = $('#init-btn');
            const status = $('#status');
            const chatInterface = $('#chat-interface');
            const messagesDiv = $('#messages');
            const userInput = $('#user-input');
            const sendBtn = $('#send-btn');
            
            let engine;
            let messages = [];
            
            // System Prompt with Schema
            const SYSTEM_PROMPT = `You are a helpful database assistant.
            You have access to a database with the following tables:
            1. profiles (id, first_name, last_name, location, needs, skills, bio, created_at)

            When a user asks a question, if you need data from the database, you must generate a SQL query.
            IMPORTANT: You can only strictly execute SELECT statements.
            
            If you need to query the database, output the query wrapped in a code block like this:
            \`\`\`sql
            SELECT first_name, bio FROM profiles LIMIT 10;
            \`\`\`
            
            If you have the data or don't need to query, just answer normally.

            The output will be JSON.
            `;

            async function init() {{
                initBtn.addEventListener('click', async () => {{
                    initBtn.disabled = true;
                    status.textContent = "Initializing Web-LLM (Phi-3.5-mini)... check console for details.";
                    
                    try {{
                        // Switching to Phi-3.5-mini (~2.3GB), which is "slightly bigger" and very capable
                        const selectedModel = "Phi-3.5-mini-instruct-q4f16_1-MLC";
                        engine = await CreateMLCEngine(selectedModel, {{
                            initProgressCallback: (report) => {{
                                status.textContent = report.text;
                                console.log(report);
                            }}
                        }});
                        
                        status.textContent = "Model Loaded! Ready to chat.";
                        status.style.color = "green";
                        chatInterface.style.display = 'flex';
                        $('#init-block').style.display = 'none';
                        
                        // Set system prompt
                        messages.push({{ role: "system", content: SYSTEM_PROMPT }});
                        
                    }} catch (err) {{
                        status.textContent = "Error loading model: " + err.message;
                        status.style.color = "red";
                        initBtn.disabled = false;
                    }}
                }});

                sendBtn.addEventListener('click', handleSendMessage);
                userInput.addEventListener('keypress', (e) => {{
                    if (e.key === 'Enter') handleSendMessage();
                }});
            }}
            
            async function handleSendMessage() {{
                const text = userInput.value.trim();
                if (!text) return;
                
                userInput.value = '';
                addMessage('user', text);
                messages.push({{ role: "user", content: text }});
                
                // Show typing indicator
                const loadingId = addMessage('assistant', "Thinking...", true);
                
                try {{
                    // 1. Get initial response from LLM
                    const reply1 = await engine.chat.completions.create({{ messages }});
                    let content1 = reply1.choices[0].message.content;
                    
                    // 2. Check for SQL code block
                    const sqlMatch = content1.match(/```sql\\s*([\\s\\S]*?)\\s*```/);
                    
                    if (sqlMatch) {{
                        // Remove trailing semicolon if present to avoid subquery syntax errors
                        const query = sqlMatch[1].trim().replace(/;$/, '');
                        updateMessage(loadingId, "Executing SQL: " + query + "...");
                        
                        // 3. Execute SQL via Supabase RPC
                        const {{ data, error }} = await supabase.rpc('exec_sql', {{ query: query }});
                        
                        let toolResult = "";
                        if (error) {{
                            toolResult = "Error executing SQL: " + error.message;
                        }} else {{
                            toolResult = "Query Result: " + JSON.stringify(data);
                        }}
                        
                        // 4. Feed result back to LLM
                        messages.push({{ role: "assistant", content: content1 }});
                        messages.push({{ role: "user", content: "Database Output: " + toolResult + "\\n\\nPlease summarize this for me." }});
                        
                        const reply2 = await engine.chat.completions.create({{ messages }});
                        const content2 = reply2.choices[0].message.content;
                        
                        updateMessage(loadingId, content2);
                        messages.push({{ role: "assistant", content: content2 }});
                        
                    }} else {{
                        // No SQL, just show response
                        updateMessage(loadingId, content1);
                        messages.push({{ role: "assistant", content: content1 }});
                    }}
                    
                }} catch (err) {{
                    updateMessage(loadingId, "Error: " + err.message);
                }}
            }}
            
            function addMessage(role, text, isLoading=false) {{
                const div = document.createElement('div');
                div.className = 'message ' + role;
                div.innerHTML = formatText(text); // Basic formatting
                if (isLoading) div.id = "msg-" + Date.now();
                messagesDiv.appendChild(div);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
                return div.id;
            }}
            
            function updateMessage(id, text) {{
                if (!id) return;
                const div = document.getElementById(id);
                if (div) {{
                    div.innerHTML = formatText(text);
                }}
            }}
            
            function formatText(text) {{
                // Simple bolding of SQL for visibility
                return text.replace(/\\n/g, '<br>').replace(/```sql/g, '<b>SQL:</b>').replace(/```/g, '');
            }}

            init();
        </script>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                padding: 2rem;
                background-color: #f8f9fa;
                color: #212529;
                box-sizing: border-box;
            }}
            * {{ box-sizing: border-box; }}
            
            h2 {{ margin-top: 0; }}
            
            #init-block {{
                background: white;
                padding: 2rem;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                max-width: 600px;
                margin: 0 auto;
                text-align: center;
            }}
            
            #init-btn {{
                background-color: #ff4b4b;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 1rem;
                cursor: pointer;
                margin-top: 10px;
            }}
            #init-btn:disabled {{ opacity: 0.6; cursor: not-allowed; }}
            
            #chat-interface {{
                display: none;
                flex-direction: column;
                height: 500px;
                max-width: 800px;
                margin: 0 auto;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            
            #messages {{
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                display: flex;
                flex-direction: column;
                gap: 15px;
            }}
            
            .message {{
                max-width: 80%;
                padding: 12px 16px;
                border-radius: 12px;
                line-height: 1.5;
            }}
            
            .message.user {{
                align-self: flex-end;
                background-color: #ff4b4b;
                color: white;
                border-bottom-right-radius: 2px;
            }}
            
            .message.assistant {{
                align-self: flex-start;
                background-color: #f0f2f6;
                color: #31333f;
                border-bottom-left-radius: 2px;
            }}
            
            .input-area {{
                padding: 20px;
                background: white;
                border-top: 1px solid #dee2e6;
                display: flex;
                gap: 10px;
            }}
            
            #user-input {{
                flex: 1;
                padding: 10px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                font-size: 1rem;
            }}
            
            #send-btn {{
                background-color: #ff4b4b;
                color: white;
                border: none;
                padding: 0 20px;
                border-radius: 4px;
                cursor: pointer;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div id="init-block">
            <h2>🚀 WebGPU Database Chatbot</h2>
            <p>This runs a powerful <b>Phi-3.5-mini</b> model <b>entirely in your browser</b>.</p>
            <p>Your data stays private. No API keys required.</p>
            <p style="font-size: 0.9em; color: #666;">Requires ~2.3GB download on first run & a decent GPU.</p>
            <button id="init-btn">Initialize Model</button>
            <p id="status" style="margin-top: 15px; font-weight: bold;"></p>
        </div>
        
        <div id="chat-interface">
            <div id="messages">
                <div class="message assistant">Hello! I can answer questions about your database. What would you like to know?</div>
            </div>
            <div class="input-area">
                <input type="text" id="user-input" placeholder="Type your question..." autocomplete="off">
                <button id="send-btn">Send</button>
            </div>
        </div>
    </body>
    </html>
    """
    
    st.components.v1.html(components_html, height=800, scrolling=True)


