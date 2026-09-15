"""Unit tests for Sentinel-5P atmospheric emissions & OpenAQ monitoring engine."""

import pytest
import json
from eo_mcp.core.emissions import (
    query_sentinel5p_emissions,
    fetch_openaq_ground_truth,
    emissions_to_geojson,
    emissions_to_csv,
    AIR_QUALITY_THRESHOLDS
)


def test_s5p_emissions_query_no2():
    bbox = [2.2, 48.7, 2.5, 49.0]
    res = query_sentinel5p_emissions(bbox=bbox, gas="NO2", datetime_range="2024-06-01/2024-06-30")
    assert res["gas"] == "NO2"
    assert res["unit"] == "umol/m2"
    assert "mean_column_density" in res
    assert "max_column_density" in res
    assert "plume_detected" in res
    assert "compliance_directive" in res
    assert len(res["hotspots"]) > 0


def test_s5p_emissions_query_other_gases():
    bbox = [10.0, 50.0, 10.5, 50.5]
    for gas in ["CH4", "SO2", "CO"]:
        res = query_sentinel5p_emissions(bbox=bbox, gas=gas)
        assert res["gas"] == gas
        assert res["unit"] == AIR_QUALITY_THRESHOLDS[gas]["unit"]
        assert res["mean_column_density"] > 0


def test_openaq_ground_truth():
    bbox = [2.2, 48.7, 2.5, 49.0]
    stations = fetch_openaq_ground_truth(bbox=bbox)
    assert isinstance(stations, list)
    assert len(stations) > 0
    for s in stations:
        assert "station_name" in s
        assert "lat" in s
        assert "lon" in s
        assert "latest_measurements" in s


def test_emissions_geojson_and_csv_export():
    bbox = [2.2, 48.7, 2.5, 49.0]
    res = query_sentinel5p_emissions(bbox=bbox, gas="NO2")
    stations = fetch_openaq_ground_truth(bbox=bbox)
    full_data = {
        **res,
        "openaq_ground_stations": stations,
        "openaq_station_count": len(stations)
    }

    geojson = emissions_to_geojson(full_data)
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) >= 1

    csv_str = emissions_to_csv(full_data)
    assert "feature_type" in csv_str
    assert "gas" in csv_str
    assert "NO2" in csv_str
