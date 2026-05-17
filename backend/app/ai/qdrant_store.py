import uuid
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from app.config import settings
from app.ai.chunking import get_chunks_metadata
import pandas as pd

logger = logging.getLogger(__name__)

COLLECTION_NAME = "whatsapp_chats"
_client = None

def get_qdrant_client():
    global _client
    if _client is None:
        logger.info(f"Initializing Qdrant client at URL: {settings.qdrant_url}")
        # Add timeout to prevent hangs
        _client = QdrantClient(url=settings.qdrant_url, timeout=10.0)
    return _client

def init_collection():
    """
    Initializes the Qdrant collection if it does not already exist.
    """
    try:
        client = get_qdrant_client()
        # Check if collection exists
        if not client.collection_exists(COLLECTION_NAME):
            logger.info(f"Creating Qdrant collection: {COLLECTION_NAME}")
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=384,  # Dimension for SentenceTransformer 'all-MiniLM-L6-v2'
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Qdrant collection {COLLECTION_NAME} created successfully.")
        else:
            logger.debug(f"Qdrant collection {COLLECTION_NAME} already exists.")
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant collection: {e}")
        # Do not raise to keep the app working if Qdrant is temporarily down
        pass

def save_workspace_embeddings(workspace_id: str, chunks: list[str], embeddings: list[list[float]], df: pd.DataFrame) -> bool:
    """
    Saves a list of chunks and their corresponding embeddings into Qdrant.
    It builds a payload for each chunk containing chunk metadata:
    - workspace_id
    - chunk_id
    - text
    - speaker
    - timestamp_range
    """
    try:
        init_collection()
        client = get_qdrant_client()
        
        # 1. Get structured metadata from df
        metadata_list = get_chunks_metadata(df)
        
        # Ensure we have metadata matching the number of chunks/embeddings
        # Fall back to sequential text matching if there's any discrepancy
        num_items = min(len(chunks), len(embeddings))
        
        points = []
        for i in range(num_items):
            chunk_text = chunks[i]
            embedding = embeddings[i]
            
            # Find the corresponding metadata if available, otherwise build fallback
            meta = metadata_list[i] if i < len(metadata_list) else {
                "text": chunk_text,
                "speaker": "Unknown",
                "timestamp_range": "Unknown"
            }
            
            # Ensure workspace_id is set
            payload = {
                "workspace_id": workspace_id,
                "chunk_id": f"{workspace_id}_{i}",
                "text": meta.get("text", chunk_text),
                "speaker": meta.get("speaker", "Unknown"),
                "timestamp_range": meta.get("timestamp_range", "Unknown")
            }
            
            # Generate a deterministic UUID based on workspace_id and chunk index
            # This makes the save operation idempotent (re-saving overwrites existing instead of duplicating)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{workspace_id}_{i}"))
            
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
            )
            
        if points:
            logger.info(f"Upserting {len(points)} points into Qdrant for workspace {workspace_id}...")
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )
            logger.info(f"Successfully saved {len(points)} embeddings in Qdrant for workspace {workspace_id}.")
            return True
            
        return False
    except Exception as e:
        logger.error(f"Error saving embeddings to Qdrant: {e}", exc_info=True)
        return False

def search_qdrant_embeddings(workspace_id: str, query_embedding: list[float], top_k: int = 5) -> list[str]:
    """
    Queries Qdrant for the query_embedding, filtered by workspace_id.
    Returns the matching chunk text values.
    """
    try:
        client = get_qdrant_client()
        
        # Query filter to only search within this workspace
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="workspace_id",
                    match=MatchValue(value=workspace_id)
                )
            ]
        )
        
        logger.debug(f"Searching Qdrant collection '{COLLECTION_NAME}' for workspace '{workspace_id}'...")
        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=top_k
        )
        
        retrieved_chunks = []
        for hit in results:
            if hit.payload and "text" in hit.payload:
                retrieved_chunks.append(hit.payload["text"])
                
        logger.info(f"Retrieved {len(retrieved_chunks)} relevant chunks from Qdrant for workspace {workspace_id}.")
        return retrieved_chunks
    except Exception as e:
        logger.error(f"Error querying Qdrant: {e}")
        return []

def delete_workspace_embeddings(workspace_id: str) -> bool:
    """
    Deletes all vector points associated with the given workspace_id from Qdrant.
    """
    try:
        client = get_qdrant_client()
        logger.info(f"Deleting embeddings in Qdrant for workspace {workspace_id}...")
        
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="workspace_id",
                        match=MatchValue(value=workspace_id)
                    )
                ]
            )
        )
        logger.info(f"Successfully deleted Qdrant embeddings for workspace {workspace_id}.")
        return True
    except Exception as e:
        logger.error(f"Error deleting Qdrant embeddings for workspace {workspace_id}: {e}")
        return False
