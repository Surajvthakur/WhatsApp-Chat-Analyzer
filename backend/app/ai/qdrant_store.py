import uuid
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType,
)
from app.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "whatsapp_chats"
_client = None


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        logger.info(f"Initializing Qdrant client at URL: {settings.qdrant_url}")
        _client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key if settings.qdrant_api_key else None,
            timeout=10.0,
        )
    return _client


def init_collection():
    """
    Creates the Qdrant collection and a payload index on 'workspace_id'
    if they do not already exist.
    """
    try:
        client = get_qdrant_client()

        if not client.collection_exists(COLLECTION_NAME):
            logger.info(f"Creating Qdrant collection: {COLLECTION_NAME}")
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=settings.embedding_dimension,
                    distance=Distance.COSINE,
                ),
            )
            # Payload index makes filtered searches O(1) instead of full scans
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="workspace_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            logger.info(f"Qdrant collection '{COLLECTION_NAME}' created with payload index.")
        else:
            logger.debug(f"Qdrant collection '{COLLECTION_NAME}' already exists.")
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant collection: {e}")


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

def has_embeddings(session_id: str) -> bool:
    """
    Returns True if Qdrant already contains at least one point
    for the given session_id (used as workspace_id in the payload).
    """
    try:
        client = get_qdrant_client()
        results = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="workspace_id",
                        match=MatchValue(value=session_id),
                    )
                ]
            ),
            limit=1,
            with_payload=False,
            with_vectors=False,
        )
        points, _ = results
        return len(points) > 0
    except Exception as e:
        logger.error(f"Error checking embeddings in Qdrant for {session_id}: {e}")
        return False


def search_qdrant_embeddings(
    workspace_id: str,
    query_embedding: list[float],
    top_k: int = 5,
) -> list[str]:
    """
    Queries Qdrant for the top-k most similar chunks filtered by workspace_id.
    Returns the matching chunk text values.
    """
    try:
        client = get_qdrant_client()
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="workspace_id",
                    match=MatchValue(value=workspace_id),
                )
            ]
        )

        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=top_k,
        )

        retrieved_chunks = [
            hit.payload["text"]
            for hit in results
            if hit.payload and "text" in hit.payload
        ]
        logger.info(
            f"Retrieved {len(retrieved_chunks)} chunks from Qdrant "
            f"for workspace '{workspace_id}'."
        )
        return retrieved_chunks
    except Exception as e:
        logger.error(f"Error querying Qdrant: {e}")
        return []


# ---------------------------------------------------------------------------
# Write / delete helpers
# ---------------------------------------------------------------------------

def save_embeddings(
    session_id: str,
    chunks: list[str],
    embeddings: list[list[float]],
    metadata_list: list[dict] | None = None,
) -> bool:
    """
    Upserts chunks and their embeddings into Qdrant under the given session_id.
    Optionally accepts pre-computed metadata (speaker, timestamp_range) per chunk.
    """
    try:
        init_collection()
        client = get_qdrant_client()

        num_items = min(len(chunks), len(embeddings))
        if num_items == 0:
            return False

        points = []
        for i in range(num_items):
            meta = (metadata_list[i] if metadata_list and i < len(metadata_list)
                    else {"text": chunks[i], "speaker": "Unknown", "timestamp_range": "Unknown"})

            payload = {
                "workspace_id": session_id,
                "chunk_id": f"{session_id}_{i}",
                "text": meta.get("text", chunks[i]),
                "speaker": meta.get("speaker", "Unknown"),
                "timestamp_range": meta.get("timestamp_range", "Unknown"),
            }

            # Deterministic UUID → idempotent upserts
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{session_id}_{i}"))

            points.append(
                PointStruct(id=point_id, vector=embeddings[i], payload=payload)
            )

        logger.info(f"Upserting {len(points)} points into Qdrant for session '{session_id}'...")
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        logger.info(f"Successfully saved {len(points)} embeddings for session '{session_id}'.")
        return True
    except Exception as e:
        logger.error(f"Error saving embeddings to Qdrant: {e}", exc_info=True)
        return False


def delete_workspace_embeddings(workspace_id: str) -> bool:
    """
    Deletes all vector points associated with the given workspace_id from Qdrant.
    """
    try:
        client = get_qdrant_client()
        logger.info(f"Deleting embeddings in Qdrant for '{workspace_id}'...")
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="workspace_id",
                        match=MatchValue(value=workspace_id),
                    )
                ]
            ),
        )
        logger.info(f"Successfully deleted Qdrant embeddings for '{workspace_id}'.")
        return True
    except Exception as e:
        logger.error(f"Error deleting Qdrant embeddings for '{workspace_id}': {e}")
        return False
