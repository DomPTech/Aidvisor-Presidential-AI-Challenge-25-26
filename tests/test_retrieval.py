from app.chatbot.rag_utils import query_vector_store
import os

def test_retrieval_logic():
    print("Testing basic RAG retrieval logic...")
    
    query1 = "2025 disaster trends"
    print(f"\nQuery: {query1}")
    result1 = query_vector_store(query1)
    print(f"Result:\n{result1}")
    
    query2 = "family emergency preparedness checklist"
    print(f"\nQuery: {query2}")
    result2 = query_vector_store(query2)
    print(f"Result:\n{result2}")

if __name__ == "__main__":
    test_retrieval_logic()
