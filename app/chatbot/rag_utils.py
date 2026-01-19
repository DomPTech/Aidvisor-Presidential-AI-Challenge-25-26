import chromadb
import os
import glob
from chromadb.utils import embedding_functions

# Path for persistent storage
DB_PATH = os.path.join(os.getcwd(), "data", "chroma_db")
COLLECTION_NAME = "disaster_knowledge"

def get_chroma_client():
    """Initialize and return a persistent ChromaDB client."""
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH, exist_ok=True)
    return chromadb.PersistentClient(path=DB_PATH)

def get_collection():
    """Get or create the disaster knowledge collection."""
    client = get_chroma_client()
    # Using default embedding function (all-MiniLM-L6-v2)
    return client.get_or_create_collection(name=COLLECTION_NAME)

def index_documents(kb_path):
    """
    Read markdown files from kb_path and add them to the collection.
    Only adds if the content has changed (using simple ID mapping).
    """
    collection = get_collection()
    files = glob.glob(os.path.join(kb_path, "*.md"))
    
    documents = []
    metadatas = []
    ids = []
    
    for file_path in files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            filename = os.path.basename(file_path)
            
            # For simplicity, we use filename as ID. 
            # In a production app, we might chunk larger documents.
            documents.append(content)
            metadatas.append({"source": filename})
            ids.append(filename)
            
    if documents:
        # chroma handles updates if IDs already exist
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        return f"Indexed {len(documents)} documents."
    return "No documents found to index."

def query_vector_store(query, n_results=3):
    """Query the collection for relevant context."""
    collection = get_collection()
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    # Format results for the chatbot
    context_bits = []
    if results['documents'] and results['documents'][0]:
        for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
            source = meta.get("source", "Unknown")
            context_bits.append(f"--- Context from {source} ---\n{doc}")
            
    return "\n\n".join(context_bits) if context_bits else "No relevant context found in knowledge base."
