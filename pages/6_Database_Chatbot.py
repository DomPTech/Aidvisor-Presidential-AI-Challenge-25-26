import streamlit as st
import json
from openai import OpenAI
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="Flooding Coordination - Database Chatbot", layout="wide")

# Initialize Session State
if "messages_db" not in st.session_state:
    st.session_state.messages_db = []
if "hf_api_key" not in st.session_state:
    st.session_state.hf_api_key = ""

st.title("💾 Database Chatbot")

# Sidebar Configuration
with st.sidebar:
    st.header("Configuration")
    mode = st.radio("Execution Mode", ["Cloud (API)", "Local (WebGPU)"], index=0)
    
    if mode == "Cloud (API)":
        st.info("Cloud Mode: Uses server-side Python and requires an API Key.")
        st.session_state.hf_api_key = st.text_input("HuggingFace API Key", 
                                                    value=st.session_state.hf_api_key, 
                                                    type="password",
                                                    key="db_chat_api_key")
        if not st.session_state.hf_api_key:
            st.warning("Please enter your Hugging Face API Key to use Cloud Mode.")
    else:
        st.info("Local Mode: Runs entirely in your browser using WebGPU. Privacy-focused and free.")
        st.warning("Requires a high-performance GPU and a compatible browser (e.g., Chrome/Edge 113+).")


# --- CLOUD MODE IMPLEMENTATION ---
if mode == "Cloud (API)":
    # Supabase Connection
    try:
        conn = st.connection("supabase", type=SupabaseConnection)
    except Exception as e:
        st.error(f"Failed to connect to Supabase: {e}")
        st.stop()

    def query_database(query: str):
        """
        Executes a read-only SQL query on the Supabase database using the 'exec_sql' RPC function.
        """
        try:
            # Basic client-side safety check (the RPC function should also have checks)
            if not query.strip().lower().startswith("select"):
                 return "Error: Only SELECT queries are allowed for safety."
            
            response = conn.query("*", ttl=0).rpc("exec_sql", {"query": query}).execute()
            return json.dumps(response.data, indent=2)
        except Exception as e:
            return f"Error executing query: {str(e)}"

    class DatabaseAgent:
        def __init__(self, api_key):
             self.client = OpenAI(
                base_url="https://router.huggingface.co/v1",
                api_key=api_key
            )
             self.model_id = "deepseek-ai/DeepSeek-R1" # Hardcoded for now, could be dynamic

        def get_response(self, user_input, history):
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "query_database",
                        "description": "Execute a SQL query to retrieve data from the database. The database has tables: 'profiles' (id, first_name, last_name, role), 'messages' (id, user_id, message_text, created_at), 'direct_messages' (id, sender_id, recipient_id, message_text, created_at).",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The SQL SELECT query to execute."
                                }
                            },
                            "required": ["query"]
                        }
                    }
                }
            ]

            messages = [{"role": "system", "content": "You are a database assistant. Use the 'query_database' tool to answer user questions about the data. Always output valid SQL."}]
            messages.extend(history)
            messages.append({"role": "user", "content": user_input})

            try:
                completion = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    max_tokens=600
                )
                
                msg = completion.choices[0].message
                
                if msg.tool_calls:
                    messages.append(msg) # Add tool call to history
                    for tool_call in msg.tool_calls:
                         if tool_call.function.name == "query_database":
                            args = json.loads(tool_call.function.arguments)
                            result = query_database(args["query"])
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": "query_database",
                                "content": result
                            })
                    
                    # Get final response
                    final = self.client.chat.completions.create(
                        model=self.model_id,
                        messages=messages,
                        max_tokens=600
                    )
                    return final.choices[0].message.content
                
                return msg.content

            except Exception as e:
                return f"Error: {str(e)}"

    # Chat UI
    for msg in st.session_state.messages_db:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about the database..."):
        if not st.session_state.hf_api_key:
            st.error("Please provide an API Key in the sidebar.")
        else:
            st.chat_message("user").markdown(prompt)
            st.session_state.messages_db.append({"role": "user", "content": prompt})

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    agent = DatabaseAgent(st.session_state.hf_api_key)
                    response = agent.get_response(prompt, st.session_state.messages_db[:-1])
                    st.markdown(response)
            
            st.session_state.messages_db.append({"role": "assistant", "content": response})


# --- LOCAL MODE IMPLEMENTATION ---
else: # mode == "Local (WebGPU)"
    # Fetch Supabase credentials from secrets
    try:
        sb_url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
        sb_key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
    except Exception as e:
        st.error(f"Supabase secrets not found or invalid structure: {e}. Please check .streamlit/secrets.toml")
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
            1. profiles (id, first_name, last_name, location, resource_needed, status, bio, created_at)

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


