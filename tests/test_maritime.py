"""Unit tests for SAR vessel detection and AIS correlation (Dark Vessel detection)."""

import numpy as np
import pytest
from eo_mcp.core.maritime import (
    cfar_vessel_detector,
    haversine_distance_km,
    correlate_sar_with_ais,
    pixel_to_wgs84
)


def test_cfar_vessel_detector():
    # 40x50 ocean clutter ~ -18 dB
    np.random.seed(42)
    sar_db = np.random.normal(loc=-18.0, scale=2.0, size=(40, 50))

    # Inject two bright metallic ship targets
    sar_db[10, 10] = 8.5  # Ship 1
    sar_db[10, 11] = 7.2  # Ship 1 cluster
    sar_db[25, 30] = 10.0 # Ship 2

    mask, targets = cfar_vessel_detector(sar_db, pfa_factor=3.0, min_cluster_size=1)

    assert len(targets) >= 2
    target_ids = [t["target_id"] for t in targets]
    assert "SAR-TRG-001" in target_ids
    assert mask[25, 30] == True


def test_haversine_distance():
    # Distance between Gdansk and Sopot ~ 12 km
    # Gdansk: 18.6466, 54.3520
    # Sopot: 18.5600, 54.4418
    dist_km = haversine_distance_km(18.6466, 54.3520, 18.5600, 54.4418)
    assert 10.0 <= dist_km <= 15.0


def test_correlate_sar_with_ais_dark_vessel():
    bbox = [18.50, 54.30, 18.80, 54.60]
    raster_shape = (40, 50)

    # 2 detected targets
    detected_targets = [
        {
            "target_id": "SAR-TRG-001",
            "pixel_row": 10.0,
            "pixel_col": 10.0,
            "length_px": 2.0,
            "width_px": 1.0,
            "peak_backscatter_db": 9.5
        },
        {
            "target_id": "SAR-TRG-002",
            "pixel_row": 30.0,
            "pixel_col": 35.0,
            "length_px": 3.0,
            "width_px": 1.5,
            "peak_backscatter_db": 11.2
        }
    ]

    # Target 1 has a matching AIS report nearby
    lon1, lat1 = pixel_to_wgs84(10.0, 10.0, bbox, raster_shape)
    ais_records = [
        {
            "mmsi": 261001234,
            "lat": lat1 + 0.001,
            "lon": lon1 + 0.001,
            "speed_knots": 12.4,
            "course_deg": 320.0,
            "heading_deg": 318
        }
    ]

    results = correlate_sar_with_ais(
        detected_targets=detected_targets,
        ais_records=ais_records,
        bbox=bbox,
        raster_shape=raster_shape,
        max_correlation_dist_km=1.5
    )

    assert results["total_sar_targets_detected"] == 2
    assert results["trusted_matched_count"] == 1
    assert results["dark_vessel_count"] == 1

    dark = results["dark_vessels"][0]
    assert dark["status"] == "DARK_VESSEL"
    assert dark["ais_state"] == "UNREPORTED"
    assert dark["track_state"] == "SUSPECT"


def test_cfar_sea_state_adaptation():
    """Verify that CA-CFAR adapts dynamically to rough sea clutter and extracts signal-to-clutter ratio."""
    np.random.seed(99)
    # Simulate rough sea clutter with higher variance and wave crests
    sar_db_rough = np.random.normal(loc=-13.0, scale=3.5, size=(50, 60))

    # Inject ship target (2 connected pixels to form realistic target cluster)
    sar_db_rough[20, 25] = 12.5
    sar_db_rough[20, 26] = 10.8

    # Auto sea-state detection should infer 'rough' and increase roughness factor
    mask_auto, targets_auto = cfar_vessel_detector(sar_db_rough, pfa_factor=3.0, min_cluster_size=1, sea_state="auto")
    
    assert len(targets_auto) >= 1
    trg = targets_auto[0]
    assert trg["sea_state"] == "rough"
    assert "signal_to_clutter_db" in trg
    assert trg["signal_to_clutter_db"] > 10.0


def test_server_detect_dark_vessels_with_sea_state():
    """Verify server tool detect_dark_vessels accepts sea_state parameter."""
    import json
    from eo_mcp.server import detect_dark_vessels

    bbox = [18.5, 54.3, 18.8, 54.6]
    res_str = detect_dark_vessels(
        bbox=bbox,
        datetime_range="2024-06-01/2024-06-30",
        sea_state="rough",
        format="summary"
    )
    data = json.loads(res_str)
    assert "dark_vessel_count" in data
    assert data["dark_vessel_count"] >= 1
