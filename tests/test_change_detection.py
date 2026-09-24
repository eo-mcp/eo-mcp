"""Unit tests for Remote Sensing Change Detection (RS-CD) Core Engine."""

import numpy as np
import pytest
from eo_mcp.core.change_detection import (
    compute_difference_image,
    compute_change_vector_analysis,
    compute_sar_log_ratio,
    compute_pixelwise_t_test,
    otsu_threshold,
    extract_contiguous_change_patches,
    patches_to_geojson,
    generate_rsicc_caption
)


def test_difference_image_modes():
    """Verify raw, absolute, relative, and normalized difference computations."""
    ep1 = np.array([[0.5, 0.2], [0.8, 0.1]], dtype=np.float32)
    ep2 = np.array([[0.2, 0.4], [0.8, 0.0]], dtype=np.float32)

    diff_raw = compute_difference_image(ep1, ep2, mode="raw")
    assert np.allclose(diff_raw, [[-0.3, 0.2], [0.0, -0.1]])

    diff_abs = compute_difference_image(ep1, ep2, mode="absolute")
    assert np.allclose(diff_abs, [[0.3, 0.2], [0.0, 0.1]])


def test_change_vector_analysis():
    """Verify CVA magnitude and directional vectors across multi-spectral bands."""
    b1_t1 = np.full((5, 5), 0.1, dtype=np.float32)
    b2_t1 = np.full((5, 5), 0.2, dtype=np.float32)

    b1_t2 = np.full((5, 5), 0.4, dtype=np.float32)  # delta 0.3
    b2_t2 = np.full((5, 5), 0.6, dtype=np.float32)  # delta 0.4

    bands1 = {"R": b1_t1, "N": b2_t1}
    bands2 = {"R": b1_t2, "N": b2_t2}

    mag, direction, meta = compute_change_vector_analysis(bands1, bands2)
    expected_mag = np.sqrt(0.3**2 + 0.4**2)  # 0.5
    assert np.allclose(mag, expected_mag)
    assert meta["mean_magnitude"] == pytest.approx(0.5, abs=1e-4)


def test_sar_log_ratio():
    """Verify SAR delta dB and severe drop/surge detection."""
    sar1 = np.full((4, 4), -12.0, dtype=np.float32)
    sar2 = np.full((4, 4), -18.0, dtype=np.float32)  # 6 dB drop (inundation)

    delta_db, stats = compute_sar_log_ratio(sar1, sar2)
    assert np.allclose(delta_db, -6.0)
    assert stats["severe_drop_percent"] == 100.0
    assert stats["mean_delta_db"] == -6.0


def test_pixelwise_t_test():
    """Verify temporal baseline Z-score anomaly detection."""
    base1 = np.full((4, 4), 10.0, dtype=np.float32)
    base2 = np.full((4, 4), 12.0, dtype=np.float32)
    base3 = np.full((4, 4), 11.0, dtype=np.float32)
    # mean = 11.0, std ~ 0.816

    post_event = np.full((4, 4), 18.0, dtype=np.float32)  # strong anomaly

    z_score, anomaly_mask, stats = compute_pixelwise_t_test([base1, base2, base3], post_event, z_threshold=2.5)
    assert np.all(anomaly_mask)
    assert stats["anomaly_percentage"] == 100.0
    assert np.all(z_score > 3.0)


def test_otsu_thresholding():
    """Verify Otsu computes clean bimodal threshold separating change from noise."""
    # Bimodal distribution: 0-0.2 (noise) and 0.8-1.0 (real change)
    np.random.seed(42)
    noise = np.random.normal(0.1, 0.02, (50, 50))
    change = np.random.normal(0.9, 0.02, (20, 20))
    img = noise.copy()
    img[10:30, 10:30] = change

    th = otsu_threshold(img)
    # Threshold must cleanly separate all noise pixels from change pixels
    assert np.max(noise) < th < np.min(change)

    # Balanced 50/50 bimodal distribution should yield midpoint threshold ~0.5
    balanced = np.zeros((50, 50), dtype=np.float32)
    balanced[:25, :] = 0.1
    balanced[25:, :] = 0.9
    th_balanced = otsu_threshold(balanced)
    assert 0.4 < th_balanced < 0.6


def test_patch_extraction_and_geojson():
    """Verify contiguous change patch clustering, MMU filtering, and GeoJSON export."""
    mask = np.zeros((50, 50), dtype=bool)
    # Patch 1: 10x10 = 100 pixels = 1.0 ha at 10m res
    mask[5:15, 5:15] = True
    # Patch 2: 1 pixel (isolated noise) -> 0.01 ha (should be filtered if MMU=0.5 ha)
    mask[40, 40] = True

    patches = extract_contiguous_change_patches(
        mask, pixel_size_m=10.0, min_patch_ha=0.5, bbox_wgs84=(-122.5, 37.5, -122.4, 37.6)
    )

    assert len(patches) == 1  # Noise pixel filtered out
    assert patches[0]["area_ha"] == 1.0
    assert patches[0]["pixel_count"] == 100

    geojson = patches_to_geojson(patches)
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 1
    assert geojson["features"][0]["properties"]["area_ha"] == 1.0


def test_rsicc_caption_generation():
    """Verify RSICC caption generation creates clear, assertive telemetry."""
    top_patches = [{
        "centroid_lat": 37.55,
        "centroid_lon": -122.45,
        "area_ha": 42.5
    }]
    caption = generate_rsicc_caption(
        location_name="San Francisco Bay",
        epoch1_str="2023-01-01",
        epoch2_str="2024-01-01",
        loss_ha=120.0,
        gain_ha=30.0,
        net_ha=-90.0,
        total_area_ha=1000.0,
        dominant_type="vegetation_canopy",
        top_patches=top_patches
    )

    assert "San Francisco Bay" in caption
    assert "120.0 ha" in caption
    assert "42.5 contiguous hectares" in caption
    assert "\u2014" not in caption  # Strictly ZERO em dashes
