"""tests/test_security.py — Unit tests for bot security guard."""

from __future__ import annotations

import time

import pytest
from bot.security import SecurityGuard


class TestSecurityGuard:
    def test_allow_all_when_no_allowlist(self):
        guard = SecurityGuard(allowed_ids="", rate_limit_rpm=100)
        assert guard.is_allowed(12345)
        assert guard.is_allowed(99999)

    def test_allowlist_permits_listed_user(self):
        guard = SecurityGuard(allowed_ids="111,222", rate_limit_rpm=100)
        assert guard.is_allowed(111)
        assert guard.is_allowed(222)

    def test_allowlist_blocks_unlisted_user(self):
        guard = SecurityGuard(allowed_ids="111,222", rate_limit_rpm=100)
        assert not guard.is_allowed(333)

    def test_rate_limit_allows_within_limit(self):
        guard = SecurityGuard(allowed_ids="", rate_limit_rpm=5)
        for _ in range(5):
            assert guard.check_rate_limit(1)

    def test_rate_limit_blocks_over_limit(self):
        guard = SecurityGuard(allowed_ids="", rate_limit_rpm=3)
        for _ in range(3):
            guard.check_rate_limit(2)
        assert not guard.check_rate_limit(2)

    def test_validate_allowed_user(self):
        guard = SecurityGuard(allowed_ids="55", rate_limit_rpm=100)
        ok, reason = guard.validate(55)
        assert ok
        assert reason == ""

    def test_validate_blocked_user(self):
        guard = SecurityGuard(allowed_ids="55", rate_limit_rpm=100)
        ok, reason = guard.validate(99)
        assert not ok
        assert "authorised" in reason.lower()

    def test_validate_rate_limited_user(self):
        guard = SecurityGuard(allowed_ids="", rate_limit_rpm=1)
        guard.validate(7)  # first call — ok
        ok, reason = guard.validate(7)  # second call — blocked
        assert not ok
        assert "slow down" in reason.lower()

    def test_rate_limit_independent_per_user(self):
        guard = SecurityGuard(allowed_ids="", rate_limit_rpm=1)
        guard.check_rate_limit(10)  # user 10 exhausted
        assert guard.check_rate_limit(20)  # user 20 still ok
