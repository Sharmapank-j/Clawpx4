"""bot/dispatcher.py — Tool dispatcher for Clawpx4.

The dispatcher holds a registry of :class:`~tools.base.BaseTool` instances and
routes :class:`~bot.planner.Plan` objects to the correct tool.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Optional

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class Dispatcher:
    """Registry and router for all available tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    # ------------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------------

    def register(self, tool: BaseTool) -> None:
        """Register *tool* under its :attr:`~tools.base.BaseTool.name`."""
        if not tool.name:
            raise ValueError(f"Tool {type(tool).__name__} has no name set.")
        self._tools[tool.name] = tool
        logger.debug("Dispatcher: registered tool '%s'", tool.name)

    def available_tools(self) -> Dict[str, str]:
        """Return a mapping of tool name → description for enabled tools."""
        return {
            name: t.description
            for name, t in self._tools.items()
            if t.is_available()
        }

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, tool_name: str, **kwargs) -> ToolResult:
        """Run the named tool with the provided keyword arguments.

        Args:
            tool_name: The :attr:`~tools.base.BaseTool.name` of the tool.
            **kwargs:  Arguments forwarded to the tool's :meth:`run` method.

        Returns:
            A :class:`~tools.base.ToolResult`.
        """
        tool = self._tools.get(tool_name)
        if tool is None:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown tool: '{tool_name}'",
            )
        if not tool.is_available():
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{tool_name}' is currently disabled.",
            )
        try:
            return tool.run(**kwargs)
        except Exception as exc:
            logger.exception("Tool '%s' raised an exception", tool_name)
            return ToolResult(
                success=False,
                output="",
                error=str(exc),
            )


# ---------------------------------------------------------------------------
# Default dispatcher — auto-registers all enabled tools
# ---------------------------------------------------------------------------

def _build_default_dispatcher() -> Dispatcher:
    """Instantiate and register all tools according to env-var configuration."""
    from tools.calculator import CalculatorTool
    from tools.web_search import WebSearchTool
    from tools.file_manager import FileManagerTool
    from tools.shell_tool import ShellTool

    dispatcher = Dispatcher()

    if os.getenv("TOOL_CALCULATOR_ENABLED", "true").lower() != "false":
        dispatcher.register(CalculatorTool())

    if os.getenv("TOOL_WEB_SEARCH_ENABLED", "true").lower() != "false":
        dispatcher.register(WebSearchTool())

    if os.getenv("TOOL_FILE_MANAGER_ENABLED", "true").lower() != "false":
        dispatcher.register(FileManagerTool())

    if os.getenv("TOOL_SHELL_ENABLED", "false").lower() == "true":
        dispatcher.register(ShellTool())

    return dispatcher


_dispatcher: Optional[Dispatcher] = None


def get_dispatcher() -> Dispatcher:
    """Return the module-level :class:`Dispatcher` singleton."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = _build_default_dispatcher()
    return _dispatcher
