"""Tests for Topographic Wetness Index (TWI) and Terrain Ruggedness Index (TRI)."""

import numpy as np
import pytest
from eo_mcp.core.dem import (
    compute_topographic_wetness_index,
    compute_terrain_ruggedness_index,
    summarize_terrain
)


def test_compute_terrain_ruggedness_index():
    # Flat terrain should have 0 ruggedness
    flat = np.full((10, 10), 100.0, dtype=np.float32)
    tri_flat = compute_terrain_ruggedness_index(flat)
    assert np.allclose(tri_flat, 0.0)

    # Steep sloping/rugged terrain
    rugged = np.arange(100, dtype=np.float32).reshape(10, 10)
    tri_rugged = compute_terrain_ruggedness_index(rugged)
    assert np.all(tri_rugged > 0.0)


def test_compute_topographic_wetness_index():
    # Terrain with gradient
    elev = np.linspace(50, 150, 100, dtype=np.float32).reshape(10, 10)
    twi = compute_topographic_wetness_index(elev, cellsize_m=30.0)
    assert twi.shape == (10, 10)
    # TWI values in natural terrain typically fall between 2 and 20
    assert np.all(~np.isnan(twi))
    assert np.mean(twi) > 0.0


def test_summarize_terrain_with_twi_tri():
    elev = np.linspace(10, 80, 100, dtype=np.float32).reshape(10, 10)
    summary = summarize_terrain(elev, cellsize_m=30.0)
    assert "mean_twi" in summary
    assert "mean_tri_m" in summary
    assert summary["mean_twi"] > 0.0
    assert summary["mean_tri_m"] > 0.0
