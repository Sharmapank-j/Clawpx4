"""tools/calculator.py — Safe arithmetic evaluation tool.

Uses Python's ast module to evaluate mathematical expressions without
calling eval() on arbitrary code.
"""

from __future__ import annotations

import ast
import math
import operator
import os
from typing import Any, Union

from tools.base import BaseTool, ToolResult

# Supported operators
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}

# Supported functions (name → callable)
_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "ceil": math.ceil,
    "floor": math.floor,
    "pi": math.pi,
    "e": math.e,
}

Number = Union[int, float]


def _safe_eval(node: ast.AST) -> Number:
    """Recursively evaluate an AST node — raises ValueError for unsupported ops."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Name) and node.id in _FUNCTIONS:
        val = _FUNCTIONS[node.id]
        if callable(val):
            raise ValueError(f"'{node.id}' is a function, not a constant.")
        return val  # type: ignore[return-value]
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _OPERATORS[op_type](left, right)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_safe_eval(node.operand)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
            raise ValueError("Only built-in math functions are allowed.")
        fn = _FUNCTIONS[node.func.id]
        if not callable(fn):
            raise ValueError(f"'{node.func.id}' is not callable.")
        args = [_safe_eval(a) for a in node.args]
        return fn(*args)  # type: ignore[operator]
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


class CalculatorTool(BaseTool):
    """Evaluate safe arithmetic and trigonometric expressions."""

    name = "calculator"
    description = "Evaluate a mathematical expression (e.g. '2 + 2', 'sqrt(9)')."

    def __init__(self) -> None:
        self.enabled = os.getenv("TOOL_CALCULATOR_ENABLED", "true").lower() != "false"

    def run(self, expression: str = "", **kwargs: Any) -> ToolResult:
        """Evaluate *expression* and return the result.

        Args:
            expression: A mathematical expression string.

        Returns:
            :class:`~tools.base.ToolResult` with the numeric result as a string.
        """
        if not expression:
            return ToolResult(success=False, output="", error="No expression provided.")

        # Strip common prefixes the planner may leave in (case-insensitive)
        for prefix in ("calculate", "calc", "="):
            if expression.strip().lower().startswith(prefix):
                expression = expression.strip()[len(prefix):].strip()
                break

        try:
            tree = ast.parse(expression.strip(), mode="eval")
            result = _safe_eval(tree)
        except (SyntaxError, ValueError, ZeroDivisionError) as exc:
            return ToolResult(success=False, output="", error=str(exc))

        # Format: avoid unnecessary ".0" for whole numbers
        formatted = str(int(result)) if isinstance(result, float) and result.is_integer() else str(result)
        return ToolResult(success=True, output=f"{expression.strip()} = {formatted}")
