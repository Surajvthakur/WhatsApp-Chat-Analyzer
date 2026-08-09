import time
import uuid
from dataclasses import dataclass

import pandas as pd


@dataclass
class ChatSession:
    chat_id: str
    df: pd.DataFrame
    created_at: float
    raw_text: str = ""
    user_id: str | None = None


class SessionStore:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._ttl_seconds = ttl_seconds

    def create(self, df: pd.DataFrame, raw_text: str = "", user_id: str | None = None) -> str:
        self._cleanup_expired()
        chat_id = str(uuid.uuid4())
        self._sessions[chat_id] = ChatSession(
            chat_id=chat_id,
            df=df,
            created_at=time.time(),
            raw_text=raw_text,
            user_id=user_id,
        )
        return chat_id

    def create_with_id(
        self, chat_id: str, df: pd.DataFrame, raw_text: str = "", user_id: str | None = None
    ) -> None:
        """Explicitly register a session with a designated chat/workspace ID."""
        self._cleanup_expired()
        self._sessions[chat_id] = ChatSession(
            chat_id=chat_id,
            df=df,
            created_at=time.time(),
            raw_text=raw_text,
            user_id=user_id,
        )

    def get(self, chat_id: str) -> pd.DataFrame | None:
        self._cleanup_expired()
        session = self._sessions.get(chat_id)
        if session is None:
            return None
        return session.df

    def get_session(self, chat_id: str) -> ChatSession | None:
        self._cleanup_expired()
        return self._sessions.get(chat_id)

    def delete(self, chat_id: str) -> None:
        """Remove a session by ID."""
        self._sessions.pop(chat_id, None)

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = [
            cid
            for cid, s in self._sessions.items()
            if now - s.created_at > self._ttl_seconds
        ]
        for cid in expired:
            del self._sessions[cid]


from app.config import settings

store = SessionStore(ttl_seconds=settings.session_ttl_seconds)
