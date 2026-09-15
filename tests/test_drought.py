"""Unit tests for reservoir surface water drought monitoring engine."""

import pytest
import json
from eo_mcp.core.drought import (
    analyze_water_body_drought,
    drought_to_geojson,
    drought_to_csv
)


def test_water_body_drought_analysis():
    bbox = [-4.5, 37.5, -4.0, 38.0]
    res = analyze_water_body_drought(bbox=bbox, historical_year=2019, recent_year=2024)
    assert res["historical_year"] == 2019
    assert res["recent_year"] == 2024
    assert res["historical_water_area_ha"] > 0
    assert res["recent_water_area_ha"] > 0
    assert "net_water_loss_ha" in res
    assert "water_loss_percentage" in res
    assert "permanent_water_area_ha" in res
    assert "dried_up_area_ha" in res
    assert "drought_severity_class" in res
    assert "policy_alignment" in res
    assert res["drought_severity_class"] in [
        "CRITICAL_DROUGHT_DEPLETION",
        "MODERATE_DEPLETION",
        "STABLE_STORAGE",
        "SURPLUS_EXPANSION"
    ]


def test_drought_geojson_and_csv_export():
    bbox = [-4.5, 37.5, -4.0, 38.0]
    res = analyze_water_body_drought(bbox=bbox, historical_year=2019, recent_year=2024)

    geojson = drought_to_geojson(res)
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 1
    assert geojson["features"][0]["geometry"]["type"] == "Polygon"
    assert geojson["features"][0]["properties"]["drought_severity_class"] == res["drought_severity_class"]

    csv_str = drought_to_csv(res)
    assert "historical_year" in csv_str
    assert "recent_year" in csv_str
    assert "net_water_loss_ha" in csv_str
    assert "drought_severity_class" in csv_str
    assert str(res["historical_year"]) in csv_str
