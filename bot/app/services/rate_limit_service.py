from __future__ import annotations

import time
from collections import defaultdict, deque


class InMemoryRateLimitService:
    def __init__(self) -> None:
        self._cooldowns: dict[str, float] = {}
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    def check_user_cooldown(self, key: str, cooldown_seconds: int) -> tuple[bool, int]:
        now = time.time()
        expires_at = self._cooldowns.get(key, 0)
        if expires_at > now:
            return False, max(1, int(expires_at - now))

        self._cooldowns[key] = now + cooldown_seconds
        return True, 0

    def check_group_window(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        now = time.time()
        queue = self._windows[key]
        while queue and now - queue[0] > window_seconds:
            queue.popleft()

        if len(queue) >= limit:
            retry_after = max(1, int(window_seconds - (now - queue[0])))
            return False, retry_after

        queue.append(now)
        return True, 0
