"""Unit tests for agentic geospatial script runner sandbox."""

from eo_mcp.core.script_runner import execute_geospatial_script


def test_script_runner_basic():
    code = """
x = 10
y = 20
total = x + y
print(f"Computed total: {total}")
"""
    result = execute_geospatial_script(code)
    assert result["success"] is True
    assert "Computed total: 30" in result["stdout"]
    assert result["results"]["total"] == 30


def test_script_runner_numpy_preloaded():
    code = """
import numpy as np
arr = np.array([1, 2, 3, 4])
arr_mean = float(arr.mean())
"""
    result = execute_geospatial_script(code)
    assert result["success"] is True
    assert result["results"]["arr_mean"] == 2.5


def test_script_runner_catches_errors():
    code = """
undefined_variable + 5
"""
    result = execute_geospatial_script(code)
    assert result["success"] is False
    assert "NameError" in result["error"]
