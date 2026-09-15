"""Unit tests for agricultural crop phenology trajectories."""

import json
from eo_mcp.core.phenology import (
    analyze_crop_phenology_trajectory,
    phenology_to_geojson,
    phenology_to_csv
)
from eo_mcp.server import monitor_crop_phenology


def test_analyze_crop_phenology_trajectory():
    # Seasonal curve: March to October
    observations = [
        {"date": "2024-03-15", "ndvi": 0.22},
        {"date": "2024-04-15", "ndvi": 0.38},
        {"date": "2024-05-15", "ndvi": 0.62},
        {"date": "2024-06-15", "ndvi": 0.78},  # Peak
        {"date": "2024-07-15", "ndvi": 0.74},
        {"date": "2024-08-15", "ndvi": 0.55},
        {"date": "2024-09-15", "ndvi": 0.32},
        {"date": "2024-10-15", "ndvi": 0.21}
    ]

    results = analyze_crop_phenology_trajectory(
        observations=observations,
        year=2024,
        reference_peak_ndvi=0.75
    )

    miles = results["phenology_milestones"]
    assert miles["peak_of_season_pos"] == "2024-06-15"
    assert miles["peak_ndvi"] == 0.78
    assert miles["seasonal_amplitude"] > 0.5
    assert results["crop_health_assessment"]["status"] == "NORMAL_HEALTHY"


def test_phenology_formatters():
    observations = [
        {"date": "2024-04-15", "ndvi": 0.30},
        {"date": "2024-06-15", "ndvi": 0.70},
        {"date": "2024-08-15", "ndvi": 0.35}
    ]
    results = analyze_crop_phenology_trajectory(observations=observations, year=2024)

    gj = phenology_to_geojson(results)
    assert gj["type"] == "FeatureCollection"
    assert len(gj["features"]) == 1

    csv_out = phenology_to_csv(results)
    assert "date,ndvi" in csv_out
    assert "2024-06-15,0.7" in csv_out


def test_server_crop_phenology_tool():
    res_str = monitor_crop_phenology(bbox=[-4.5, 37.5, -4.3, 37.7], year=2024, crop_type="Wheat")
    res = json.loads(res_str)
    assert "phenology_milestones" in res
    assert "crop_health_assessment" in res
