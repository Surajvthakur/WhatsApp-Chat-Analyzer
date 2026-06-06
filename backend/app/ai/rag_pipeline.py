import logging

from groq import Groq

from app.config import settings
from app.ai.chunking import chunk_chat_data, get_chunks_metadata
from app.ai.embeddings import generate_embeddings
from app.ai.qdrant_store import (
    has_embeddings,
    save_embeddings,
    search_qdrant_embeddings,
    delete_workspace_embeddings,
)

import pandas as pd

logger = logging.getLogger(__name__)


def ingest_chat(session_id: str, df: pd.DataFrame) -> bool:
    """
    Ensures embeddings exist in Qdrant for the given session.
    If they already exist, returns immediately (cache hit).
    Otherwise chunks the chat, generates embeddings via Ollama,
    and persists them to Qdrant.
    """
    # Fast path: embeddings already stored in Qdrant
    if has_embeddings(session_id):
        logger.info(f"Embeddings already exist in Qdrant for '{session_id}'. Skipping ingestion.")
        return True

    logger.info(f"Ingesting chat for session '{session_id}'...")
    chunks = chunk_chat_data(df)
    if not chunks:
        logger.warning(f"No chunks generated for session '{session_id}'.")
        return False

    metadata_list = get_chunks_metadata(df)
    embeddings = generate_embeddings(chunks)

    success = save_embeddings(
        session_id=session_id,
        chunks=chunks,
        embeddings=embeddings,
        metadata_list=metadata_list,
    )

    if success:
        logger.info(f"Ingestion complete for '{session_id}'. Stored {len(chunks)} chunks in Qdrant.")
    else:
        logger.error(f"Failed to save embeddings to Qdrant for '{session_id}'.")

    return success


def query_chat(session_id: str, question: str) -> str:
    """
    Embeds the question, retrieves the most relevant chunks from Qdrant,
    and generates an answer using the Groq LLM.
    """
    # 1. Embed the question
    question_embedding = generate_embeddings([question])[0]
    if hasattr(question_embedding, "tolist"):
        question_embedding = question_embedding.tolist()

    # 2. Search Qdrant
    retrieved_chunks = search_qdrant_embeddings(session_id, question_embedding, top_k=5)

    if not retrieved_chunks:
        return "Could not find relevant information in the chat."

    context = "\n\n".join(retrieved_chunks)

    # 3. Ask Groq
    if not settings.groq_api_key:
        return "GROQ API Key is not configured on the server."

    try:
        client = Groq(api_key=settings.groq_api_key)

        prompt = f"""You are a helpful AI assistant analyzing a WhatsApp chat export.
Answer the user's question based ONLY on the provided chat context. If the answer is not in the context, say so. Do not invent information.

CONTEXT:
{context}

QUESTION:
{question}
"""

        completion = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant analyzing WhatsApp chat logs.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.2,
            max_tokens=1024,
        )

        return completion.choices[0].message.content

    except Exception as e:
        logger.error(f"Error calling Groq API: {e}")
        return f"Sorry, there was an error communicating with the AI provider: {str(e)}"


def delete_session(session_id: str):
    """
    Deletes all embeddings for the session from Qdrant.
    """
    deleted = delete_workspace_embeddings(session_id)
    if deleted:
        logger.info(f"Deleted Qdrant vectors for session '{session_id}'.")
    else:
        logger.warning(f"No vectors found or deletion failed for session '{session_id}'.")
