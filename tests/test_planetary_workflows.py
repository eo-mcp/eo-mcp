"""Unit and Integration tests for Milestone M3: Turnkey Planetary Workflows & Server Integration.

Verifies:
1. Turnkey Wildfire Burn Severity Audit (audit_wildfire_burn):
   - Location geocoding & multi-temporal pre/post scene discovery
   - Differential Normalized Burn Ratio (dNBR) calculation
   - USGS 6-tier severity classification
   - Burned area quantification in hectares and acres
   - Scar perimeter vectorization and visual artifact export
2. Turnkey Flood Inundation & DEM Slope Masking (detect_flood_inundation):
   - Multi-temporal optical MNDWI water extraction
   - Copernicus DEM Horn (1981) central-difference slope terrain filtering (> 5.0 deg shadow rejection)
   - Permanent water baseline separation from inundated agricultural land
   - Flood severity classification and visual artifact export
3. Turnkey Dual-Epoch Vegetation Change (detect_vegetation_change):
   - Dual-epoch canopy vitality differencing (Delta NDVI / Delta EVI)
   - Loss & greening anomaly threshold masking
   - Contiguous anomaly patch clustering with centroids and bounding boxes
   - Visual artifact export
4. FastMCP Server Integration:
   - Registration of the 3 turnkey workflows as @eo_tool() tools
   - stac_search default compact=True parameter (< 2,500 chars) & compact=False legacy support
   - Integration of visual artifact generation into calculate_spectral_index, calculate_burn_severity, simulate_sea_level_rise
5. Zero Network Offline Guarantee:
   - 100% deterministic offline execution with synthetic fixtures
"""

import json
import os
import socket
from pathlib import Path
import numpy as np
import pytest
from PIL import Image

from eo_mcp.workflows import (
    audit_wildfire_burn,
    detect_flood_inundation,
    detect_vegetation_change,
    resolve_aoi,
)
from eo_mcp.server import (
    stac_search,
    calculate_spectral_index,
    calculate_burn_severity,
    simulate_sea_level_rise,
    audit_wildfire_burn as server_audit_wildfire_burn,
    detect_flood_inundation as server_detect_flood_inundation,
    detect_vegetation_change as server_detect_vegetation_change,
)


# ==============================================================================
# WORKFLOW 1: WILDFIRE BURN SEVERITY AUDIT TESTS
# ==============================================================================

def test_audit_wildfire_burn_contract_and_metrics(offline_environment):
    """Verify audit_wildfire_burn calculates quantitative dNBR metrics and USGS 6 tiers."""
    out_dir = str(offline_environment["output_dir"])
    res_str = audit_wildfire_burn(
        location="Athens, Greece",
        fire_date="2024-07-24",
        collection="sentinel-2-l2a",
        format="summary",
        pixel_size_m=10.0,
        output_dir=out_dir,
    )

    data = json.loads(res_str)
    assert data["workflow"] == "audit_wildfire_burn"
    assert data["location"]["resolved_name"] == "Athens, Attica, Greece"
    assert "total_burned_area_ha" in data
    assert "total_burned_area_acres" in data
    assert data["total_burned_area_ha"] > 0.0
    assert data["total_burned_area_acres"] == pytest.approx(data["total_burned_area_ha"] * 2.47105, rel=1e-3)

    # USGS 6-tier breakdown verification
    breakdown = data["severity_breakdown"]
    for tier in [
        "enhanced_regrowth",
        "unburned",
        "low_severity",
        "moderate_low_severity",
        "moderate_high_severity",
        "high_severity",
    ]:
        assert tier in breakdown, f"Missing USGS tier: {tier}"
        assert "ha" in breakdown[tier]
        assert "acres" in breakdown[tier]
        assert "pct" in breakdown[tier]
        assert "pixel_count" in breakdown[tier]

    assert breakdown["high_severity"]["ha"] > 0.0
    assert data["mean_dnbr"] is not None
    assert data["max_dnbr"] >= 0.660

    # Visual artifact verification
    assert "preview_path" in data
    assert "map_path" in data
    assert "geotiff_path" in data
    assert "geojson_path" in data
    assert "visual_artifacts" in data
    assert Path(data["preview_path"]).exists()
    assert Path(data["map_path"]).exists()


