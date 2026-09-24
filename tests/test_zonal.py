"""Unit tests for Vector Zonal Statistics and Temporal Compositing Engine."""

import numpy as np
import pytest
from eo_mcp.core.zonal import (
    compute_zonal_statistics,
    compute_bitemporal_zonal_change,
    compute_temporal_composite,
    apply_raster_mask,
    query_osm_geometries
)


def test_zonal_statistics():
    """Verify zonal statistics calculation within a rectangular polygon."""
    raster = np.zeros((100, 100), dtype=np.float32)
    # Put values of 0.8 inside the top-left quadrant [0:50, 0:50]
    raster[0:50, 0:50] = 0.8

    bbox = (-122.5, 37.5, -122.3, 37.7)

    # Polygon covering top-left quadrant: lon from -122.5 to -122.4, lat from 37.6 to 37.7
    poly = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-122.5, 37.6],
                    [-122.4, 37.6],
                    [-122.4, 37.7],
                    [-122.5, 37.7],
                    [-122.5, 37.6]
                ]]
            },
            "properties": {"name": "Test Park"}
        }]
    }

    zonal = compute_zonal_statistics(raster, bbox, poly, pixel_size_m=10.0)
    assert len(zonal["features"]) == 1
    props = zonal["features"][0]["properties"]
    assert props["name"] == "Test Park"
    assert props["pixel_count"] > 0
    assert props["mean"] == pytest.approx(0.8, abs=0.05)


def test_bitemporal_zonal_change():
    """Verify dual-epoch zonal change and status classification."""
    raster_ep1 = np.full((50, 50), 0.7, dtype=np.float32)
    raster_ep2 = np.full((50, 50), 0.3, dtype=np.float32)  # -0.4 drop (degraded)

    bbox = (-122.5, 37.5, -122.3, 37.7)
    poly = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-122.5, 37.5],
                    [-122.3, 37.5],
                    [-122.3, 37.7],
                    [-122.5, 37.7],
                    [-122.5, 37.5]
                ]]
            },
            "properties": {"name": "Forested Valley"}
        }]
    }

    change = compute_bitemporal_zonal_change(
        raster_ep1, raster_ep2, bbox, poly, pixel_size_m=10.0, change_threshold=0.15
    )

    assert len(change["features"]) == 1
    props = change["features"][0]["properties"]
    assert props["delta_mean"] < -0.3
    assert props["status"] == "degraded"
    assert props["change_intensity"] > 0.3


def test_temporal_composite():
    """Verify temporal reduction across image stack."""
    arr1 = np.full((5, 5), 10.0, dtype=np.float32)
    arr2 = np.full((5, 5), 20.0, dtype=np.float32)
    arr3 = np.full((5, 5), 30.0, dtype=np.float32)

    stack = [arr1, arr2, arr3]

    median_comp = compute_temporal_composite(stack, method="median")
    assert np.allclose(median_comp, 20.0)

    mean_comp = compute_temporal_composite(stack, method="mean")
    assert np.allclose(mean_comp, 20.0)

    max_comp = compute_temporal_composite(stack, method="max")
    assert np.allclose(max_comp, 30.0)

    min_comp = compute_temporal_composite(stack, method="min")
    assert np.allclose(min_comp, 10.0)


def test_apply_raster_mask():
    """Verify raster masking with NaN values."""
    raster = np.ones((4, 4), dtype=np.float32)
    mask = np.zeros((4, 4), dtype=bool)
    mask[0:2, 0:2] = True  # mask out top-left

    masked = apply_raster_mask(raster, mask, invert=False, fill_value=np.nan)
    assert np.isnan(masked[0, 0])
    assert not np.isnan(masked[3, 3])
    assert masked[3, 3] == 1.0


def test_query_osm_geometries_structure():
    """Verify query_osm_geometries returns a well-formed FeatureCollection."""
    res = query_osm_geometries(
        bbox_wgs84=(-122.45, 37.75, -122.40, 37.80),
        osm_tag="leisure=park",
        timeout_s=5.0
    )
    assert res["type"] == "FeatureCollection"
    assert "features" in res
    assert isinstance(res["features"], list)
