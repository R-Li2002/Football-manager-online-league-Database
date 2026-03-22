from __future__ import annotations

import time
from collections import deque


class InMemoryRateLimiter:
    def __init__(self):
        self._user_cooldowns: dict[str, float] = {}
        self._group_windows: dict[str, deque[float]] = {}

    def check_user_cooldown(self, key: str, cooldown_seconds: int) -> tuple[bool, int]:
        now = time.time()
        last_ts = self._user_cooldowns.get(key, 0.0)
        retry_after = int(max(0, cooldown_seconds - (now - last_ts)))
        if last_ts and retry_after > 0:
            return False, retry_after
        self._user_cooldowns[key] = now
        return True, 0

    def check_group_window(self, key: str, limit_per_minute: int) -> tuple[bool, int]:
        now = time.time()
        window = self._group_windows.setdefault(key, deque())
        while window and now - window[0] >= 60:
            window.popleft()
        if len(window) >= max(1, limit_per_minute):
            retry_after = int(max(1, 60 - (now - window[0])))
            return False, retry_after
        window.append(now)
        return True, 0
