from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.routers.analysis import _get_df
from app.auth.authorization import get_current_user_id, verify_chat_access
from app.ai.rag_pipeline import ingest_chat, query_chat, delete_session
from app.ai.qdrant_store import has_embeddings

from google.genai.errors import APIError

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.get("/{chat_id}/status")
def get_ai_session_status(chat_id: str, req: Request):
    """
    Checks if embeddings exist in Qdrant for the given chat_id.
    """
    user_id = get_current_user_id(req)
    verify_chat_access(chat_id, user_id)
    exists = has_embeddings(chat_id)
    return {"status": "success", "exists": exists}


class QueryRequest(BaseModel):
    question: str


@router.post("/{chat_id}/init")
async def init_ai_session(chat_id: str, req: Request):
    """
    Initializes an AI session for the given chat_id by creating embeddings.
    """
    user_id = get_current_user_id(req)
    try:
        df = _get_df(chat_id, user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        success = await ingest_chat(chat_id, df)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to initialize AI session (no data found).")
    except APIError as e:
        if getattr(e, "code", None) == 429 or getattr(e, "status", None) == "RESOURCE_EXHAUSTED" or "quota" in str(e).lower():
            raise HTTPException(
                status_code=429,
                detail="Gemini API Rate Limit Exceeded. You have exceeded your API quota. Please wait a minute and retry."
            )
        raise HTTPException(status_code=500, detail=f"AI Service Error: {e.message or str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    return {"status": "success", "message": "AI session initialized successfully."}


@router.post("/{chat_id}/query")
async def ask_question(chat_id: str, body: QueryRequest, req: Request):
    """
    Asks a question to the initialized AI session.
    """
    user_id = get_current_user_id(req)
    verify_chat_access(chat_id, user_id)

    from groq import RateLimitError as GroqRateLimitError, APIError as GroqAPIError
    try:
        answer = await query_chat(chat_id, body.question)
        return {"status": "success", "answer": answer}
    except GroqRateLimitError as e:
        raise HTTPException(
            status_code=429,
            detail="Groq LLM Rate Limit Exceeded. You have exceeded your Groq API quota. Please wait a minute and retry."
        )
    except GroqAPIError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Groq LLM Service Error: {str(e)}"
        )
    except APIError as e:
        if getattr(e, "code", None) == 429 or getattr(e, "status", None) == "RESOURCE_EXHAUSTED" or "quota" in str(e).lower():
            raise HTTPException(
                status_code=429,
                detail="Gemini API Rate Limit Exceeded. You have exceeded your API quota. Please wait a minute and retry."
            )
        raise HTTPException(status_code=500, detail=f"AI Service Error: {e.message or str(e)}")
    except Exception as e:
        err_str = str(e).lower()
        if "rate limit" in err_str or "resource_exhausted" in err_str or "quota" in err_str or "429" in err_str:
            raise HTTPException(
                status_code=429,
                detail=f"Rate Limit Exceeded: {str(e)}"
            )
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.delete("/{chat_id}/close")
def close_ai_session(chat_id: str, req: Request):
    """
    Closes and deletes the AI session.
    """
    user_id = get_current_user_id(req)
    verify_chat_access(chat_id, user_id)
    delete_session(chat_id)
    return {"status": "success"}
