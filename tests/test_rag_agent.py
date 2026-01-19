from app.chatbot.chatbot import DisasterAgent
import os

def test_rag_retrieval():
    print("Testing RAG retrieval tool integration...")
    bot = DisasterAgent()
    
    # Test queries that should trigger RAG
    print("\nQuery 1: What are the disaster trends for 2025-2026?")
    response1 = bot.get_response("What are the major natural disaster trends and challenges for 2025-2026?")
    print(f"Response 1: {response1}")
    
    print("\nQuery 2: How should I prepare my family for an emergency?")
    response2 = bot.get_response("Give me a checklist for family emergency preparedness in 2025.")
    print(f"Response 2: {response2}")

if __name__ == "__main__":
    if not os.environ.get("HF_TOKEN") and not os.environ.get("HUGGINGFACEHUB_API_TOKEN"):
        print("Warning: HF_TOKEN not found. Response might be an error message.")
    
    test_rag_retrieval()
