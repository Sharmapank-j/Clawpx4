"""tools/base.py — Abstract base class for all Clawpx4 tools.

Every tool must subclass :class:`BaseTool` and implement :meth:`run`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolResult:
    """Structured result returned by every tool."""

    success: bool
    output: str
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        if self.success:
            return self.output
        return f"[Error] {self.error}"


class BaseTool(ABC):
    """Abstract base class for Clawpx4 tools.

    Subclasses must set :attr:`name` and :attr:`description`, and implement
    the :meth:`run` method.
    """

    #: Unique, lowercase, underscore-separated name used by the dispatcher.
    name: str = ""

    #: Human-readable description shown to the planner.
    description: str = ""

    #: Whether the tool is enabled (can be overridden via env var).
    enabled: bool = True

    @abstractmethod
    def run(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with the given keyword arguments.

        Returns:
            A :class:`ToolResult` describing the outcome.
        """

    def is_available(self) -> bool:
        """Return True if the tool is enabled and ready to use."""
        return self.enabled

    def describe(self) -> Dict[str, str]:
        """Return a dict describing this tool for the planner."""
        return {
            "name": self.name,
            "description": self.description,
            "enabled": str(self.enabled),
        }
