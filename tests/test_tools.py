"""tests/test_tools.py — Unit tests for the tools layer."""

from __future__ import annotations

import pytest
from tools.calculator import CalculatorTool
from tools.base import ToolResult


class TestCalculatorTool:
    def setup_method(self):
        self.tool = CalculatorTool()

    def test_basic_addition(self):
        result = self.tool.run(expression="2 + 2")
        assert result.success
        assert "4" in result.output

    def test_subtraction(self):
        result = self.tool.run(expression="10 - 3")
        assert result.success
        assert "7" in result.output

    def test_multiplication(self):
        result = self.tool.run(expression="6 * 7")
        assert result.success
        assert "42" in result.output

    def test_division(self):
        result = self.tool.run(expression="10 / 4")
        assert result.success
        assert "2.5" in result.output

    def test_power(self):
        result = self.tool.run(expression="2 ** 8")
        assert result.success
        assert "256" in result.output

    def test_sqrt_function(self):
        result = self.tool.run(expression="sqrt(16)")
        assert result.success
        assert "4" in result.output

    def test_division_by_zero(self):
        result = self.tool.run(expression="1 / 0")
        assert not result.success
        assert result.error

    def test_empty_expression(self):
        result = self.tool.run(expression="")
        assert not result.success

    def test_invalid_expression(self):
        result = self.tool.run(expression="import os")
        assert not result.success

    def test_calc_prefix_stripped(self):
        result = self.tool.run(expression="calc 3 + 3")
        assert result.success
        assert "6" in result.output

    def test_tool_result_is_toolresult(self):
        result = self.tool.run(expression="1+1")
        assert isinstance(result, ToolResult)

    def test_tool_name(self):
        assert self.tool.name == "calculator"

    def test_tool_describe(self):
        d = self.tool.describe()
        assert d["name"] == "calculator"
        assert "description" in d
