import numpy as np

def create_faiss_index(embeddings: list[list[float]]):
    """
    Creates a temporary index (numpy array) in memory from a list of embeddings.
    This replaces FAISS with pure NumPy to avoid installing heavy C++ binaries.
    """
    if embeddings is None or len(embeddings) == 0:
        return None
        
    # Just convert and return the embeddings as a float32 numpy array
    return np.array(embeddings).astype('float32')

def search_faiss_index(index, query_embedding: list[float], top_k: int = 5) -> list[int]:
    """
    Searches the in-memory numpy array for the top_k most similar embeddings to the query
    using Euclidean (L2) distance, maintaining compatibility with the FAISS IndexFlatL2 API.
    Returns the indices of the matches.
    """
    if index is None or query_embedding is None or len(query_embedding) == 0:
        return []
        
    # index shape: (num_embeddings, dimension)
    # query_array shape: (dimension,)
    query_array = np.array(query_embedding).astype('float32')
    
    # Calculate squared L2 distance: sum((embedding - query) ** 2) for each embedding
    distances = np.sum((index - query_array) ** 2, axis=1)
    
    # Sort distances ascending (smallest distance first) and get the top_k indices
    top_indices = np.argsort(distances)[:top_k]
    
    return top_indices.tolist()
