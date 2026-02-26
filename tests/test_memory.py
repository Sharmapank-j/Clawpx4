"""tests/test_memory.py — Unit tests for SQLite memory store."""

from __future__ import annotations

import os
import tempfile

import pytest
from memory.sqlite_store import SQLiteStore


@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    return SQLiteStore(db_path=db_path)


class TestSQLiteStore:
    def test_add_and_get_history(self, store):
        store.add_message("user1", "user", "Hello")
        store.add_message("user1", "assistant", "Hi there!")
        history = store.get_history("user1")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"

    def test_history_limit(self, store):
        for i in range(10):
            store.add_message("user2", "user", f"msg {i}")
        history = store.get_history("user2", limit=5)
        assert len(history) == 5

    def test_clear_history(self, store):
        store.add_message("user3", "user", "Test")
        store.clear_history("user3")
        assert store.get_history("user3") == []

    def test_history_isolation(self, store):
        store.add_message("alice", "user", "Alice's message")
        store.add_message("bob", "user", "Bob's message")
        assert len(store.get_history("alice")) == 1
        assert store.get_history("alice")[0]["content"] == "Alice's message"

    def test_kv_set_and_get(self, store):
        store.set("my_key", {"value": 42})
        result = store.get("my_key")
        assert result == {"value": 42}

    def test_kv_default(self, store):
        assert store.get("nonexistent", default="fallback") == "fallback"

    def test_kv_overwrite(self, store):
        store.set("key", "first")
        store.set("key", "second")
        assert store.get("key") == "second"

    def test_kv_delete(self, store):
        store.set("to_delete", 1)
        store.delete("to_delete")
        assert store.get("to_delete") is None

    def test_history_order_oldest_first(self, store):
        store.add_message("user4", "user", "first")
        store.add_message("user4", "assistant", "second")
        store.add_message("user4", "user", "third")
        history = store.get_history("user4")
        assert history[0]["content"] == "first"
        assert history[-1]["content"] == "third"
