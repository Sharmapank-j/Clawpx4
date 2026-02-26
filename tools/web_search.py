"""tools/web_search.py — DuckDuckGo web search tool.

Uses the duckduckgo-search library which makes no API key required and works
well on low-bandwidth / Termux environments.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    """Search the web using DuckDuckGo and return a brief summary."""

    name = "web_search"
    description = "Search the web for a query and return top results."

    def __init__(self) -> None:
        self.enabled = os.getenv("TOOL_WEB_SEARCH_ENABLED", "true").lower() != "false"
        self._max_results = 5

    def run(self, query: str = "", **kwargs: Any) -> ToolResult:
        """Perform a DuckDuckGo search for *query*.

        Args:
            query: The search query string.

        Returns:
            :class:`~tools.base.ToolResult` with formatted search results.
        """
        if not query:
            return ToolResult(success=False, output="", error="No query provided.")

        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return ToolResult(
                success=False,
                output="",
                error="duckduckgo-search is not installed. Run: pip install duckduckgo-search",
            )

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=self._max_results))
        except Exception as exc:
            logger.warning("DuckDuckGo search failed: %s", exc)
            return ToolResult(success=False, output="", error=f"Search failed: {exc}")

        if not results:
            return ToolResult(success=True, output="No results found.")

        lines = [f"🔍 Results for: *{query}*\n"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            url = r.get("href", "")
            body = r.get("body", "")
            snippet = body[:200].replace("\n", " ") + ("…" if len(body) > 200 else "")
            lines.append(f"{i}. *{title}*\n   {snippet}\n   {url}")

        return ToolResult(success=True, output="\n\n".join(lines))
