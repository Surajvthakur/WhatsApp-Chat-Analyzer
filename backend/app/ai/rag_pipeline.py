import time
from groq import Groq
from app.config import settings
from app.ai.chunking import chunk_chat_data
from app.ai.embeddings import generate_embeddings
from app.ai.faiss_store import create_faiss_index, search_faiss_index
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Memory store for active sessions
# Format: active_sessions[session_id] = {"index": index, "chunks": chunks, "last_accessed": timestamp}
active_sessions = {}

def ingest_chat(session_id: str, df: pd.DataFrame):
    """
    Chunks the chat, generates embeddings, stores in FAISS, 
    and keeps the session in memory.
    """
    logger.info(f"Ingesting chat for session {session_id}")
    chunks = chunk_chat_data(df)
    
    if not chunks:
        logger.warning(f"No chunks generated for session {session_id}")
        return False
        
    embeddings = generate_embeddings(chunks)
    index = create_faiss_index(embeddings)
    
    # Safely convert embeddings (numpy array) to list of floats for persistence later
    embeddings_list = [e.tolist() for e in embeddings] if hasattr(embeddings, "tolist") else list(embeddings)
    
    active_sessions[session_id] = {
        "index": index,
        "chunks": chunks,
        "embeddings": embeddings_list,
        "last_accessed": time.time()
    }
    
    logger.info(f"Ingestion complete for session {session_id}. Created {len(chunks)} chunks.")
    return True

def query_chat(session_id: str, question: str) -> str:
    """
    Retrieves context using FAISS (RAM) or Qdrant (persistent) and generates an answer using Groq.
    """
    session = active_sessions.get(session_id)
    
    # 1. Embed the question
    question_embedding = generate_embeddings([question])[0]
    if hasattr(question_embedding, "tolist"):
        question_embedding = question_embedding.tolist()
    
    retrieved_chunks = []
    
    if session:
        # Update last accessed time
        session["last_accessed"] = time.time()
        
        index = session["index"]
        chunks = session["chunks"]
        
        # Retrieve top chunks using FAISS
        top_indices = search_faiss_index(index, question_embedding, top_k=5)
        retrieved_chunks = [chunks[i] for i in top_indices if i >= 0 and i < len(chunks)]
    else:
        # Fall back to Qdrant search if not in RAM
        from app.ai.qdrant_store import search_qdrant_embeddings
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
                    "content": "You are a helpful assistant analyzing WhatsApp chat logs."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        
        return completion.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error calling Groq API: {e}")
        return f"Sorry, there was an error communicating with the AI provider: {str(e)}"

def cleanup_inactive_sessions(timeout_minutes: int = 30):
    """
    Removes sessions that haven't been accessed in the timeout period.
    """
    current_time = time.time()
    timeout_seconds = timeout_minutes * 60
    
    expired_sessions = []
    for session_id, data in active_sessions.items():
        if current_time - data["last_accessed"] > timeout_seconds:
            expired_sessions.append(session_id)
            
    for session_id in expired_sessions:
        del active_sessions[session_id]
        logger.info(f"Cleaned up inactive session: {session_id}")

def delete_session(session_id: str):
    """
    Explicitly deletes a session.
    """
    if session_id in active_sessions:
        del active_sessions[session_id]
        logger.info(f"Deleted session: {session_id}")
