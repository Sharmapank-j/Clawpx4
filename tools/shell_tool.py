"""tools/shell_tool.py — Safe shell command executor.

Only executes commands whose base name appears in the SHELL_ALLOWED_COMMANDS
environment variable (default: ls,cat,pwd,echo,date,uname).

The tool is disabled by default and must be explicitly enabled:
    TOOL_SHELL_ENABLED=true
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
from typing import Any

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

_DEFAULT_ALLOWED = "ls,cat,pwd,echo,date,uname"


class ShellTool(BaseTool):
    """Execute a shell command from an explicit allowlist."""

    name = "shell"
    description = "Run a whitelisted shell command and return its output."

    def __init__(self) -> None:
        raw = os.getenv("SHELL_ALLOWED_COMMANDS", _DEFAULT_ALLOWED)
        self._allowed: set[str] = {
            c.strip() for c in raw.split(",") if c.strip()
        }
        self.enabled = os.getenv("TOOL_SHELL_ENABLED", "false").lower() == "true"

    # ------------------------------------------------------------------

    def run(self, command: str = "", **kwargs: Any) -> ToolResult:
        """Execute *command* if it is on the allowlist.

        Args:
            command: The shell command string to execute.

        Returns:
            :class:`~tools.base.ToolResult` with stdout on success.
        """
        if not command:
            return ToolResult(success=False, output="", error="No command provided.")

        try:
            parts = shlex.split(command)
        except ValueError as exc:
            return ToolResult(success=False, output="", error=f"Invalid command: {exc}")

        base_cmd = os.path.basename(parts[0]) if parts else ""
        if base_cmd not in self._allowed:
            return ToolResult(
                success=False,
                output="",
                error=(
                    f"Command '{base_cmd}' is not allowed. "
                    f"Allowed commands: {', '.join(sorted(self._allowed))}"
                ),
            )

        logger.info("ShellTool: executing %s", parts)
        try:
            result = subprocess.run(
                parts,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error="Command timed out.")
        except FileNotFoundError:
            return ToolResult(
                success=False,
                output="",
                error=f"Command not found: '{parts[0]}'",
            )

        if result.returncode != 0:
            return ToolResult(
                success=False,
                output=result.stdout,
                error=result.stderr.strip() or f"Exit code {result.returncode}",
            )

        return ToolResult(success=True, output=result.stdout.strip())
