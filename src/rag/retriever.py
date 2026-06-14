from .embed_catalog import get_chroma_client, get_embedding_function

def retrieve_knowledge(query: str, top_k: int = 3) -> str:
    """
    Search the ChromaDB knowledge base for FAQs and Product Info.
    """
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name="ecombot_kb",
        embedding_function=get_embedding_function(),
    )
    
    # query_texts automatically encodes using the provided embedding_function (ef)
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )
    
    if not results["documents"] or not results["documents"][0]:
        return "No relevant information found in the knowledge base."
        
    return "\n\n".join(results["documents"][0])
