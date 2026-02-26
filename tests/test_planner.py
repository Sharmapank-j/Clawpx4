"""tests/test_planner.py — Unit tests for the intent planner."""

from __future__ import annotations

import pytest
from bot.planner import Planner, Plan


@pytest.fixture
def planner():
    return Planner()


class TestPlanner:
    def test_slash_start_is_command(self, planner):
        plan = planner.plan("/start")
        assert plan.action == "command"
        assert plan.command == "start"

    def test_slash_help_is_command(self, planner):
        plan = planner.plan("/help")
        assert plan.action == "command"
        assert plan.command == "help"

    def test_slash_reset_is_command(self, planner):
        plan = planner.plan("/reset")
        assert plan.action == "command"
        assert plan.command == "reset"

    def test_slash_status_is_command(self, planner):
        plan = planner.plan("/status")
        assert plan.action == "command"
        assert plan.command == "status"

    def test_search_routes_to_web_search(self, planner):
        plan = planner.plan("search Python tutorials")
        assert plan.action == "tool"
        assert plan.tool_name == "web_search"
        assert "Python tutorials" in plan.tool_kwargs["query"]

    def test_web_prefix_routes_to_web_search(self, planner):
        plan = planner.plan("web latest AI news")
        assert plan.action == "tool"
        assert plan.tool_name == "web_search"

    def test_arithmetic_routes_to_calculator(self, planner):
        plan = planner.plan("12 + 34")
        assert plan.action == "tool"
        assert plan.tool_name == "calculator"

    def test_calc_prefix_routes_to_calculator(self, planner):
        plan = planner.plan("calc sqrt(49)")
        assert plan.action == "tool"
        assert plan.tool_name == "calculator"

    def test_shell_run_routes_to_shell(self, planner):
        plan = planner.plan("run: ls -la")
        assert plan.action == "tool"
        assert plan.tool_name == "shell"

    def test_file_read_routes_to_file_manager(self, planner):
        plan = planner.plan("read file /tmp/test.txt")
        assert plan.action == "tool"
        assert plan.tool_name == "file_manager"

    def test_plain_text_falls_back_to_llm(self, planner):
        plan = planner.plan("Tell me about the solar system")
        assert plan.action == "llm"

    def test_empty_message_falls_back_to_llm(self, planner):
        plan = planner.plan("")
        assert plan.action == "llm"

    def test_plan_has_empty_tool_kwargs_by_default(self, planner):
        plan = planner.plan("Hello there")
        assert isinstance(plan.tool_kwargs, dict)
