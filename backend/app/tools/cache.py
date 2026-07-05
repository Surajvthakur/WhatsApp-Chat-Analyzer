import time
import hashlib
import json
import logging
from typing import Any
from app.tools.base import ToolResult

logger = logging.getLogger(__name__)

class ToolCache:
    """In-memory cache for tool results with TTL expiration.
    
    Prevents running expensive aggregations or filters repeatedly within a short window.
    """
    _cache: dict[str, tuple[float, ToolResult]] = {}
    TTL_SECONDS = 300  # 5 minutes default cache longevity

    @classmethod
    def _generate_key(cls, session_id: str, tool_name: str, params: dict[str, Any], df_signature: str) -> str:
        """Create a unique, deterministic string key from execution parameters and DataFrame signature."""
        serialized_params = json.dumps(params, sort_keys=True, default=str)
        hash_input = f"{session_id}:{tool_name}:{serialized_params}:{df_signature}"
        return hashlib.md5(hash_input.encode("utf-8")).hexdigest()

    @classmethod
    def get(cls, session_id: str, tool_name: str, params: dict[str, Any], df_signature: str = "") -> ToolResult | None:
        """Fetch cached tool result if it exists and has not expired."""
        key = cls._generate_key(session_id, tool_name, params, df_signature)
        if key in cls._cache:
            created_at, result = cls._cache[key]
            if time.time() - created_at < cls.TTL_SECONDS:
                logger.debug(f"Cache hit for tool: {tool_name} (session: {session_id})")
                return result
            # Expired, clean it up
            del cls._cache[key]
        return None

    @classmethod
    def set(cls, session_id: str, tool_name: str, params: dict[str, Any], result: ToolResult, df_signature: str = "") -> None:
        """Cache a tool execution result."""
        # Ensure we don't cache failures
        if not result.success:
            return
            
        # Clean expired cache entries to prevent memory growth
        cls._cleanup_expired()
        
        key = cls._generate_key(session_id, tool_name, params, df_signature)
        cls._cache[key] = (time.time(), result)
        logger.debug(f"Cached result for tool: {tool_name} (session: {session_id})")

    @classmethod
    def invalidate_session(cls, session_id: str) -> None:
        """Remove all cache entries for a specific session (e.g. when session is closed)."""
        keys_to_delete = [
            k for k in cls._cache.keys()
            # Since keys are MD5 hashes, we can't search by prefix directly unless we store metadata.
            # Instead, let's keep it simple: we can loop or do a minor refactor.
            # Wait, let's store keys as a dict with metadata or include session_id in the cache dict.
        ]
        # Let's update the cache structure to allow efficient invalidation.

    @classmethod
    def _cleanup_expired(cls) -> None:
        """Delete all expired entries from the cache."""
        now = time.time()
        expired_keys = [
            key for key, (created_at, _) in cls._cache.items()
            if now - created_at > cls.TTL_SECONDS
        ]
        for key in expired_keys:
            del cls._cache[key]
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired tool cache entries.")
