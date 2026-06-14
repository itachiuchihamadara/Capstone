import json
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

CHROMA_DB_PATH = Path(__file__).parent / ".chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_embedding_function = None


def get_embedding_function():
    global _embedding_function
    if _embedding_function is None:
        _embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
    return _embedding_function

def get_chroma_client():
    return chromadb.PersistentClient(path=str(CHROMA_DB_PATH))

def load_data():
    data_dir = Path(__file__).parent / "data"
    
    with open(data_dir / "products.json", "r") as f:
        products = json.load(f)
        
    with open(data_dir / "faq.json", "r") as f:
        faqs = json.load(f)
        
    return products, faqs

def embed_catalog():
    print(f"Embedding catalog and FAQs using {EMBEDDING_MODEL}...")
    client = get_chroma_client()
    embedding_function = get_embedding_function()
    
    # Create or get collection with the local embedding function
    collection = client.get_or_create_collection(name="ecombot_kb", embedding_function=embedding_function)
    
    products, faqs = load_data()
    
    docs = []
    ids = []
    metadatas = []
    
    for prod in products:
        docs.append(f"Product: {prod['name']} | Category: {prod['category']} | Price: ₹{prod['price']} | Specs: {prod['specs']} | Warranty: {prod['warranty']}")
        ids.append(prod['id'])
        metadatas.append({"type": "product", "name": prod['name']})
        
    for faq in faqs:
        docs.append(f"FAQ Q: {faq['question']} | A: {faq['answer']}")
        ids.append(faq['id'])
        metadatas.append({"type": "faq"})
        
    # Upsert - embeddings are generated automatically by Chroma
    collection.upsert(
        ids=ids,
        documents=docs,
        metadatas=metadatas
    )
    print("Done embedding into ChromaDB.")

if __name__ == "__main__":
    embed_catalog()
