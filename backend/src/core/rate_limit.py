"""In-process load protection for the single-instance deployment.

1. ``RateLimiter``: sliding-window request limit per client IP.
2. ``prediction_slot``: caps concurrent model runs so parallel requests cannot
   push the 512 MB instance out of memory; extra requests wait, then get 503.

Both are per process. With more than one instance, move them to a shared store.
"""

import asyncio
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Deque, Dict, Optional

from fastapi import HTTPException, Request, status

from src.core.config import get_settings


def client_ip(request: Request) -> str:
    """Client IP; behind Render's proxy the first X-Forwarded-For hop is the client."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    def __init__(self, window_seconds: float = 60.0) -> None:
        self.window = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int) -> Optional[int]:
        """Record a hit. Returns None when allowed, else seconds until retry."""
        if limit <= 0:
            return None
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= limit:
                return max(1, int(self.window - (now - hits[0])) + 1)
            hits.append(now)
            if len(self._hits) > 10_000:  # drop idle keys so memory stays bounded
                for k in [k for k, v in self._hits.items() if not v]:
                    del self._hits[k]
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


rate_limiter = RateLimiter()


def enforce_rate_limit(request: Request) -> None:
    """FastAPI dependency: 429 when the client exceeds RATE_LIMIT_PER_MINUTE."""
    limit = get_settings().RATE_LIMIT_PER_MINUTE
    retry_after = rate_limiter.check(f"{request.url.path}|{client_ip(request)}", limit)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait a minute and try again.",
            headers={"Retry-After": str(retry_after)},
        )


_semaphore: Optional[asyncio.Semaphore] = None
_semaphore_size: int = 0


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore, _semaphore_size
    size = max(1, get_settings().MAX_CONCURRENT_PREDICTIONS)
    if _semaphore is None or _semaphore_size != size:
        _semaphore, _semaphore_size = asyncio.Semaphore(size), size
    return _semaphore


@asynccontextmanager
async def prediction_slot():
    """Hold one model-run slot; 503 when none frees up within the queue timeout."""
    sem = _get_semaphore()
    timeout = get_settings().PREDICTION_QUEUE_TIMEOUT_SECONDS
    try:
        await asyncio.wait_for(sem.acquire(), timeout=timeout)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The analysis service is busy. Please try again in a minute.",
            headers={"Retry-After": "30"},
        )
    try:
        yield
    finally:
        sem.release()
