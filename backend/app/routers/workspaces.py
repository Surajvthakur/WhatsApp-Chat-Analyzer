import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import pandas as pd

import preprocessor
from app.config import settings
from app.routers.analysis import store
from app.auth.authorization import get_current_user_id, verify_workspace_ownership, verify_chat_access
from app.ai.qdrant_store import delete_workspace_embeddings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


class PersistRequest(BaseModel):
    chat_id: str
    workspace_id: str
    workspace_name: str


@router.post("/persist")
def persist_workspace(req: Request, body: PersistRequest):
    """
    Persists parsed chat messages directly to PostgreSQL.
    Embeddings are generated lazily when the user opens the AI chat.
    """
    user_id = get_current_user_id(req)
    chat_id = body.chat_id
    workspace_id = body.workspace_id

    # 0. Verify authorization
    verify_chat_access(chat_id, user_id)

    # 1. Fetch chat DataFrame from RAM SessionStore
    session_data = store.get_session(chat_id)
    if not session_data:
        raise HTTPException(
            status_code=404,
            detail="Chat session not found or expired in RAM. Please upload again.",
        )

    df = session_data.df
    raw_text = session_data.raw_text

    # 2. Bulk-insert chat messages into the database
    if not settings.database_url:
        logger.error("Database URL is not configured.")
        raise HTTPException(
            status_code=500,
            detail="Database URL is not configured in settings.",
        )

    try:
        import psycopg2
        from psycopg2.extras import execute_values
        import uuid

        logger.info(f"Connecting to database to bulk-insert chat messages for workspace {workspace_id}...")
        conn = psycopg2.connect(settings.database_url)
        try:
            with conn.cursor() as cur:
                # Prepare data for insertion (id, workspaceId, date, user, message)
                # Filter out messages without a valid date since Postgres schema demands non-null date
                valid_df = df[df["date"].notna()]
                
                insert_values = []
                for row in valid_df.itertuples(index=False):
                    msg_id = str(uuid.uuid4())
                    dt_val = row.date.to_pydatetime()
                    
                    insert_values.append((
                        msg_id,
                        workspace_id,
                        dt_val,
                        row.user,
                        row.message
                    ))
                
                # Execute bulk insert
                insert_query = 'INSERT INTO "ChatMessage" ("id", "workspaceId", "date", "user", "message") VALUES %s'
                execute_values(cur, insert_query, insert_values)
                conn.commit()
                logger.info(f"Successfully bulk-inserted {len(insert_values)} messages for workspace {workspace_id}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to insert messages into PostgreSQL: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to save messages to database: {str(e)}")
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database connection error during persist: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database connection error during persist: {str(e)}")

    # 3. Cache the session in RAM under the workspace_id for instant retrieval in future requests
    store.create_with_id(workspace_id, df, raw_text=raw_text, user_id=user_id)

    return {
        "status": "success",
        "workspace_id": workspace_id,
        "workspace_name": body.workspace_name,
    }


@router.post("/{workspace_id}/load")
def load_workspace(workspace_id: str, req: Request):
    """
    Loads parsed chat messages directly from PostgreSQL, constructs the DataFrame,
    and populates it into FastAPI's RAM SessionStore under the workspace_id.
    """
    user_id = get_current_user_id(req)
    if not verify_workspace_ownership(workspace_id, user_id):
        raise HTTPException(status_code=403, detail="Access forbidden: You do not own this workspace")

    if not settings.database_url:
        logger.error("Database URL is not configured.")
        raise HTTPException(
            status_code=500,
            detail="Database URL is not configured in settings.",
        )

    try:
        import psycopg2
        logger.info(f"Connecting to database to fetch workspace messages for {workspace_id}...")
        conn = psycopg2.connect(settings.database_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT "date", "user", "message" FROM "ChatMessage" WHERE "workspaceId" = %s ORDER BY "date" ASC',
                    (workspace_id,)
                )
                rows = cur.fetchall()
                if not rows:
                    raise HTTPException(
                        status_code=404,
                        detail=f"No messages found for workspace ID {workspace_id} in database.",
                    )
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch workspace messages from PostgreSQL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch workspace messages from database: {str(e)}")

    try:
        # Construct DataFrame from the fetched database rows
        df = pd.DataFrame(rows, columns=["date", "user", "message"])
        df["date"] = pd.to_datetime(df["date"])

        # Add derived date columns
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['day'] = df['date'].dt.day
        df['hour'] = df['date'].dt.hour
        df['minute'] = df['date'].dt.minute
        df['only_date'] = df['date'].dt.date
        df['month_num'] = df['date'].dt.month
        df['day_name'] = df['date'].dt.day_name()

        h = df['hour']
        h_next = h + 1
        h_str = h.astype(str).where(h != 0, '00')
        h_next_str = h_next.astype(str).where(h != 23, '00')
        df['period'] = h_str + '-' + h_next_str

        # Store in session store using workspace_id as the chat_id and user_id ownership
        store.create_with_id(workspace_id, df, raw_text="", user_id=user_id)

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
    except Exception as e:
        logger.error(f"Error loading workspace {workspace_id} in RAM: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load workspace data: {str(e)}")


@router.delete("/{workspace_id}")
def delete_workspace(workspace_id: str, req: Request):
    """
    Cleans up all resources associated with the workspace:
    Qdrant vectors and RAM sessions.
    """
    user_id = get_current_user_id(req)
    if not verify_workspace_ownership(workspace_id, user_id):
        raise HTTPException(status_code=403, detail="Access forbidden: You do not own this workspace")

    # 1. Delete from Qdrant
    qdrant_deleted = delete_workspace_embeddings(workspace_id)

    # 2. Delete from memory session store
    session_existed = store.get_session(workspace_id) is not None
    store.delete(workspace_id)

    return {
        "status": "success",
        "qdrant_deleted": qdrant_deleted,
        "ram_deleted": session_existed,
    }
