"""
Modular, thread-safe in-memory sliding window rate limiter.
"""

import time
import asyncio
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """
    Sliding-window rate limiter for protecting sensitive endpoints.
    """

    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check_rate_limit(
        self, key: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check if an action under `key` exceeds `max_requests` within `window_seconds`.
        
        Returns:
            (allowed: bool, retry_after: int)
        """
        async with self._lock:
            now = time.time()
            cutoff = now - window_seconds
            
            # Prune expired timestamps for key
            timestamps = [t for t in self._requests[key] if t > cutoff]
            self._requests[key] = timestamps
            
            if len(timestamps) >= max_requests:
                # Calculate remaining time until the oldest request in window expires
                oldest_in_window = timestamps[0]
                retry_after = int(oldest_in_window + window_seconds - now) + 1
                logger.warning(
                    "Rate limit exceeded for key '%s': %d requests in window. Retry after %ds",
                    key,
                    len(timestamps),
                    retry_after,
                )
                return False, max(retry_after, 1)

            # Record current request timestamp
            self._requests[key].append(now)
            return True, 0

    async def clear(self, key: str) -> None:
        """Clear recorded requests for a specific key (e.g. after successful OTP verify)."""
        async with self._lock:
            if key in self._requests:
                del self._requests[key]


# Singleton instance
rate_limiter = InMemoryRateLimiter()
