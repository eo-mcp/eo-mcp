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