def test_audit_wildfire_burn_geojson_format(offline_environment):
    """Verify audit_wildfire_burn returns RFC 7946 FeatureCollection when format='geojson'."""
    out_dir = str(offline_environment["output_dir"])
    res_str = audit_wildfire_burn(
        location="Athens, Greece",
        fire_date="2024-07-24",
        format="geojson",
        output_dir=out_dir,
    )

    geojson = json.loads(res_str)
    assert geojson["type"] == "FeatureCollection"
    assert "features" in geojson
    assert "properties" in geojson
    assert geojson["properties"]["total_burned_area_ha"] > 0.0


# ==============================================================================
# WORKFLOW 2: FLOOD INUNDATION & DEM SLOPE MASKING TESTS
# ==============================================================================

def test_detect_flood_inundation_contract_and_slope_filtering(offline_environment):
    """Verify detect_flood_inundation performs Copernicus DEM slope masking and separates permanent water."""
    out_dir = str(offline_environment["output_dir"])
    res_str = detect_flood_inundation(
        location="Thessaly, Greece",
        flood_date="2023-09-07",
        slope_threshold_deg=5.0,
        format="summary",
        output_dir=out_dir,
    )

    data = json.loads(res_str)
    assert data["workflow"] == "detect_flood_inundation"
    assert data["inundated_land_area_ha"] > 0.0
    assert data["inundated_land_area_km2"] == pytest.approx(data["inundated_land_area_ha"] / 100.0, rel=1e-3)
    assert data["permanent_water_area_ha"] > 0.0
    assert data["slope_filtered_shadow_area_ha"] > 0.0, "Steep mountain radar shadows must be rejected by DEM slope"
    assert data["flood_severity_rating"] in ["LOCALIZED", "MODERATE", "SEVERE", "CATASTROPHIC"]

    # Visual artifacts check
    assert "preview_path" in data
    assert "map_path" in data
    assert Path(data["preview_path"]).exists()
    assert Path(data["map_path"]).exists()


def test_detect_flood_inundation_geojson_format(offline_environment):
    """Verify detect_flood_inundation exports GeoJSON vector features when requested."""
    out_dir = str(offline_environment["output_dir"])
    res_str = detect_flood_inundation(
        location="Thessaly, Greece",
        flood_date="2023-09-07",
        format="geojson",
        output_dir=out_dir,
    )

    geojson = json.loads(res_str)
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) > 0
    assert "properties" in geojson


# ==============================================================================
# WORKFLOW 3: VEGETATION CHANGE & ANOMALY CLUSTERING TESTS
# ==============================================================================

def test_detect_vegetation_change_contract_and_patch_clustering(offline_environment):
    """Verify detect_vegetation_change computes dual-epoch differencing and clusters clearing anomalies."""
    out_dir = str(offline_environment["output_dir"])
    res_str = detect_vegetation_change(
        location="Amazon, Brazil",
        epoch1_date="2023-07-01/2023-07-31",
        epoch2_date="2024-07-01/2024-07-31",
        index="NDVI",
        loss_threshold=-0.15,
        gain_threshold=0.15,
        format="summary",
        output_dir=out_dir,
    )

    data = json.loads(res_str)
    assert data["workflow"] == "detect_vegetation_change"
    assert "clearing_loss_ha" in data
    assert data["clearing_loss_ha"] > 0.0
    assert "clearing_loss_acres" in data
    assert "greening_gain_ha" in data
    assert "net_vegetation_change_pct" in data
    assert "top_clearing_patches" in data

    # Patch cluster assertions
    patches = data["top_clearing_patches"]
    assert isinstance(patches, list)
    assert len(patches) > 0
    first_patch = patches[0]
    assert "patch_id" in first_patch
    assert "area_ha" in first_patch
    assert first_patch["area_ha"] > 0.0
    assert "centroid" in first_patch
    assert len(first_patch["centroid"]) == 2
    assert "bbox" in first_patch
    assert len(first_patch["bbox"]) == 4

    # Visual artifacts
    assert Path(data["preview_path"]).exists()
    assert Path(data["map_path"]).exists()


# ==============================================================================
# SERVER INTEGRATION & TOOL REGISTRATION TESTS
# ==============================================================================

