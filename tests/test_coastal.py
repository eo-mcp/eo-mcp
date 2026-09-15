"""Unit tests for coastal erosion and shoreline transect analysis."""

import numpy as np
import pytest
from eo_mcp.core.coastal import (
    compute_mndwi,
    extract_water_mask_otsu,
    extract_shoreline_boundary,
    compute_transect_erosion_rates
)


def test_compute_mndwi():
    green = np.array([[500, 2000], [1000, 3000]], dtype=np.uint16)
    swir = np.array([[2000, 500], [1000, 1000]], dtype=np.uint16)

    mndwi = compute_mndwi(green, swir)
    # green=2000, swir=500 -> (2000-500)/(2000+500) = 1500/2500 = 0.6 (Water)
    assert mndwi[0, 1] == pytest.approx(0.6, abs=0.01)
    # green=500, swir=2000 -> -0.6 (Land)
    assert mndwi[0, 0] == pytest.approx(-0.6, abs=0.01)


def test_extract_shoreline_boundary():
    # 10x10 array with water on columns 0-4 and land on columns 5-9
    water_mask = np.zeros((10, 10), dtype=bool)
    water_mask[:, :5] = True

    boundary = extract_shoreline_boundary(water_mask)
    # The boundary should be at column 4
    assert np.all(boundary[:, 4] == True)
    assert not np.any(boundary[:, :4])
    assert not np.any(boundary[:, 5:])


def test_compute_transect_erosion_rates():
    rows, cols = 30, 40
    # Historical waterline at column 15
    hist_mask = np.zeros((rows, cols), dtype=bool)
    hist_mask[:, :15] = True

    # Modern waterline at column 18 (water moved inland by 3 pixels = 30m over 5 years)
    recent_mask = np.zeros((rows, cols), dtype=bool)
    recent_mask[:, :18] = True

    results = compute_transect_erosion_rates(
        hist_water_mask=hist_mask,
        recent_water_mask=recent_mask,
        time_delta_years=5.0,
        pixel_size_m=10.0,
        transect_sample_step=5
    )

    assert results["transects_evaluated"] > 0
    # NSM = +30m (water gained, land eroded)
    # EPR = 30m / 5yr = 6.0 m/yr
    assert results["eroding_transects_count"] > 0
    assert results["overall_status"] in ["EROSIONAL", "DYNAMICALLY_STABLE", "ACCRETIONAL"]
