import os
from openai import OpenAI
import json

class DisasterAgent:
    def __init__(self, model_id="deepseek-ai/DeepSeek-R1-0528", api_token=None, tools=None):
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
            "You are a helpful assistant for a Flash Flood Prediction Application. "
            "The app helps users check flood probability at USGS sites based on streamflow data. "
            "Answer questions about floods, safety, and how to interpret risk levels (Low < 30%, Moderate < 70%, High >= 70%). "
            "Keep answers concise and helpful."
        )
        messages.append({"role": "system", "content": system_prompt})
        
        # History
        if history:
            # Ensure history format matches OpenAI expectations (role/content)
            messages.extend(history)
        
        # Current user input
        messages.append({"role": "user", "content": user_input})
        
        # Define tools schema
        # We only have one tool for now, but we can expand this
        tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": "get_flood_probability",
                    "description": "Get the probability of a flood for a specific location.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "site_code": {
                                "type": "string",
                                "description": "The USGS site code (e.g., '03432400')."
                            },
                            "lat": {
                                "type": "number",
                                "description": "Latitude of the location."
                            },
                            "lon": {
                                "type": "number",
                                "description": "Longitude of the location."
                            },
                            "site_name": {
                                "type": "string",
                                "description": "Name of the site or location."
                            }
                        },
                        "required": [] 
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_flood_news",
                    "description": "Get recent flash flood news for a specific location.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location_query": {
                                "type": "string",
                                "description": "The location to search for news (e.g., 'Nashville, TN')."
                            }
                        },
                        "required": ["location_query"] 
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
                    function_args = json.loads(tool_call.function.arguments)
                    
                    if function_name in self.tools:
                        # Execute tool
                        tool_func = self.tools[function_name]
                        tool_result = tool_func(**function_args)
                        
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
                    max_tokens=500,
                )
                return self._clean_response(final_completion.choices[0].message.content)
            
            return self._clean_response(response_message.content)

        except Exception as e:
            return f"Error connecting to chatbot: {str(e)}"

    def _clean_response(self, content):
        """
        Remove <think>...</think> tags from the response content.
        """
        if not content:
            return ""
        import re
        # Remove <think>...</think> blocks, including newlines
        cleaned_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        return cleaned_content.strip()

if __name__ == "__main__":
    # Simple test
    # Ensure HF_TOKEN is set in env for this test to work
    bot = HuggingFaceChatbot()
    print(bot.get_response("What is a flash flood?"))
