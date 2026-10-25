"""Small in-memory rate limiter for the auth endpoints.

Counts are per process, so with several workers each one limits separately. That is enough to
stop password guessing against a single account; a shared store (e.g. Redis) would be the next step.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from helpers.config import Config


class RateLimiter:
    def __init__(self, name: str, limit: int, window_seconds: int) -> None:
        self.name = name
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str) -> None:
        """Record an attempt, raising 429 if the key is over its limit."""
        if not Config.rate_limits_enabled:
            return
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = int(self.window - (now - hits[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many attempts. Try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# Password guessing against one account, and from one address against many accounts
login_by_account = RateLimiter("login-account", limit=8, window_seconds=300)
login_by_ip = RateLimiter("login-ip", limit=30, window_seconds=300)
signup_by_ip = RateLimiter("signup-ip", limit=10, window_seconds=3600)
