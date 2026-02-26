"""bot/planner.py — Intent planner for Clawpx4.

The planner inspects the user's message and decides which tool (if any)
should handle it, or whether to fall back to the LLM for a free-form reply.

Tool routing uses simple keyword/pattern matching — no extra model call needed,
keeping RAM usage low on Termux devices.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Plan:
    """Describes what the bot should do in response to a user message."""

    action: str  # "tool" | "llm" | "command"
    tool_name: Optional[str] = None
    tool_kwargs: Dict[str, Any] = None
    command: Optional[str] = None  # e.g. "reset", "help", "status"

    def __post_init__(self) -> None:
        if self.tool_kwargs is None:
            self.tool_kwargs = {}


# ---------------------------------------------------------------------------
# Keyword → tool routing table
# ---------------------------------------------------------------------------
# Each entry: (compiled regex, tool_name, kwarg_builder)
# kwarg_builder receives the regex match object and the original message.

def _calc_kwargs(match: re.Match, message: str) -> Dict[str, Any]:
    return {"expression": message.strip()}


def _search_kwargs(match: re.Match, message: str) -> Dict[str, Any]:
    query = re.sub(r"(?i)^(search|look up|find|google|web)\s*(for\s*)?", "", message).strip()
    return {"query": query or message.strip()}


def _file_read_kwargs(match: re.Match, message: str) -> Dict[str, Any]:
    path = match.group(1).strip() if match.lastindex and match.group(1) else ""
    return {"action": "read", "path": path}


def _file_write_kwargs(match: re.Match, message: str) -> Dict[str, Any]:
    return {"action": "write", "path": "", "content": message}


def _shell_kwargs(match: re.Match, message: str) -> Dict[str, Any]:
    cmd = re.sub(r"(?i)^(run|exec(ute)?|shell)\s*:?\s*", "", message).strip()
    return {"command": cmd}


_ROUTING_TABLE = [
    # Calculator — matches expressions like "2 + 2", "sqrt(9)", "calc ..."
    (re.compile(r"(?i)(^calc(ulate)?\s+|\d[\d\s\+\-\*\/\(\)\.\^%]+\d)"), "calculator", _calc_kwargs),
    # File read
    (re.compile(r"(?i)(read|open|show)\s+file\s+(.+)"), "file_manager", _file_read_kwargs),
    # Shell
    (re.compile(r"(?i)^(run|exec(ute)?|shell)\s*:"), "shell", _shell_kwargs),
    # Web search — must come after shell to avoid greedy match
    (re.compile(r"(?i)^(search|look up|find|google|web)\b"), "web_search", _search_kwargs),
]

# ---------------------------------------------------------------------------
# Bot commands (messages starting with /)
# ---------------------------------------------------------------------------
_COMMANDS: Dict[str, str] = {
    "/start": "start",
    "/help": "help",
    "/reset": "reset",
    "/status": "status",
}


class Planner:
    """Routes a user message to a :class:`Plan`."""

    def plan(self, message: str) -> Plan:
        """Analyse *message* and return the appropriate :class:`Plan`.

        Priority order:
        1. Telegram /commands
        2. Keyword-based tool routing
        3. Fall back to LLM
        """
        text = message.strip()

        # 1. /commands
        for cmd_prefix, cmd_name in _COMMANDS.items():
            if text.lower().startswith(cmd_prefix):
                return Plan(action="command", command=cmd_name)

        # 2. Tool routing
        for pattern, tool_name, kwarg_builder in _ROUTING_TABLE:
            match = pattern.search(text)
            if match:
                return Plan(
                    action="tool",
                    tool_name=tool_name,
                    tool_kwargs=kwarg_builder(match, text),
                )

        # 3. LLM fallback
        return Plan(action="llm")


# Module-level singleton
_planner: Optional[Planner] = None


def get_planner() -> Planner:
    """Return the module-level :class:`Planner` singleton."""
    global _planner
    if _planner is None:
        _planner = Planner()
    return _planner
