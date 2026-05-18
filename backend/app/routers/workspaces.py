import logging
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd

import preprocessor
from app.config import settings
from app.routers.analysis import store
from app.ai.rag_pipeline import active_sessions
from app.ai.chunking import chunk_chat_data
from app.ai.embeddings import generate_embeddings
from app.ai.faiss_store import create_faiss_index
from app.ai.qdrant_store import save_workspace_embeddings, delete_workspace_embeddings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])

class PersistRequest(BaseModel):
    chat_id: str
    workspace_id: str
    workspace_name: str

class LoadRequest(BaseModel):
    raw_text: str

@router.post("/persist")
def persist_workspace(request: PersistRequest):
    """
    Saves RAM embeddings of chat_id to Qdrant under workspace_id,
    and returns the raw chat text and a nice summary.
    """
    chat_id = request.chat_id
    workspace_id = request.workspace_id
    
    # 1. Fetch chat DataFrame and raw text from RAM SessionStore
    session_data = store.get_session(chat_id)
    if not session_data:
        raise HTTPException(
            status_code=404, 
            detail="Chat session not found or expired in RAM. Please upload again."
        )
        
    df = session_data.df
    raw_text = session_data.raw_text
    
    # 2. Check if active AI session exists in RAM (holds chunks and embeddings)
    ai_session = active_sessions.get(chat_id)
    if not ai_session:
        logger.info(f"AI session not found in RAM for {chat_id}. Generating embeddings on the fly...")
        # Generate embeddings on the fly since Ask AI was never clicked
        chunks = chunk_chat_data(df)
        if not chunks:
            raise HTTPException(
                status_code=422,
                detail="Could not generate chunks from the chat data."
            )
        embeddings = generate_embeddings(chunks)
        index = create_faiss_index(embeddings)
        embeddings_list = [e.tolist() for e in embeddings] if hasattr(embeddings, "tolist") else list(embeddings)
        
        # Cache it in active_sessions so subsequent queries work immediately
        active_sessions[chat_id] = {
            "index": index,
            "chunks": chunks,
            "embeddings": embeddings_list,
            "last_accessed": time.time()
        }
        ai_session = active_sessions[chat_id]
        
    chunks = ai_session["chunks"]
    embeddings = ai_session["embeddings"]
    
    # 3. Save to Qdrant vector store
    success = save_workspace_embeddings(
        workspace_id=workspace_id,
        chunks=chunks,
        embeddings=embeddings,
        df=df
    )
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to persist vector embeddings to Qdrant."
        )
        
    # 4. Generate summary (using Groq if key is available, fallback to stats)
    summary = ""
    if settings.groq_api_key:
        try:
            from groq import Groq
            client = Groq(api_key=settings.groq_api_key)
            
            # Use the first 25 messages of the conversation as a sample for LLM summary
            sample_df = df[df["user"] != "group_notification"].head(25)
            chat_sample = ""
            for _, r in sample_df.iterrows():
                chat_sample += f"{r.get('user', 'User')}: {r.get('message', '')}\n"
                
            prompt = (
                "You are an expert chat analyzer. Provide a brief 2-sentence summary "
                "describing the primary topic or tone of this WhatsApp conversation based on this sample. "
                "Be warm, concise, and do not use placeholders or technical jargon:\n\n"
                f"{chat_sample}"
            )
            
            completion = client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes chats."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=120
            )
            summary = completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Failed to generate LLM summary: {e}")
            
    if not summary:
        # Fallback metadata summary
        start_date = str(df['date'].min())[:10] if pd.notna(df['date'].min()) else "Unknown"
        end_date = str(df['date'].max())[:10] if pd.notna(df['date'].max()) else "Unknown"
        users = df[df['user'] != 'group_notification']['user'].unique()
        speakers_str = ", ".join(users[:3])
        if len(users) > 3:
            speakers_str += f" and {len(users) - 3} others"
        summary = f"A WhatsApp chat between {speakers_str} spanning from {start_date} to {end_date} containing {len(df)} messages."
        
    return {
        "status": "success",
        "workspace_id": workspace_id,
        "workspace_name": request.workspace_name,
        "summary": summary,
        "raw_text": raw_text
    }

@router.post("/{workspace_id}/load")
def load_workspace(workspace_id: str, request: LoadRequest):
    """
    Loads raw chat text from a saved workspace, parses it,
    and populates it into FastAPI's RAM SessionStore under the workspace_id.
    This enables the entire analytics dashboard to work instantly.
    """
    raw_text = request.raw_text
    if not raw_text:
        raise HTTPException(status_code=400, detail="raw_text is required.")
        
    try:
        df = preprocessor.preprocess(raw_text)
        if df.empty:
            raise HTTPException(status_code=422, detail="Parsed chat is empty.")
            
        # Store in session store using workspace_id as the chat_id!
        # This is a beautiful mapping where workspace_id == chat_id
        store.create(df, raw_text=raw_text)
        
        # Override the generated UUID in store to make sure it matches workspace_id
        # Our modified SessionStore supports custom IDs, or we can just inject it
        store._sessions[workspace_id] = store._sessions.pop(list(store._sessions.keys())[-1])
        store._sessions[workspace_id].chat_id = workspace_id
        
        # Build user list
        from app.serializers import build_user_list, get_date_range
        from app.schemas import DateRange
        users = build_user_list(df)
        start, end = get_date_range(df)
        
        return {
            "status": "success",
            "chat_id": workspace_id,
            "message_count": len(df),
            "users": users,
            "date_range": {"start": start, "end": end}
        }
    except Exception as e:
        logger.error(f"Error loading workspace {workspace_id} in RAM: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load workspace data: {str(e)}")

@router.delete("/{workspace_id}")
def delete_workspace(workspace_id: str):
    """
    Cleans up all resources associated with the workspace: Qdrant vectors
    and RAM sessions.
    """
    # 1. Delete from Qdrant
    qdrant_deleted = delete_workspace_embeddings(workspace_id)
    
    # 2. Delete from memory session store
    session_deleted = False
    if workspace_id in store._sessions:
        del store._sessions[workspace_id]
        session_deleted = True
        
    if workspace_id in active_sessions:
        del active_sessions[workspace_id]
        
    return {
        "status": "success",
        "qdrant_deleted": qdrant_deleted,
        "ram_deleted": session_deleted
    }
