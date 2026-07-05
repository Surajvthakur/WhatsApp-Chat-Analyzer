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
    get_qdrant_embeddings_count,
)

import pandas as pd

logger = logging.getLogger(__name__)


async def ingest_chat(session_id: str, df: pd.DataFrame) -> bool:
    """
    Ensures embeddings exist in Qdrant for the given session.
    If they already exist and the count matches the expected number of chunks,
    returns immediately (cache hit).
    Otherwise chunks the chat, generates embeddings via the configured
    provider, and persists them to Qdrant.
    """
    chunks = chunk_chat_data(df)
    if not chunks:
        logger.warning("No chunks generated for session '%s'.", session_id)
        return False

    expected_count = len(chunks)
    actual_count = get_qdrant_embeddings_count(session_id)

    if actual_count == expected_count:
        logger.info(
            "Embeddings already exist in Qdrant for '%s' and count matches (%d chunks). Skipping ingestion.",
            session_id,
            actual_count,
        )
        return True

    if actual_count > 0:
        logger.info(
            "Embeddings count mismatch for '%s' (Qdrant: %d vs expected: %d). Deleting old embeddings and re-ingesting...",
            session_id,
            actual_count,
            expected_count,
        )
        delete_workspace_embeddings(session_id)

    logger.info("Ingesting chat for session '%s'...", session_id)
    metadata_list = get_chunks_metadata(df)
    embeddings = await generate_embeddings(chunks)

    success = save_embeddings(
        session_id=session_id,
        chunks=chunks,
        embeddings=embeddings,
        metadata_list=metadata_list,
    )

    if success:
        logger.info(
            "Ingestion complete for '%s'. Stored %d chunks in Qdrant.",
            session_id,
            len(chunks),
        )
    else:
        logger.error("Failed to save embeddings to Qdrant for '%s'.", session_id)

    return success


def get_recent_chat_history(workspace_id: str, limit: int = 10) -> list:
    """
    Retrieves the most recent messages for the given workspace_id from PostgreSQL.
    Returns a list of dicts with 'role' and 'content', ordered chronologically (oldest first).
    """
    if not settings.database_url:
        logger.error("Database URL is not configured. Cannot fetch chat history.")
        raise ValueError("Database URL is not configured.")

    import psycopg2

    conn = psycopg2.connect(settings.database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT "role", "content" FROM "Message" WHERE "workspaceId" = %s ORDER BY "createdAt" DESC LIMIT %s',
                (workspace_id, limit),
            )
            rows = cur.fetchall()
            messages = [{"role": row[0], "content": row[1]} for row in reversed(rows)]
            return messages
    finally:
        conn.close()


