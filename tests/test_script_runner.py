"""Unit tests for agentic geospatial script creation, AST validation, and sandbox runner."""

import pytest
from eo_mcp.core.script_runner import (
    validate_script_ast,
    generate_geospatial_script,
    synthesize_pipeline_script,
    execute_geospatial_script,
)


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
    assert result["execution_time_seconds"] >= 0.0


def test_script_runner_numpy_preloaded():
    code = """
import numpy as np
arr = np.array([1, 2, 3, 4])
arr_mean = float(arr.mean())
"""
    result = execute_geospatial_script(code)
    assert result["success"] is True
    assert result["results"]["arr_mean"] == 2.5


def test_script_runner_catches_runtime_errors():
    code = """
undefined_variable + 5
"""
    result = execute_geospatial_script(code)
    assert result["success"] is False
    assert "NameError" in result["error"]


def test_ast_validator_clean_code():
    code = """
import numpy as np
import rasterio
from shapely.geometry import Point

p = Point(10.0, 20.0)
coords = [p.x, p.y]
"""
    res = validate_script_ast(code)
    assert res["valid"] is True
    assert len(res["errors"]) == 0


def test_ast_validator_blocks_forbidden_modules():
    code = """
import subprocess
subprocess.run(["ls", "-la"])
"""
    res = validate_script_ast(code)
    assert res["valid"] is False
    assert any("subprocess" in err for err in res["errors"])

    # Test blocked in execution
    exec_res = execute_geospatial_script(code)
    assert exec_res["success"] is False
    assert "ASTValidationError" in exec_res["error"]


def test_ast_validator_blocks_eval_and_exec():
    code = """
eval("1 + 1")
"""
    res = validate_script_ast(code)
    assert res["valid"] is False
    assert any("eval()" in err for err in res["errors"])


def test_generate_geospatial_script_standalone():
    for task in ["coastal_water_quality", "inundation_model", "maritime_patrol"]:
        script = generate_geospatial_script(
            task_type=task,
            bbox=[22.70, 38.80, 22.95, 38.95],
            datetime_range="2024-06-01/2024-06-30",
            mode="standalone"
        )
        assert isinstance(script, str)
        assert len(script) > 100
        # Check that generated script passes AST validation
        ast_check = validate_script_ast(script)
        assert ast_check["valid"] is True, f"Generated script for {task} failed AST: {ast_check['errors']}"


def test_generate_geospatial_script_sdk():
    script = generate_geospatial_script(
        task_type="coastal_water_quality",
        bbox=[22.70, 38.80, 22.95, 38.95],
        mode="sdk"
    )
    assert "from eo_mcp.core.water_quality import analyze_coastal_water_quality" in script
    ast_check = validate_script_ast(script)
    assert ast_check["valid"] is True


def test_synthesize_pipeline_script():
    script = synthesize_pipeline_script(
        recipe_name="coastal_water_quality_eutrophication",
        bbox=[22.70, 38.80, 22.95, 38.95],
        output_format="standalone"
    )
    assert isinstance(script, str)
    assert "pystac_client" in script or "numpy" in script
    ast_check = validate_script_ast(script)
    assert ast_check["valid"] is True
