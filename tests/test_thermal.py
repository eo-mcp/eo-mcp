"""Unit tests for Land Surface Temperature and Urban Heat Island analysis."""

import numpy as np
import json
from eo_mcp.core.thermal import (
    calculate_land_surface_temperature,
    compute_fractional_vegetation_cover,
    compute_land_surface_emissivity,
    thermal_to_geojson,
    thermal_to_csv
)
from eo_mcp.server import analyze_urban_heat_island


def test_fvc_and_emissivity():
    ndvi = np.array([[-0.1, 0.15], [0.35, 0.7]], dtype=np.float32)
    fvc = compute_fractional_vegetation_cover(ndvi)
    assert np.all(fvc >= 0.0) and np.all(fvc <= 1.0)

    emissivity = compute_land_surface_emissivity(fvc, ndvi)
    assert emissivity[0, 0] == 0.995  # Water
    assert emissivity[0, 1] == 0.960  # Soil
    assert emissivity[1, 1] == 0.985  # Dense Veg


def test_calculate_land_surface_temperature():
    rows, cols = 20, 20
    red = np.full((rows, cols), 1200, dtype=np.float32)
    nir = np.full((rows, cols), 2800, dtype=np.float32)
    thermal_tb = np.full((rows, cols), 302.0, dtype=np.float32)  # ~28.85 °C in Kelvin

    # Inject urban heat island in center
    thermal_tb[8:12, 8:12] = 312.0  # ~38.85 °C

    results = calculate_land_surface_temperature(
        thermal_radiance=thermal_tb,
        red_band=red,
        nir_band=nir,
        cellsize_m=30.0
    )

    assert results["mean_lst_celsius"] > 20.0
    assert results["max_lst_celsius"] > results["mean_lst_celsius"]
    assert results["uhi_intensity_celsius"] > 0.0
    assert results["thermal_hotspot_area_ha"] > 0.0


def test_thermal_formatters():
    rows, cols = 10, 10
    res = calculate_land_surface_temperature(
        thermal_radiance=np.full((rows, cols), 305.0, dtype=np.float32),
        red_band=np.full((rows, cols), 1000, dtype=np.float32),
        nir_band=np.full((rows, cols), 2500, dtype=np.float32)
    )

    gj = thermal_to_geojson(res)
    assert gj["type"] == "FeatureCollection"

    csv_out = thermal_to_csv(res)
    assert "mean_lst" in csv_out
    assert "uhi_intensity" in csv_out


def test_server_urban_heat_island_tool():
    res_str = analyze_urban_heat_island(bbox=[2.25, 48.82, 2.35, 48.90], datetime_range="2024-06-01/2024-08-31")
    res = json.loads(res_str)
    assert "mean_lst_celsius" in res
    assert "uhi_intensity_celsius" in res

