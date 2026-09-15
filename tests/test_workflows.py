"""Unit tests for ergonomic workflows, category scoping, and progressive discovery."""

import os
import json
import pytest
from eo_mcp.workflows import resolve_aoi, assess_location_hazard, environmental_site_audit
from eo_mcp.registry import (
    discover_tools,
    is_tool_enabled,
    get_allowed_tools,
    TOOL_CATEGORIES,
    PROFILES
)


def test_resolve_aoi():
    # Test valid 4-float bbox list
    bbox, name = resolve_aoi([-0.4, 39.4, -0.3, 39.5])
    assert bbox == [-0.4, 39.4, -0.3, 39.5]
    assert "Bounding Box" in name

    # Test coordinate string
    bbox2, name2 = resolve_aoi("-0.4, 39.4, -0.3, 39.5")
    assert bbox2 == [-0.4, 39.4, -0.3, 39.5]

    # Test invalid inputs
    with pytest.raises(ValueError):
        resolve_aoi([-0.4, 39.4])

    with pytest.raises(TypeError):
        resolve_aoi(12345)


def test_registry_categories_and_profiles():
    # Verify all categories have descriptions and tools
    assert "workflows" in TOOL_CATEGORIES
    assert "core" in TOOL_CATEGORIES
    assert "hazards" in TOOL_CATEGORIES

    # Verify profile scoping
    workflows_tools = get_allowed_tools("workflows")
    assert "assess_location_hazard" in workflows_tools
    assert "environmental_site_audit" in workflows_tools
    assert "eo_geocode" in workflows_tools
    assert "detect_dark_vessels" not in workflows_tools  # maritime not in workflows profile

    hazards_tools = get_allowed_tools("hazards")
    assert "simulate_sea_level_rise" in hazards_tools
    assert "detect_active_wildfires" in hazards_tools
    assert "monitor_crop_phenology" not in hazards_tools

    # Test is_tool_enabled
    assert is_tool_enabled("assess_location_hazard", profile="workflows") is True
    assert is_tool_enabled("detect_dark_vessels", profile="workflows") is False
    assert is_tool_enabled("detect_dark_vessels", profile="all") is True


def test_discover_tools():
    # Global discovery
    all_res = discover_tools()
    assert all_res["categories_matched"] >= 5

    # Filtered by category
    wf_res = discover_tools(category="workflows")
    assert wf_res["categories_matched"] == 1
    assert "assess_location_hazard" in wf_res["results"]["workflows"]["tools"]

    # Filtered by search query
    search_res = discover_tools(query="wildfire")
    assert "hazards" in search_res["results"]
    assert "detect_active_wildfires" in search_res["results"]["hazards"]["tools"]


def test_assess_location_hazard_flood():
    # Test flood inundation with coordinate bbox
    res_str = assess_location_hazard(
        location=[-0.42, 39.42, -0.32, 39.50],
        hazard_type="flood_inundation",
        water_level_rise_m=1.5
    )
    data = json.loads(res_str)
    assert data["workflow"] == "assess_location_hazard:flood_inundation"
    assert "inundated_land_area_ha" in data
    assert "ascii_flood_depth_map" in data


def test_assess_location_hazard_wildfire():
    res_str = assess_location_hazard(
        location=[-120.5, 38.5, -120.0, 39.0],
        hazard_type="wildfire",
        days=2
    )
    data = json.loads(res_str)
    assert data["workflow"] == "assess_location_hazard:wildfire"
    assert "fire_perimeters_count" in data


def test_assess_location_hazard_burn_severity():
    res_str = assess_location_hazard(
        location=[-120.2, 38.6, -120.0, 38.8],
        hazard_type="burn_severity",
        pre_fire_date_range="2023-06-01/2023-06-30",
        post_fire_date_range="2023-08-01/2023-08-31"
    )
    data = json.loads(res_str)
    assert data["workflow"] == "assess_location_hazard:burn_severity"
    assert "mean_dnbr" in data
    assert "total_burned_area_ha" in data


def test_assess_location_hazard_geojson():
    res_geojson = assess_location_hazard(
        location=[-0.42, 39.42, -0.32, 39.50],
        hazard_type="flood_inundation",
        format="geojson"
    )
    geo = json.loads(res_geojson)
    assert geo["type"] == "FeatureCollection"
    assert len(geo["features"]) > 0


def test_environmental_site_audit():
    res_str = environmental_site_audit(
        location=[-0.42, 39.42, -0.32, 39.50],
        format="summary"
    )
    data = json.loads(res_str)
    assert data["workflow"] == "environmental_site_audit"
    assert "scorecard" in data
    assert "flood_susceptibility" in data["scorecard"]
    assert "canopy_vigor_index_ndvi" in data["scorecard"]
    assert "spectral_layers" in data
    assert "ndvi" in data["spectral_layers"]
    assert "ndwi" in data["spectral_layers"]


def test_environmental_site_audit_geojson():
    res_str = environmental_site_audit(
        location=[-0.42, 39.42, -0.32, 39.50],
        format="geojson"
    )
    geo = json.loads(res_str)
    assert geo["type"] == "FeatureCollection"
    assert len(geo["features"]) == 1
    assert "overall_environmental_health" in geo["features"][0]["properties"]