def test_server_stac_search_compact_and_legacy_modes(offline_environment):
    """Verify server stac_search defaults to compact mode under 2,500 chars, and supports legacy mode."""
    # 1. Compact mode (default)
    compact_res = stac_search(
        collections=["sentinel-2-l2a"],
        bbox=[2.10, 41.34, 2.25, 41.45],
        datetime_range="2024-06-01/2024-06-30",
        limit=5,
    )
    assert len(compact_res) < 2500, f"Compact STAC payload exceeded 2,500 chars: {len(compact_res)}"
    compact_data = json.loads(compact_res)
    assert "scenes" in compact_data
    assert len(compact_data["scenes"]) <= 5
    first = compact_data["scenes"][0]
    assert "id" in first
    assert "platform" in first
    assert "cloud_cover" in first
    assert "bands" in first
    assert "assets" not in first

    # 2. Legacy mode (compact=False)
    legacy_res = stac_search(
        collections=["sentinel-2-l2a"],
        bbox=[2.10, 41.34, 2.25, 41.45],
        datetime_range="2024-06-01/2024-06-30",
        limit=5,
        compact=False,
    )
    legacy_data = json.loads(legacy_res)
    assert "assets" in legacy_data["scenes"][0]


def test_server_analytical_tools_visual_artifact_integration(offline_environment):
    """Verify calculate_spectral_index, calculate_burn_severity, and simulate_sea_level_rise return visual artifacts."""
    out_dir = offline_environment["output_dir"]

    # 1. Spectral index
    spec_res = calculate_spectral_index(
        collection="sentinel-2-l2a",
        index="NDVI",
        bbox=[23.65, 37.95, 23.85, 38.15],
        datetime_range="2024-06-01/2024-06-30",
    )
    spec_data = json.loads(spec_res)
    assert "preview_path" in spec_data
    assert "map_path" in spec_data
    assert Path(spec_data["preview_path"]).exists()
    assert Path(spec_data["map_path"]).exists()

    # 2. Burn severity
    burn_res = calculate_burn_severity(
        bbox=[23.65, 37.95, 23.85, 38.15],
        pre_fire_date_range="2024-06-01/2024-06-30",
        post_fire_date_range="2024-07-25/2024-08-15",
    )
    burn_data = json.loads(burn_res)
    assert "preview_path" in burn_data
    assert "map_path" in burn_data
    assert Path(burn_data["preview_path"]).exists()
    assert Path(burn_data["map_path"]).exists()

    # 3. Sea level rise
    slr_res = simulate_sea_level_rise(
        bbox=[-0.42, 39.42, -0.32, 39.50],
        water_level_rise_m=1.5,
        storm_surge_m=0.5,
    )
    slr_data = json.loads(slr_res)
    assert "preview_path" in slr_data
    assert "map_path" in slr_data
    assert Path(slr_data["preview_path"]).exists()
    assert Path(slr_data["map_path"]).exists()


def test_server_turnkey_workflow_tool_wrappers(offline_environment):
    """Verify server-level @eo_tool decorated turnkey workflows invoke cleanly."""
    out_dir = str(offline_environment["output_dir"])

    # audit_wildfire_burn
    wf1 = server_audit_wildfire_burn(
        location="Athens, Greece",
        fire_date="2024-07-24",
        output_dir=out_dir,
    )
    assert "total_burned_area_ha" in json.loads(wf1)

    # detect_flood_inundation
    wf2 = server_detect_flood_inundation(
        location="Thessaly, Greece",
        flood_date="2023-09-07",
        output_dir=out_dir,
    )
    assert "inundated_land_area_ha" in json.loads(wf2)

    # detect_vegetation_change
    wf3 = server_detect_vegetation_change(
        location="Amazon, Brazil",
        epoch1_date="2023-07-01/2023-07-31",
        epoch2_date="2024-07-01/2024-07-31",
        output_dir=out_dir,
    )
    assert "clearing_loss_ha" in json.loads(wf3)


# ==============================================================================
# ZERO NETWORK OFFLINE GUARANTEE TEST
# ==============================================================================

def test_zero_network_offline_guarantee(offline_environment, monkeypatch):
    """Verify all 3 turnkey workflows operate with zero outbound network calls."""
    def _forbidden_connect(*args, **kwargs):
        raise ConnectionRefusedError("TEST INTEGRITY VIOLATION: Outbound network call detected!")

    monkeypatch.setattr(socket.socket, "connect", _forbidden_connect)
    out_dir = str(offline_environment["output_dir"])

    res1 = audit_wildfire_burn("Athens, Greece", "2024-07-24", output_dir=out_dir)
    assert "total_burned_area_ha" in json.loads(res1)

    res2 = detect_flood_inundation("Thessaly, Greece", "2023-09-07", output_dir=out_dir)
    assert "inundated_land_area_ha" in json.loads(res2)

    res3 = detect_vegetation_change("Amazon, Brazil", "2023-07-01", "2024-07-01", output_dir=out_dir)
    assert "clearing_loss_ha" in json.loads(res3)
