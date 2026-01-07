import os
from openai import OpenAI
import json

class DisasterAgent:
    def __init__(self, model_id="deepseek-ai/DeepSeek-R1", api_token=None, tools=None):
        """
        Initialize the HuggingFace Chatbot using the OpenAI client.
        
        Args:
            model_id (str): The HuggingFace model ID to use. 
                            Defaults to 'deepseek-ai/DeepSeek-R1-0528'.
            api_token (str): Optional HuggingFace API token.
            tools (dict): Optional dictionary of tool functions. 
                          Format: {"tool_name": function_reference}
        """
        self.model_id = model_id
        self.tools = tools or {}
        
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

    def get_response(self, user_input, history=None):
        """
        Generate a response from the chatbot.
        
        Args:
            user_input (str): The user's message.
            history (list): List of previous messages (optional, for context).
                            Format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        
        Returns:
            str: The chatbot's response.
        """
        if not self.client:
            return "Error: API Token is missing. Please provide a HuggingFace API Token."

        # Construct messages list
        messages = []
        
        # System prompt
        system_prompt = (
            "You are a helpful assistant that helps identify areas of most need during natural disaster events. "
            "You are an expert in disaster coordination, volunteering, and donation logistics. "
            "IMPORTANT: Always search for data using the provided tools (OpenFEMA, Google News, NWS Alerts) "
            "before making claims about specific community needs or disaster status. "
            "If you do not have data from a tool for a specific inquiry about a location's needs, "
            "clearly state that you don't have that information instead of speculating or fabricating needs. "
            "Keep answers concise, structured, and helpful."
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
                    "name": "get_google_news",
                    "description": "Get recent flash flood news for a specific location or search query.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query or location to search for news (e.g., 'Nashville flood')."
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
            }
        ]
        
        try:
            # First API call
            completion = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                tools=tools_schema,
                tool_choice="auto",
                max_tokens=500,
            )
            
            response_message = completion.choices[0].message
            
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
                        try:
                            tool_result = tool_func(**function_args)
                        except Exception as tool_err:
                            tool_result = f"Error executing tool: {str(tool_err)}"
                        
                        # Add tool result to messages
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": str(tool_result),
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
                    max_tokens=600,
                )
                return self._clean_response(final_completion.choices[0].message.content)
            
            return self._clean_response(response_message.content)

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
    from app.chatbot.tools.google_news import get_google_news
    from app.chatbot.tools.nws_alerts import get_nws_alerts
    
    test_tools = {
        "get_google_news": get_google_news,
        "get_nws_alerts": get_nws_alerts
    }
    
    bot = DisasterAgent(tools=test_tools)
    print(bot.get_response("Are there any weather alerts for Nashville (36.16, -86.78)?"))
    print(bot.get_response("What is the latest news on floods in Tennessee?"))
