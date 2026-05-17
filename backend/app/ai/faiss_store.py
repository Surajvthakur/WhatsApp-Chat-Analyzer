import faiss
import numpy as np

def create_faiss_index(embeddings: list[list[float]]):
    """
    Creates a temporary FAISS index in memory from a list of embeddings.
    """
    if embeddings is None or len(embeddings) == 0:
        return None
        
    embeddings_array = np.array(embeddings).astype('float32')
    dimension = embeddings_array.shape[1]
    
    # Using L2 distance
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_array)
    
    return index

def search_faiss_index(index, query_embedding: list[float], top_k: int = 5) -> list[int]:
    """
    Searches the FAISS index for the top_k most similar embeddings to the query.
    Returns the indices of the matches.
    """
    if index is None or query_embedding is None or len(query_embedding) == 0:
        return []
        
    query_array = np.array([query_embedding]).astype('float32')
    distances, indices = index.search(query_array, top_k)
    
    return indices[0].tolist()
