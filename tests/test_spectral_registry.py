"""Unit tests for Awesome Spectral Indices (ASI) Registry and Formula Engine."""

import numpy as np
import pytest
from eo_mcp.core.spectral_registry import SpectralIndexRegistry, registry


def test_registry_initialization():
    """Verify registry loaded indices and fallback works."""
    assert len(registry._indices) >= 8
    ndvi = registry.get_index("NDVI")
    assert ndvi is not None
    assert ndvi["application_domain"] == "vegetation"
    assert "N" in ndvi["bands"] and "R" in ndvi["bands"]


def test_registry_listing_and_search():
    """Verify listing by domain and search functionality."""
    veg_indices = registry.list_indices(domain="vegetation")
    assert len(veg_indices) > 0
    assert all(i["application_domain"] == "vegetation" for i in veg_indices)

    water_search = registry.search_indices("water")
    assert len(water_search) > 0
    assert any("NDWI" in m["short_name"] for m in water_search)


def test_band_resolution():
    """Verify generic band symbols resolve to sensor-specific keys."""
    resolved_s2 = registry.resolve_band_keys("NDVI", platform="sentinel-2")
    assert resolved_s2["N"] == "B08"
    assert resolved_s2["R"] == "B04"

    resolved_l8 = registry.resolve_band_keys("NDVI", platform="landsat-8")
    assert resolved_l8["N"] in ("nir08", "nir", "B5")
    assert resolved_l8["R"] in ("red", "B4")


def test_compute_native_dispatch():
    """Verify native vector dispatch produces accurate mathematical results."""
    shape = (10, 10)
    nir = np.full(shape, 0.6, dtype=np.float32)
    red = np.full(shape, 0.2, dtype=np.float32)

    ndvi = registry.compute_index("NDVI", {"N": nir, "R": red})
    expected = (0.6 - 0.2) / (0.6 + 0.2)  # 0.4 / 0.8 = 0.5
    assert np.allclose(ndvi, expected)


def test_compute_ast_evaluation():
    """Verify dynamic AST evaluation handles complex formulas and constants."""
    shape = (10, 10)
    nir = np.full(shape, 0.7, dtype=np.float32)
    red = np.full(shape, 0.1, dtype=np.float32)
    blue = np.full(shape, 0.05, dtype=np.float32)

    evi = registry.compute_index("EVI", {"N": nir, "R": red, "B": blue})
    assert evi.shape == shape
    assert not np.isnan(evi).any()
    assert np.all(evi > 0)


def test_missing_bands_error():
    """Verify proper error handling when required band is missing."""
    shape = (5, 5)
    nir = np.full(shape, 0.5, dtype=np.float32)
    with pytest.raises(ValueError, match="Missing required bands"):
        registry.compute_index("NDVI", {"N": nir})
