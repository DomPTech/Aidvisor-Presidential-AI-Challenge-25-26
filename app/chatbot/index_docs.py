import os
import sys

# Add the project root to sys.path so we can import app.chatbot.rag_utils
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from app.chatbot.rag_utils import index_documents

if __name__ == "__main__":
    kb_path = os.path.join(project_root, "data", "knowledge_base")
    if not os.path.exists(kb_path):
        print(f"Error: Knowledge base path {kb_path} does not exist.")
        sys.exit(1)
        
    print(f"Indexing documents from {kb_path}...")
    result = index_documents(kb_path)
    print(result)
    print("Vector store cached in data/chroma_db")
