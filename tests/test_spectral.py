"""Unit tests for spectral band indices."""

import numpy as np
from eo_mcp.core.spectral import (
    compute_ndvi,
    compute_ndwi,
    compute_nbr,
    compute_evi,
    calculate_array_stats
)


def test_compute_ndvi_healthy_vegetation():
    # NIR is high (0.8), Red is low (0.1) -> NDVI should be high ~ 0.778
    nir = np.array([[0.8, 0.7], [0.85, 0.9]], dtype=np.float32)
    red = np.array([[0.1, 0.15], [0.12, 0.08]], dtype=np.float32)
    
    ndvi = compute_ndvi(nir, red)
    assert ndvi.shape == (2, 2)
    assert np.all(ndvi > 0.6)
    assert np.all(ndvi <= 1.0)


def test_compute_ndvi_water_or_barren():
    # NIR is low (0.05), Red is higher (0.1) -> NDVI should be negative
    nir = np.array([[0.05]], dtype=np.float32)
    red = np.array([[0.1]], dtype=np.float32)
    
    ndvi = compute_ndvi(nir, red)
    assert ndvi[0, 0] < 0.0


def test_compute_ndwi_water_body():
    # Green is high (0.4), NIR is low (0.05) -> NDWI > 0
    green = np.array([[0.4]], dtype=np.float32)
    nir = np.array([[0.05]], dtype=np.float32)
    
    ndwi = compute_ndwi(green, nir)
    assert ndwi[0, 0] > 0.5


def test_calculate_array_stats():
    arr = np.array([[0.2, 0.4], [0.6, 0.8]], dtype=np.float32)
    stats = calculate_array_stats(arr)
    assert stats["count"] == 4
    assert np.isclose(stats["mean"], 0.5)
    assert np.isclose(stats["min"], 0.2)
    assert np.isclose(stats["max"], 0.8)
