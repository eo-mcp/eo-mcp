"""Unit tests for Copernicus DEM terrain analysis."""

import numpy as np
from eo_mcp.core.dem import compute_slope_and_aspect, summarize_terrain


def test_flat_terrain_slope_zero():
    # Constant elevation surface (100m everywhere) -> slope should be 0
    dem = np.full((10, 10), 100.0, dtype=np.float32)
    slope, aspect = compute_slope_and_aspect(dem, cellsize_m=30.0)
    assert np.allclose(slope, 0.0)


def test_summarize_terrain():
    dem = np.array([[100.0, 150.0], [100.0, 150.0]], dtype=np.float32)
    summary = summarize_terrain(dem, cellsize_m=30.0)
    assert summary["min_elevation_m"] == 100.0
    assert summary["max_elevation_m"] == 150.0
    assert summary["mean_elevation_m"] == 125.0
    assert summary["mean_slope_degrees"] > 0.0
