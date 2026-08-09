"""
Modular authorization helpers for checking resource ownership.
"""

import logging
import psycopg2
from fastapi import Request, HTTPException

from app.config import settings
from app.session_store import store

logger = logging.getLogger(__name__)


def get_current_user_id(request: Request) -> str:
    """
    Extract current authenticated user ID from request state.
    Set by AuthMiddleware.
    """
    user = getattr(request.state, "user", None)
    if not user or not isinstance(user, dict) or "sub" not in user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user["sub"]


def verify_workspace_ownership(workspace_id: str, user_id: str) -> bool:
    """
    Verify if the given workspace belongs to user_id in PostgreSQL.
    """
    if not settings.database_url:
        logger.warning("DATABASE_URL is not set; skipping database ownership check.")
        return True

    try:
        conn = psycopg2.connect(settings.database_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT "userId" FROM "Workspace" WHERE id = %s',
                    (workspace_id,)
                )
                row = cur.fetchone()
                if not row:
                    return False
                return row[0] == user_id
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error checking workspace ownership for {workspace_id}: {e}")
        return False


def verify_chat_access(chat_id: str, user_id: str) -> None:
    """
    Verify if user_id has permission to access chat_id/workspace_id.
    Raises HTTPException(403) if access is denied, or 404 if not found.
    """
    session = store.get_session(chat_id)
    if session is not None:
        if session.user_id is not None and session.user_id != user_id:
            logger.warning(f"User {user_id} attempted unauthorized access to RAM session {chat_id}")
            raise HTTPException(status_code=403, detail="Access forbidden: You do not own this chat session")
        elif session.user_id == user_id:
            return  # Granted via RAM session match

    # If not matched in RAM or session.user_id is unset, check DB workspace ownership
    if not verify_workspace_ownership(chat_id, user_id):
        logger.warning(f"User {user_id} denied access to workspace {chat_id}")
        raise HTTPException(status_code=403, detail="Access forbidden: You do not own this workspace")
