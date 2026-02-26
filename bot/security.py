"""bot/security.py — Access control and rate limiting.

Reads configuration from environment variables:
    ALLOWED_USER_IDS  – comma-separated Telegram user IDs allowed to use the
                        bot; leave empty to allow everyone.
    RATE_LIMIT_RPM    – max requests per user per minute (default: 10).
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional


class SecurityGuard:
    """Enforces user allowlist and per-user rate limiting."""

    def __init__(
        self,
        allowed_ids: Optional[str] = None,
        rate_limit_rpm: int = 10,
    ) -> None:
        raw = allowed_ids or os.getenv("ALLOWED_USER_IDS", "")
        self._allowed: set[int] = (
            {int(uid.strip()) for uid in raw.split(",") if uid.strip()}
            if raw.strip()
            else set()
        )
        self._rate_limit_rpm = int(os.getenv("RATE_LIMIT_RPM", rate_limit_rpm))
        # Maps user_id → deque of request timestamps (unix seconds)
        self._timestamps: Dict[int, Deque[float]] = defaultdict(deque)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_allowed(self, user_id: int) -> bool:
        """Return True if *user_id* is permitted to use the bot."""
        if not self._allowed:
            return True
        return user_id in self._allowed

    def check_rate_limit(self, user_id: int) -> bool:
        """Return True if *user_id* is within their rate limit.

        Records the current request timestamp.  Returns False if the user
        has exceeded :attr:`_rate_limit_rpm` requests in the last 60 seconds.
        """
        now = time.monotonic()
        window = self._timestamps[user_id]
        cutoff = now - 60.0
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= self._rate_limit_rpm:
            return False
        window.append(now)
        return True

    def validate(self, user_id: int) -> tuple[bool, str]:
        """Combine allowlist and rate-limit checks.

        Returns:
            ``(True, "")`` if the request is permitted.
            ``(False, reason_string)`` otherwise.
        """
        if not self.is_allowed(user_id):
            return False, "You are not authorised to use this bot."
        if not self.check_rate_limit(user_id):
            return False, "Too many requests. Please slow down."
        return True, ""


# Module-level singleton
_guard: Optional[SecurityGuard] = None


def get_guard() -> SecurityGuard:
    """Return the module-level :class:`SecurityGuard` singleton."""
    global _guard
    if _guard is None:
        _guard = SecurityGuard()
    return _guard
