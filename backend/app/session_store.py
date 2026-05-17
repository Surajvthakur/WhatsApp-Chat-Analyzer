import time
import uuid
from dataclasses import dataclass

import pandas as pd


@dataclass
class ChatSession:
    chat_id: str
    df: pd.DataFrame
    created_at: float


class SessionStore:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._ttl_seconds = ttl_seconds

    def create(self, df: pd.DataFrame) -> str:
        self._cleanup_expired()
        chat_id = str(uuid.uuid4())
        self._sessions[chat_id] = ChatSession(
            chat_id=chat_id,
            df=df,
            created_at=time.time(),
        )
        return chat_id

    def get(self, chat_id: str) -> pd.DataFrame | None:
        self._cleanup_expired()
        session = self._sessions.get(chat_id)
        if session is None:
            return None
        return session.df

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = [
            cid
            for cid, s in self._sessions.items()
            if now - s.created_at > self._ttl_seconds
        ]
        for cid in expired:
            del self._sessions[cid]
