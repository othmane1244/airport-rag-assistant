"""Small single-process rate limit for the public, LLM-backed chat route.

For multiple API replicas, enforce the same policy at the API gateway or with
shared storage (for example Redis) instead of relying on this process-local map.
"""

from collections import deque
from threading import Lock
from time import monotonic

from fastapi import Depends, HTTPException, status

from app.auth import require_current_user

WINDOW_SECONDS = 60
MAX_REQUESTS = 30
_requests: dict[str, deque[float]] = {}
_lock = Lock()


def enforce_chat_rate_limit(
    user: dict = Depends(require_current_user),
) -> None:
    subject = str(user.get("sub", "unknown"))
    now = monotonic()
    retry_after = 0

    with _lock:
        # Expire old keys so a changing user base cannot grow this map forever.
        expired = [
            key
            for key, timestamps in _requests.items()
            if not timestamps or now - timestamps[-1] >= WINDOW_SECONDS
        ]
        for key in expired:
            del _requests[key]

        timestamps = _requests.setdefault(subject, deque())
        while timestamps and now - timestamps[0] >= WINDOW_SECONDS:
            timestamps.popleft()

        if len(timestamps) >= MAX_REQUESTS:
            retry_after = max(1, int(WINDOW_SECONDS - (now - timestamps[0])))
        else:
            timestamps.append(now)

    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Chat request limit reached. Please try again shortly.",
            headers={"Retry-After": str(retry_after)},
        )
