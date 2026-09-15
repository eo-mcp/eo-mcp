"""Unit tests for sea level rise and connected flood inundation modeling."""

import numpy as np
import pytest
from eo_mcp.core.inundation import (
    simulate_connected_inundation,
    IPCC_AR6_SCENARIOS
)


def test_ipcc_scenarios_exist():
    assert "SSP1-2.6" in IPCC_AR6_SCENARIOS
    assert "SSP2-4.5" in IPCC_AR6_SCENARIOS
    assert "SSP5-8.5" in IPCC_AR6_SCENARIOS
    assert IPCC_AR6_SCENARIOS["SSP5-8.5"]["slr_median_m"] == 0.77


def test_connected_inundation_disconnected_depression():
    """
    Test that an inland depression below sea level that is isolated from the ocean
    is NOT falsely flooded by the connected flood-fill algorithm.
    """
    # Create 20x20 terrain
    # Ocean on columns 0-3 (elevation -1.0m)
    # Coastal ridge on columns 4-6 (elevation +5.0m)
    # Inland depression on columns 7-10 (elevation +0.5m)
    # High inland on columns 11-19 (elevation +10.0m)
    dem = np.full((20, 20), 10.0, dtype=np.float32)
    dem[:, :4] = -1.0
    dem[:, 4:7] = 5.0
    dem[:, 7:11] = 0.5

    # Simulate sea level rise of +1.0m (total water level = 1.0m)
    # In a naive bathtub model, the depression at 0.5m would falsely flood.
    # But in the connected model, the ridge at 5.0m blocks the ocean, so depression must stay dry!
    flooded_mask, depth_grid, metrics = simulate_connected_inundation(
        dem_array=dem,
        water_level_rise_m=1.0,
        storm_surge_m=0.0,
        cellsize_m=30.0,
        sea_level_datum_m=0.0
    )

    # Confirm ocean cells are connected, but isolated depression (columns 7-10) is NOT flooded
    assert np.all(flooded_mask[:, 7:11] == False)
    assert metrics["inundated_land_area_ha"] == 0.0


def test_connected_inundation_breached_ridge():
    """
    Test that when the surge exceeds the ridge height, flood waters penetrate and submerge land.
    """
    dem = np.full((20, 20), 10.0, dtype=np.float32)
    dem[:, :4] = -1.0
    dem[:, 4:7] = 1.5   # 1.5m low coastal ridge
    dem[:, 7:11] = 0.5  # 0.5m lowland

    # Water level rise + surge = 1.0m + 1.0m = 2.0m (overtops the 1.5m ridge)
    flooded_mask, depth_grid, metrics = simulate_connected_inundation(
        dem_array=dem,
        water_level_rise_m=1.0,
        storm_surge_m=1.0,  # Total 2.0m
        cellsize_m=30.0,
        sea_level_datum_m=0.0
    )

    # Now both ridge (at 1.5m) and lowland (at 0.5m) are submerged
    assert np.all(flooded_mask[:, 4:11] == True)
    assert metrics["inundated_land_area_ha"] > 0.0
    assert metrics["max_inundation_depth_m"] == pytest.approx(1.5, abs=0.1) # 2.0 - 0.5 = 1.5m
