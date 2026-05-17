from sentence_transformers import SentenceTransformer

# Load model lazily to avoid loading it on import if not needed
_model = None

def get_embedding_model():
    global _model
    if _model is None:
        # all-MiniLM-L6-v2 is fast, lightweight, and good quality
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generates embeddings for a list of text strings.
    """
    if not texts:
        return []
        
    model = get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings
