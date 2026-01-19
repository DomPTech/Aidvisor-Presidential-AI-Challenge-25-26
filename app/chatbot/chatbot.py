import os
from openai import OpenAI
import json
from datetime import date

class DisasterAgent:
    def __init__(self, model_id="Qwen/Qwen3-8B:nscale", api_token=None, tools=None):
        """
        Initialize the HuggingFace Chatbot using the OpenAI client.
        
        Args:
            model_id (str): The HuggingFace model ID to use. 
                            Defaults to 'Qwen/Qwen3-8B-Instruct'.
            api_token (str): Optional HuggingFace API token.
            tools (dict): Optional dictionary of tool functions. 
                          Format: {"tool_name": function_reference}
        """
        self.model_id = model_id
        self.tools = tools or {}
        
        # Add RAG tool by default
        if "get_rag_context" not in self.tools:
            try:
                from app.chatbot.rag_utils import query_vector_store
                self.tools["get_rag_context"] = query_vector_store
            except ImportError:
                print("Warning: Could not import rag_utils. RAG tool will not be available.")
        
        # Use provided token or fall back to environment variable
        token = api_token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
        
        if not token:
            # We can't initialize the client properly without a token for this endpoint
            self.client = None
        else:
            self.client = OpenAI(
                base_url="https://router.huggingface.co/v1",
                api_key=token,
            )

    def get_response(self, user_input, history=None, return_raw=False):
        """
        Generate a response from the chatbot.
        
        Args:
            user_input (str): The user's message.
            history (list): List of previous messages (optional, for context).
                            Format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            return_raw (bool): If True, return a dict with {"text": ..., "visuals": ...}.
                               If False, return only the text str.
        
        Returns:
            str|dict: The chatbot's response.
        """
        if not self.client:
            return "Error: API Token is missing. Please provide a HuggingFace API Token."

        # Construct messages list
        messages = []
        
        # System prompt
        system_prompt = (
            "You are a helpful assistant that helps identify areas of most need during natural disaster events. "
            "You are an expert in disaster coordination, volunteering, and donation logistics. "
            "IMPORTANT: Always search for up-to-date data using the provided tools (RAG Knowledge Base, OpenFEMA, DuckDuckGo Search, NWS Alerts) "
            "before making claims about specific community needs, disaster status, or preparedness protocols. "
            "Use the 'get_rag_context' tool specifically for 2025-2026 preparedness guides, emergency protocols, and general disaster trends. "
            "If you do not have data from a tool for a specific inquiry about a location's needs or a protocol, "
            "clearly state that you don't have that information instead of speculating or fabricating needs. "
            "Keep answers concise, structured, and helpful."
            f"The year is {date.today().year}."
        )
        messages.append({"role": "system", "content": system_prompt})
        
        # History
        if history:
            # Ensure history format matches OpenAI expectations (role/content)
            messages.extend(history)
        
        # Current user input
        messages.append({"role": "user", "content": user_input})
        
        # Define tools schema
        tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": "post_disaster_alert",
                    "description": "Post a verified disaster alert to the public Bounty Board for volunteers to see.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "Location of the event (e.g., 'Miami, FL')."
                            },
                            "summary": {
                                "type": "string",
                                "description": "Brief summary of the need or threat."
                            },
                            "severity": {
                                "type": "integer",
                                "description": "Severity level from 1 to 10."
                            },
                            "disaster_type": {
                                "type": "string",
                                "description": "Type: 'Flood', 'Hurricane', 'Fire', 'Earthquake', etc."
                            }
                        },
                        "required": ["location", "summary", "severity"] 
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_search",
                    "description": "General web search using DuckDuckGo.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query."
                            }
                        },
                        "required": ["query"] 
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_news_search",
                    "description": "Search DuckDuckGo News for recent news and information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query (e.g., 'Nashville flood news')."
                            }
                        },
                        "required": ["query"] 
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_nws_alerts",
                    "description": "Get active weather alerts from the National Weather Service for a specific latitude and longitude.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "lat": {
                                "type": "number",
                                "description": "Latitude of the location."
                            },
                            "lon": {
                                "type": "number",
                                "description": "Longitude of the location."
                            }
                        },
                        "required": ["lat", "lon"] 
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_rag_context",
                    "description": "Get up-to-date (2025-2026) information on natural disaster preparedness, emergency protocols, and disaster trends from the knowledge base.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The specific preparedness topic or disaster trend to search for."
                            }
                        },
                        "required": ["query"] 
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_fema_disaster_declarations",
                    "description": "Get recent FEMA disaster declarations for a specific state and optionally a county.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "state": {
                                "type": "string",
                                "description": "The two-letter state abbreviation (e.g., 'TN')."
                            },
                            "county": {
                                "type": "string",
                                "description": "The county name (e.g., 'Davidson')."
                            },
                            "days": {
                                "type": "integer",
                                "description": "Number of days to look back (default is 365)."
                            }
                        },
                        "required": ["state"] 
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_fema_assistance_data",
                    "description": "Get summary data for FEMA Individual Assistance approved in a state/county to gauge community need.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "state": {
                                "type": "string",
                                "description": "The two-letter state abbreviation (e.g., 'TN')."
                            },
                            "county": {
                                "type": "string",
                                "description": "The county name (e.g., 'Davidson')."
                            }
                        },
                        "required": ["state"] 
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_nasa_eonet_events",
                    "description": "Get recent natural events (wildfires, storms, volcanoes, etc.) from NASA EONET.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of events to return (default is 10)."
                            },
                            "days": {
                                "type": "integer",
                                "description": "Number of days to look back (default is 20)."
                            },
                            "status": {
                                "type": "string",
                                "description": "Status of events to return: 'open' or 'closed' (default is 'open')."
                            }
                        }
                    }
                }
            }
        ]
        
        try:
            # First API call
            completion = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                tools=tools_schema,
                tool_choice="auto",
                max_tokens=2000,
            )
            
            response_message = completion.choices[0].message
            collected_visuals = []
            
            # Check if the model wants to call a tool
            if response_message.tool_calls:
                # Add the assistant's response (with tool calls) to history
                messages.append(response_message)
                
                # Process each tool call
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    raw_args = tool_call.function.arguments
                    
                    try:
                        function_args = self._safe_json_loads(raw_args)
                    except Exception as json_err:
                        print(f"Error parsing tool arguments for {function_name}: {json_err}")
                        print(f"Raw arguments: {raw_args}")
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": f"Error: Invalid JSON arguments returned by model for tool '{function_name}'.",
                        })
                        continue

                    if function_name in self.tools:
                        # Execute tool
                        tool_func = self.tools[function_name]
                        print(f"🤖 AI calling tool: {function_name} with args: {function_args}")
                        try:
                            tool_result = tool_func(**function_args)
                            print(f"✅ Tool {function_name} returned data.")
                        except Exception as tool_err:
                            tool_result = f"Error executing tool: {str(tool_err)}"
                            print(f"❌ Tool {function_name} error: {tool_err}")
                        
                        # Handle structured results for visualizations
                        if isinstance(tool_result, dict):
                            summary = tool_result.get("summary", str(tool_result))
                            visual = tool_result.get("visuals")
                            if visual:
                                collected_visuals.append(visual)
                            tool_content = summary
                        else:
                            tool_content = str(tool_result)

                        # Add tool result to messages
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": tool_content,
                        })
                    else:
                        # Handle unknown tool
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": f"Error: Tool '{function_name}' not found.",
                        })
                
                # Second API call to get the final response
                final_completion = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=messages,
                    max_tokens=3000,
                )
                final_text = self._clean_response(final_completion.choices[0].message.content)
                if return_raw:
                    return {"text": final_text, "visuals": collected_visuals}
                return final_text
            
            final_text = self._clean_response(response_message.content)
            if return_raw:
                return {"text": final_text, "visuals": []}
            return final_text

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Error connecting to chatbot: {str(e)}"

    def _safe_json_loads(self, s):
        """
        Attempt to parse JSON while handling potential extra data from reasoning models.
        """
        if not s:
            return {}
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            # Common issue with reasoning models: JSON followed by <think> or other text
            import re
            # Extract anything between the first { and the last }
            match = re.search(r'(\{.*\})', s, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except:
                    pass
            raise

    def _clean_response(self, content):
        """
        Remove <think>...</think> tags and clean up the response.
        """
        if not content:
            return ""
        import re
        # Remove reasoning blocks
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        return content.strip()

if __name__ == "__main__":
    # Test with tools
    from app.chatbot.tools.ddg_search import get_search, get_news_search
    from app.chatbot.tools.nws_alerts import get_nws_alerts
    from app.chatbot.tools.bounty_tools import post_disaster_alert
    
    test_tools = {
        "post_disaster_alert": post_disaster_alert,
        "get_search": get_search,
        "get_news_search": get_news_search,
        "get_nws_alerts": get_nws_alerts
    }
    
    bot = DisasterAgent(tools=test_tools)
    print(bot.get_response("Are there any weather alerts for Nashville (36.16, -86.78)?"))
    print(bot.get_response("What is the latest news on floods in Tennessee?"))
