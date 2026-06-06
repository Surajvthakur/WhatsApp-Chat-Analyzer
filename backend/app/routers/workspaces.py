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
    Persists parsed chat messages directly to PostgreSQL.
    Embeddings are generated lazily when the user opens the AI chat.
    """
    chat_id = request.chat_id
    workspace_id = request.workspace_id

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

    # 4. Cache the session in RAM under the workspace_id for instant retrieval in future requests
    from app.session_store import ChatSession
    import time
    store._sessions[workspace_id] = ChatSession(
        chat_id=workspace_id,
        df=df,
        created_at=time.time(),
        raw_text=raw_text
    )

    return {
        "status": "success",
        "workspace_id": workspace_id,
        "workspace_name": request.workspace_name,
    }


@router.post("/{workspace_id}/load")
def load_workspace(workspace_id: str):
    """
    Loads parsed chat messages directly from PostgreSQL, constructs the DataFrame,
    and populates it into FastAPI's RAM SessionStore under the workspace_id.
    """
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

        # Store in session store using workspace_id as the chat_id
        store.create(df, raw_text="")

        # Override the generated UUID to match workspace_id
        last_key = list(store._sessions.keys())[-1]
        store._sessions[workspace_id] = store._sessions.pop(last_key)
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
