import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd

import preprocessor
from app.config import settings
from app.routers.analysis import store
from app.ai.qdrant_store import delete_workspace_embeddings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


class PersistRequest(BaseModel):
    chat_id: str
    workspace_id: str
    workspace_name: str


@router.post("/persist")
def persist_workspace(request: PersistRequest):
    """
    Persists raw chat text and a summary for the workspace.
    Embeddings are generated lazily when the user opens the AI chat.
    """
    chat_id = request.chat_id
    workspace_id = request.workspace_id

    # 1. Fetch chat DataFrame and raw text from RAM SessionStore
    session_data = store.get_session(chat_id)
    if not session_data:
        raise HTTPException(
            status_code=404,
            detail="Chat session not found or expired in RAM. Please upload again.",
        )

    df = session_data.df
    raw_text = session_data.raw_text

    # 2. Generate summary (using Groq if available, fallback to stats)
    summary = ""
    if settings.groq_api_key:
        try:
            from groq import Groq
            client = Groq(api_key=settings.groq_api_key)

            sample_df = df[df["user"] != "group_notification"].head(25)
            users = sample_df["user"] if "user" in sample_df.columns else ["User"] * len(sample_df)
            messages = sample_df["message"] if "message" in sample_df.columns else [""] * len(sample_df)
            chat_sample = "".join(f"{u}: {m}\n" for u, m in zip(users, messages))

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
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=120,
            )
            summary = completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Failed to generate LLM summary: {e}")

    if not summary:
        # Fallback metadata summary
        start_date = str(df["date"].min())[:10] if pd.notna(df["date"].min()) else "Unknown"
        end_date = str(df["date"].max())[:10] if pd.notna(df["date"].max()) else "Unknown"
        users = df[df["user"] != "group_notification"]["user"].unique()
        speakers_str = ", ".join(users[:3])
        if len(users) > 3:
            speakers_str += f" and {len(users) - 3} others"
        summary = (
            f"A WhatsApp chat between {speakers_str} "
            f"spanning from {start_date} to {end_date} containing {len(df)} messages."
        )

    return {
        "status": "success",
        "workspace_id": workspace_id,
        "workspace_name": request.workspace_name,
        "summary": summary,
        "raw_text": raw_text,
    }


@router.post("/{workspace_id}/load")
def load_workspace(workspace_id: str):
    """
    Loads raw chat text from PostgreSQL for a saved workspace, parses it,
    and populates it into FastAPI's RAM SessionStore under the workspace_id.
    This enables the entire analytics dashboard to work instantly.
    """
    if not settings.database_url:
        logger.error("Database URL is not configured.")
        raise HTTPException(
            status_code=500,
            detail="Database URL is not configured in settings.",
        )

    try:
        import psycopg2
        logger.info(f"Connecting to database to fetch workspace {workspace_id}...")
        conn = psycopg2.connect(settings.database_url)
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT "chatData" FROM "Workspace" WHERE "id" = %s', (workspace_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Workspace with ID {workspace_id} not found in database.",
                    )
                raw_text = row[0]
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch workspace from PostgreSQL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch workspace from database: {str(e)}")

    try:
        df = preprocessor.preprocess(raw_text)
        if df.empty:
            raise HTTPException(status_code=422, detail="Parsed chat is empty.")

        # Store in session store using workspace_id as the chat_id
        store.create(df, raw_text=raw_text)

        # Override the generated UUID to match workspace_id
        store._sessions[workspace_id] = store._sessions.pop(list(store._sessions.keys())[-1])
        store._sessions[workspace_id].chat_id = workspace_id

        # Build user list
        from app.serializers import build_user_list, get_date_range
        users = build_user_list(df)
        start, end = get_date_range(df)

        return {
            "status": "success",
            "chat_id": workspace_id,
            "message_count": len(df),
            "users": users,
            "date_range": {"start": start, "end": end},
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading workspace {workspace_id} in RAM: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load workspace data: {str(e)}")


@router.delete("/{workspace_id}")
def delete_workspace(workspace_id: str):
    """
    Cleans up all resources associated with the workspace:
    Qdrant vectors and RAM sessions.
    """
    # 1. Delete from Qdrant
    qdrant_deleted = delete_workspace_embeddings(workspace_id)

    # 2. Delete from memory session store
    session_deleted = False
    if workspace_id in store._sessions:
        del store._sessions[workspace_id]
        session_deleted = True

    return {
        "status": "success",
        "qdrant_deleted": qdrant_deleted,
        "ram_deleted": session_deleted,
    }
