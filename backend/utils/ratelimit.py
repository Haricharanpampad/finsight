"""Tiny in-memory rate limiter (per process).

Good enough for a single-instance deployment. If you run several workers/instances, replace it
with a shared store such as Redis (for example via the `slowapi` or `fastapi-limiter` packages).
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, status


class RateLimiter:
    def __init__(self, max_calls: int, per_seconds: int):
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self._hits: dict[str, deque] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self.per_seconds:
            hits.popleft()
        if len(hits) >= self.max_calls:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests - please slow down and try again shortly.")
        hits.append(now)
