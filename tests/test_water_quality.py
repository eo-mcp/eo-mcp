"""Unit tests for coastal water quality, eutrophication, and marine pollution engine."""

import numpy as np
import pytest
from eo_mcp.core.water_quality import (
    compute_ndci,
    classify_ndci_trophic_state,
    compute_ndti,
    classify_ndti_turbidity,
    estimate_spm_nechad,
    detect_thermal_plume_anomalies,
    analyze_coastal_water_quality,
    water_quality_to_geojson,
    water_quality_to_csv,
)


def test_compute_ndci_basic():
    # Low chlorophyll (red > red_edge)
    red = np.array([[0.10, 0.15], [0.12, 0.14]], dtype=np.float32)
    red_edge = np.array([[0.05, 0.08], [0.06, 0.07]], dtype=np.float32)
    ndci = compute_ndci(red_edge, red)
    assert ndci.shape == (2, 2)
    assert np.all(ndci < 0.0)

    # High chlorophyll / algal bloom (red_edge > red)
    red_edge_bloom = np.array([[0.20, 0.25], [0.22, 0.24]], dtype=np.float32)
    ndci_bloom = compute_ndci(red_edge_bloom, red)
    assert np.all(ndci_bloom > 0.0)
    assert np.all(ndci_bloom <= 1.0)


def test_classify_ndci_trophic_state():
    # Grid spanning all 4 trophic levels
    ndci = np.array([
        [-0.25, -0.15],  # Oligotrophic (< -0.10)
        [0.00, 0.05],    # Mesotrophic (-0.10 to 0.10)
        [0.15, 0.18],    # Eutrophic (0.10 to 0.20)
        [0.25, 0.40]     # Hypertrophic / HAB (>= 0.20)
    ], dtype=np.float32)

    classified, breakdown = classify_ndci_trophic_state(ndci)
    assert classified.shape == (4, 2)
    assert breakdown["oligotrophic_pct"] == 25.0
    assert breakdown["mesotrophic_pct"] == 25.0
    assert breakdown["eutrophic_pct"] == 25.0
    assert breakdown["hypertrophic_hab_pct"] == 25.0


def test_compute_ndti_and_classify():
    green = np.array([[0.10, 0.05], [0.08, 0.12]], dtype=np.float32)
    red = np.array([[0.05, 0.10], [0.08, 0.06]], dtype=np.float32)
    ndti = compute_ndti(red, green)
    assert ndti.shape == (2, 2)

    classified, breakdown = classify_ndti_turbidity(ndti)
    assert classified.shape == (2, 2)
    total_pct = sum(breakdown.values())
    assert 99.9 <= total_pct <= 100.1


def test_estimate_spm_nechad():
    red = np.array([[0.02, 0.05], [0.08, 0.12]], dtype=np.float32)
    spm = estimate_spm_nechad(red)
    assert spm.shape == (2, 2)
    assert np.all(spm >= 0.0)
    # Higher red reflectance must yield higher suspended matter
    assert spm[1, 1] > spm[0, 0]


def test_detect_thermal_plume_anomalies():
    # Ambient water temperature around 20°C
    sst = np.full((30, 30), 20.0, dtype=np.float32)
    # Inject 5-pixel thermal effluent hotspot at 23.5°C (+3.5°C anomaly)
    sst[10:15, 10:15] = 23.5

    mask, metrics = detect_thermal_plume_anomalies(sst, delta_t_threshold_celsius=1.5)
    assert metrics["thermal_plume_detected"] is True
    assert metrics["plume_hotspots_count"] >= 1
    assert metrics["max_delta_t_celsius"] >= 3.0
    assert metrics["plume_area_km2"] > 0.0


def test_analyze_coastal_water_quality_full_pipeline():
    rows, cols = 50, 50
    green = np.full((rows, cols), 0.08, dtype=np.float32)
    red = np.full((rows, cols), 0.06, dtype=np.float32)
    red_edge = np.full((rows, cols), 0.07, dtype=np.float32)

    # Inject HAB algal bloom patch
    red_edge[10:25, 10:25] = 0.22
    red[10:25, 10:25] = 0.05

    # Thermal array with industrial discharge
    sst = np.full((rows, cols), 21.0, dtype=np.float32)
    sst[35:40, 35:40] = 24.5

    bbox = [22.70, 38.80, 22.95, 38.95]
    results = analyze_coastal_water_quality(
        green=green,
        red=red,
        red_edge=red_edge,
        sst=sst,
        cellsize_m=10.0,
        bbox=bbox
    )

    assert "summary" in results
    assert "chlorophyll_ndci" in results
    assert "turbidity_ndti" in results
    assert "suspended_solids_spm" in results
    assert "thermal_plume" in results

    assert results["summary"]["hab_alert_level"] in ["CRITICAL", "ELEVATED", "MODERATE"]
    assert results["chlorophyll_ndci"]["max"] > 0.30
    assert results["thermal_plume"]["thermal_plume_detected"] is True

    # Test GeoJSON serialization
    geojson = water_quality_to_geojson(results, bbox)
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 2
    assert geojson["features"][0]["geometry"]["type"] == "Polygon"
    assert geojson["features"][1]["geometry"]["type"] == "Point"

    # Test CSV serialization
    csv_str = water_quality_to_csv(results)
    assert "parameter,value,unit,interpretation" in csv_str
    assert "hab_alert_level" in csv_str
    assert "mean_ndci" in csv_str
