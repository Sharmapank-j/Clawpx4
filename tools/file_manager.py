"""tools/file_manager.py — Sandboxed file read/write tool.

Only paths under FILE_MANAGER_ALLOWED_DIRS are accessible.
Default allowed directories: /sdcard/clawpx4_files, /tmp.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, List

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

_DEFAULT_ALLOWED = "/sdcard/clawpx4_files,/tmp"
_MAX_READ_BYTES = 50_000  # 50 KB cap for low-RAM devices


def _allowed_dirs() -> List[Path]:
    raw = os.getenv("FILE_MANAGER_ALLOWED_DIRS", _DEFAULT_ALLOWED)
    return [Path(d.strip()).resolve() for d in raw.split(",") if d.strip()]


def _is_safe_path(path: Path) -> bool:
    resolved = path.resolve()
    return any(
        resolved == allowed or allowed in resolved.parents
        for allowed in _allowed_dirs()
    )


class FileManagerTool(BaseTool):
    """Read or write files within permitted directories."""

    name = "file_manager"
    description = "Read or write a file within the allowed directories."

    def __init__(self) -> None:
        self.enabled = (
            os.getenv("TOOL_FILE_MANAGER_ENABLED", "true").lower() != "false"
        )

    def run(
        self,
        action: str = "read",
        path: str = "",
        content: str = "",
        **kwargs: Any,
    ) -> ToolResult:
        """Perform a file operation.

        Args:
            action:  ``"read"`` or ``"write"``.
            path:    File path (must be under an allowed directory).
            content: Content to write (only for ``action="write"``).

        Returns:
            :class:`~tools.base.ToolResult`.
        """
        if not path:
            return ToolResult(success=False, output="", error="No file path provided.")

        target = Path(path)
        if not _is_safe_path(target):
            allowed = ", ".join(str(d) for d in _allowed_dirs())
            return ToolResult(
                success=False,
                output="",
                error=f"Access denied. Allowed directories: {allowed}",
            )

        if action == "read":
            return self._read(target)
        if action == "write":
            return self._write(target, content)
        return ToolResult(
            success=False, output="", error=f"Unknown action: '{action}'"
        )

    # ------------------------------------------------------------------

    def _read(self, path: Path) -> ToolResult:
        if not path.exists():
            return ToolResult(success=False, output="", error=f"File not found: {path}")
        if not path.is_file():
            return ToolResult(success=False, output="", error=f"Not a file: {path}")
        try:
            data = path.read_bytes()
        except OSError as exc:
            return ToolResult(success=False, output="", error=str(exc))

        if len(data) > _MAX_READ_BYTES:
            data = data[:_MAX_READ_BYTES]
            suffix = f"\n\n[Truncated at {_MAX_READ_BYTES} bytes]"
        else:
            suffix = ""

        try:
            text = data.decode("utf-8") + suffix
        except UnicodeDecodeError:
            text = f"[Binary file — {len(data)} bytes]"

        return ToolResult(success=True, output=text)

    def _write(self, path: Path, content: str) -> ToolResult:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            return ToolResult(success=False, output="", error=str(exc))
        return ToolResult(success=True, output=f"Written {len(content)} characters to {path}")