async def query_chat(session_id: str, question: str) -> str:
    """
    Routes the question through tools if applicable, else falls back to embedding search in Qdrant,
    generating an answer using the Groq LLM.
    """
    import json
    from app.routers.analysis import _get_df
    from app.tools import ToolRouter, ToolExecutor

    # 1. Try to load DataFrame for tool execution
    df = None
    try:
        df = _get_df(session_id)
    except Exception as e:
        logger.warning(f"Could not load DataFrame for session {session_id} to run tools: {e}")

    # 2. Check tools if DataFrame is available
    if df is not None:
        try:
            router = ToolRouter()
            routing = router.route(question)
            
            if routing.has_tools:
                logger.info(f"Routed query '{question}' through tools: {[t.name for t in routing.tools]}")
                executor = ToolExecutor()
                results = await executor.execute(session_id, routing, df)
                
                # Format tool results to text context
                tool_contexts = []
                for r in results:
                    status = "Success" if r.success else "Failed"
                    tool_contexts.append(f"### Tool: {r.tool_name} (Status: {status})")
                    if r.success:
                        tool_contexts.append(json.dumps(r.data, indent=2, ensure_ascii=False))
                    else:
                        tool_contexts.append(f"Error: {r.error}")
                        
                context_str = "\n\n".join(tool_contexts)
                
                # Ask Groq using the tool results as context
                if not settings.groq_api_key:
                    return "GROQ API Key is not configured on the server."
                    
                client = Groq(api_key=settings.groq_api_key)
                
                # Retrieve chat history
                chat_history = get_recent_chat_history(session_id, limit=10)
                if chat_history and chat_history[-1]["role"] == "user" and chat_history[-1]["content"] == question:
                    chat_history.pop()
                chat_history = chat_history[-10:]
                
                history_context = ""
                if chat_history:
                    history_lines = []
                    for msg in chat_history:
                        role_label = "User" if msg["role"] == "user" else "Assistant"
                        history_lines.append(f"{role_label}: {msg['content']}")
                    history_context = "\n".join(history_lines)
                    
                prompt = f"""You are a helpful AI assistant analyzing a WhatsApp chat export.
You have been provided with structured query results extracted from the chat dataset by running dedicated analysis tools.
Answer the user's question accurately using ONLY the provided tool results. Format numbers, percentages, dates, and lists cleanly.

TOOL EXECUTION RESULTS:
{context_str}
"""
                if history_context:
                    prompt += f"\nRECENT CHAT HISTORY:\n{history_context}\n"
                prompt += f"\nQUESTION:\n{question}\n"
                
                messages = [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant analyzing WhatsApp chat logs.",
                    }
                ]
                for msg in chat_history:
                    messages.append({"role": msg["role"], "content": msg["content"]})
                messages.append({"role": "user", "content": prompt})
                
                completion = client.chat.completions.create(
                    model=settings.groq_model,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=1024,
                )
                return completion.choices[0].message.content
                
        except Exception as e:
            from groq import RateLimitError, APIError as GroqAPIError
            err_str = str(e).lower()
            if isinstance(e, (RateLimitError, GroqAPIError)) or "rate limit" in err_str or "resource_exhausted" in err_str or "quota" in err_str or "429" in err_str:
                logger.warning(f"Groq API/rate limit error in tool pipeline, raising directly to trigger user retry UI: {e}")
                raise e
            logger.error(f"Error in tool routing/execution pipeline: {e}", exc_info=True)
            # Proceed to standard RAG pipeline fallback

    # 3. Fallback to standard RAG pipeline (embedding search)
    # 1. Embed the question
    question_embedding = (await generate_embeddings([question]))[0]
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

        # Retrieve chat history
        chat_history = get_recent_chat_history(session_id, limit=10)

        # Exclude current question if it was already saved asynchronously by frontend
        if chat_history and chat_history[-1]["role"] == "user" and chat_history[-1]["content"] == question:
            chat_history.pop()

        chat_history = chat_history[-10:]  # Ensure we have at most 10 messages (5 turns)

        history_context = ""
        if chat_history:
            history_lines = []
            for msg in chat_history:
                role_label = "User" if msg["role"] == "user" else "Assistant"
                history_lines.append(f"{role_label}: {msg['content']}")
            history_context = "\n".join(history_lines)

        prompt = f"""You are a helpful AI assistant analyzing a WhatsApp chat export.
Answer the user's question based ONLY on the provided chat context. If the answer is not in the context, say so. Do not invent information.

CONTEXT:
{context}
"""

        if history_context:
            prompt += f"\nRECENT CHAT HISTORY:\n{history_context}\n"

        prompt += f"""
QUESTION:
{question}
"""

        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant analyzing WhatsApp chat logs.",
            }
        ]

        # Inject structural chat history
        for msg in chat_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # Inject the current query prompt
        messages.append({
            "role": "user",
            "content": prompt
        })

        completion = client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
        )

        return completion.choices[0].message.content

    except Exception as e:
        logger.error("Error calling Groq API: %s", e)
        return f"Sorry, there was an error communicating with the AI provider: {str(e)}"


def delete_session(session_id: str):
    """
    Deletes all embeddings for the session from Qdrant.
    """
    deleted = delete_workspace_embeddings(session_id)
    if deleted:
        logger.info("Deleted Qdrant vectors for session '%s'.", session_id)
    else:
        logger.warning("No vectors found or deletion failed for session '%s'.", session_id)
