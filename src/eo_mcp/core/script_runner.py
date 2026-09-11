"""Agentic Geospatial Python Script Runner.

Provides AI agents with an execution sandbox pre-loaded with geospatial
libraries (rasterio, numpy, shapely, pystac) to run custom analytical pipelines.
"""

import sys
import io
import traceback
from typing import Dict, Any


def execute_geospatial_script(script_code: str, custom_context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute an agent-generated Python geospatial script in an isolated namespace.

    Args:
        script_code: Python source code string.
        custom_context: Optional dictionary of variables to inject into the script scope.

    Returns:
        Dict containing success status, stdout, stderr, and exported result variables.
    """
    # Build safe execution scope with geospatial imports preloaded
    scope = {
        "__name__": "__agent_exec__",
        "__doc__": None,
    }

    # Pre-inject common libraries if available
    try:
        import numpy as np
        scope["np"] = np
        scope["numpy"] = np
    except ImportError:
        pass

    try:
        import rasterio
        scope["rasterio"] = rasterio
    except ImportError:
        pass

    try:
        import shapely
        scope["shapely"] = shapely
    except ImportError:
        pass

    if custom_context:
        scope.update(custom_context)

    # Capture stdout / stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    redirected_stdout = io.StringIO()
    redirected_stderr = io.StringIO()

    sys.stdout = redirected_stdout
    sys.stderr = redirected_stderr

    success = False
    error_msg = None
    output_variables = {}

    try:
        exec(script_code, scope)
        success = True
        
        # Extract variables produced by the script that are serializable
        for k, v in scope.items():
            if k.startswith("_") or k in ["np", "numpy", "rasterio", "shapely"]:
                continue
            if isinstance(v, (int, float, str, bool, list, dict)):
                output_variables[k] = v
    except Exception as exc:
        success = False
        error_msg = f"{type(exc).__name__}: {str(exc)}\n{traceback.format_exc()}"
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return {
        "success": success,
        "stdout": redirected_stdout.getvalue(),
        "stderr": redirected_stderr.getvalue(),
        "error": error_msg,
        "results": output_variables
    }
