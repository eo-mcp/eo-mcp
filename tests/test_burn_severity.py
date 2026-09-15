"""Unit tests for dNBR post-fire burn severity calculations."""

import numpy as np
import json
from eo_mcp.core.wildfire import calculate_burn_severity_dnbr, burn_severity_to_geojson, burn_severity_to_csv
from eo_mcp.server import calculate_burn_severity


def test_calculate_burn_severity_dnbr():
    rows, cols = 30, 30
    pre_nbr = np.full((rows, cols), 0.60, dtype=np.float32)
    post_nbr = np.full((rows, cols), 0.60, dtype=np.float32)

    # Inject high-severity burn scar in center
    post_nbr[10:20, 10:20] = -0.20  # dNBR = 0.60 - (-0.20) = 0.80 (High severity)

    results = calculate_burn_severity_dnbr(pre_nbr, post_nbr, pixel_size_m=10.0)

    assert results["total_burned_area_ha"] > 0.0
    assert results["burned_percentage"] > 10.0
    assert results["overall_burn_severity_class"] == "HIGH_SEVERITY"
    assert results["severity_breakdown_ha"]["high_severity_ha"] > 0.0


def test_burn_severity_formatters():
    rows, cols = 10, 10
    pre_nbr = np.full((rows, cols), 0.50, dtype=np.float32)
    post_nbr = np.full((rows, cols), 0.10, dtype=np.float32)
    results = calculate_burn_severity_dnbr(pre_nbr, post_nbr)

    geojson = burn_severity_to_geojson(results)
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 1

    csv_out = burn_severity_to_csv(results)
    assert "mean_dnbr" in csv_out
    assert "high_severity_ha" in csv_out


def test_server_burn_severity_tool():
    res_str = calculate_burn_severity(
        bbox=[-120.2, 38.6, -120.0, 38.8],
        pre_fire_date_range="2023-06-01/2023-06-30",
        post_fire_date_range="2023-08-01/2023-08-31"
    )
    res = json.loads(res_str)
    assert "mean_dnbr" in res
    assert "severity_breakdown_ha" in res
