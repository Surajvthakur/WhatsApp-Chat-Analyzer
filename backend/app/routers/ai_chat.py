from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.routers.analysis import _get_df
from app.ai.rag_pipeline import ingest_chat, query_chat, delete_session
from app.ai.qdrant_store import has_embeddings

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.get("/{chat_id}/status")
def get_ai_session_status(chat_id: str):
    """
    Checks if embeddings exist in Qdrant for the given chat_id.
    """
    exists = has_embeddings(chat_id)
    return {"status": "success", "exists": exists}


class QueryRequest(BaseModel):
    question: str


@router.post("/{chat_id}/init")
async def init_ai_session(chat_id: str):
    """
    Initializes an AI session for the given chat_id by creating embeddings.
    """
    try:
        df = _get_df(chat_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    success = await ingest_chat(chat_id, df)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to initialize AI session (no data found).")

    return {"status": "success", "message": "AI session initialized successfully."}


@router.post("/{chat_id}/query")
async def ask_question(chat_id: str, request: QueryRequest):
    """
    Asks a question to the initialized AI session.
    """
    answer = await query_chat(chat_id, request.question)
    return {"status": "success", "answer": answer}


@router.delete("/{chat_id}/close")
def close_ai_session(chat_id: str):
    """
    Closes and deletes the AI session.
    """
    delete_session(chat_id)
    return {"status": "success"}
