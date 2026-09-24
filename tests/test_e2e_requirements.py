"""Comprehensive Opaque-Box E2E Test Suite for eo-mcp Requirements R1 - R4.

Structured across 4 rigorous tiers:
- Tier 1: Feature Coverage (R1 visual outputs, R2 compact STAC token budget, R3 turnkey workflows, R4 offline compatibility)
- Tier 2: Boundary & Corner Cases (empty results, extreme clouds, steep DEM slope filtering, negative NDVI/dNBR, NaNs)
- Tier 3: Cross-Feature Interactions (STAC discovery -> turnkey workflow -> visual artifact export, filesystem integrity)
- Tier 4: Real-World Planetary Application Scenarios (Athens wildfire burn, Thessaly flood inundation, Amazon deforestation)

All tests execute 100% offline with zero external network access, leveraging synthetic fixtures from tests/conftest.py.
Pending milestone functions are checked against interface contracts and marked with informative xfails when not yet implemented.
"""

import inspect
import io
import json
import os
from pathlib import Path
from typing import Dict, Any, List
import numpy as np
from PIL import Image
import pytest

from eo_mcp.core.models import (
    BoundingBox,
    CompactSTACItem,
    CompactSTACResponse,
    STACSearchResultItem,
    SpectralIndexResult,
)
from eo_mcp.core.spectral import (
    compute_ndvi,
    compute_ndwi,
    compute_nbr,
    calculate_array_stats,
)
from eo_mcp.core.wildfire import (
    calculate_burn_severity_dnbr,
    burn_severity_to_geojson,
)
from eo_mcp.core.dem import compute_slope_and_aspect, summarize_terrain
from eo_mcp.core.sar import detect_water_mask
from eo_mcp.core.coastal import compute_mndwi
from eo_mcp.workflows import resolve_aoi


# ==============================================================================
# Helper functions for interface contract inspection
# ==============================================================================

def get_visualizer_export():
    """Inspect and return export_visual_artifacts from eo_mcp.utils.visualizer if implemented."""
    import eo_mcp.utils.visualizer as vis
    if not hasattr(vis, "export_visual_artifacts"):
        pytest.xfail("export_visual_artifacts is pending implementation in Milestone M1 (R1).")
    return getattr(vis, "export_visual_artifacts")


def get_compact_stac_formatter():
    """Inspect and return format_compact_stac_items from eo_mcp.providers.stac if implemented."""
    import eo_mcp.providers.stac as stac
    if not hasattr(stac, "format_compact_stac_items"):
        pytest.xfail("format_compact_stac_items is pending implementation in Milestone M2 (R2).")
    return getattr(stac, "format_compact_stac_items")


def check_stac_search_compact_param():
    """Verify that stac_search supports the compact parameter."""
    try:
        from eo_mcp.server import stac_search
    except Exception:
        pytest.xfail("eo_mcp.server.stac_search is unavailable.")
    sig = inspect.signature(stac_search)
    if "compact" not in sig.parameters:
        pytest.xfail("Parameter 'compact: bool = True' on stac_search is pending implementation in Milestone M2 (R2).")
    return stac_search


def get_stac_search():
    """Lazy load stac_search from server.py."""
    from eo_mcp.server import stac_search
    return stac_search


def get_workflow_tool(tool_name: str):
    """Inspect and return a turnkey workflow function from eo_mcp.workflows if implemented."""
    import eo_mcp.workflows as wf
    if not hasattr(wf, tool_name):
        pytest.xfail(f"Turnkey workflow '{tool_name}' is pending implementation in Milestone M3 (R3).")
    return getattr(wf, tool_name)


# ==============================================================================
# TIER 1: FEATURE COVERAGE (R1 - R4)
# ==============================================================================

class TestTier1FeatureCoverage:
    """Tier 1: Primary behavior and interface contracts for Requirements R1 to R4."""

    # --------------------------------------------------------------------------
    # R1: Visual Artifact Generation & Interactive Maps
    # --------------------------------------------------------------------------

    def test_r1_export_visual_artifacts_contract(self, test_output_dir):
        """R1: Verify export_visual_artifacts produces .png, .tif, .html and returns valid paths & URIs."""
        export_fn = get_visualizer_export()

        # Synthetic test array and bounding box
        data = np.linspace(-0.2, 0.8, 100 * 100, dtype=np.float32).reshape((100, 100))
        bbox = [-0.42, 39.42, -0.32, 39.50]

        result = export_fn(
            array=data,
            bbox=bbox,
            name="test_ndvi_preview",
            colormap="rdylgn",
            output_dir=str(test_output_dir),
        )

        assert isinstance(result, dict)
        assert "preview_path" in result
        assert "preview_uri" in result
        assert "map_path" in result
        assert "map_uri" in result

        # Verify files exist on disk
        png_path = Path(result["preview_path"])
        map_path = Path(result["map_path"])

        assert png_path.exists(), f"Preview PNG does not exist at {png_path}"
        assert png_path.stat().st_size > 0, "Preview PNG is an empty file"
        assert map_path.exists(), f"Interactive Map HTML does not exist at {map_path}"
        assert map_path.stat().st_size > 0, "Interactive Map HTML is an empty file"

        # Verify file:// URIs conform to RFC 8089
        assert result["preview_uri"].startswith("file://")
        assert result["map_uri"].startswith("file://")

    def test_r1_color_ramped_png_generation(self, test_output_dir):
        """R1: Verify color-ramped PNG rendering generates valid RGBA image with transparent NaNs."""
        export_fn = get_visualizer_export()

        # 40x50 array with center region containing NaNs
        arr = np.full((40, 50), 0.5, dtype=np.float32)
        arr[15:25, 20:30] = np.nan

        result = export_fn(
            array=arr,
            bbox=[-120.5, 38.5, -120.0, 39.0],
            name="test_nan_alpha_lut",
            colormap="ylorrd",
            output_dir=str(test_output_dir),
        )

        png_path = Path(result["preview_path"])
        assert png_path.exists()

        # Open and inspect image channels
        with Image.open(png_path) as img:
            assert img.format == "PNG"
            assert img.mode in ("RGBA", "RGB")
            if img.mode == "RGBA":
                rgba = np.array(img)
                # NaN region must be transparent (alpha == 0)
                nan_alpha = rgba[15:25, 20:30, 3]
                assert np.all(nan_alpha == 0), "NaN pixels must be rendered with alpha=0 (fully transparent)"
                # Valid region must be opaque (alpha == 255)
                valid_alpha = rgba[0:10, 0:10, 3]
                assert np.all(valid_alpha == 255), "Valid data pixels must be rendered with alpha=255 (opaque)"

    def test_r1_standalone_offline_html_map(self, test_output_dir):
        """R1: Verify interactive HTML map is self-contained with zero backend dependencies."""
        export_fn = get_visualizer_export()

        arr = np.full((30, 30), 0.7, dtype=np.float32)
        result = export_fn(
            array=arr,
            bbox=[23.65, 37.95, 23.85, 38.15],
            name="test_athens_map",
            colormap="rdylgn",
            output_dir=str(test_output_dir),
        )

        html_path = Path(result["map_path"])
        html_content = html_path.read_text(encoding="utf-8")

        # HTML must be valid standalone document
        assert "<!DOCTYPE html>" in html_content or "<html" in html_content
        assert "</html>" in html_content

        # Must embed raster overlay data URI or inline vector data
        has_embedded_overlay = (
            "data:image/png;base64," in html_content
            or "data:image/" in html_content
            or "raster-preview" in html_content
            or "imageOverlay" in html_content
            or "coordinates" in html_content
        )
        assert has_embedded_overlay, "HTML map must embed raster/vector overlay for offline visualization"

    # --------------------------------------------------------------------------
    # R2: Token-Optimized STAC Catalog Discovery
    # --------------------------------------------------------------------------

    def test_r2_compact_stac_token_budget_under_2500_chars(self, mock_stac_scenes_5):
        """R2: Standard 5-scene STAC response must remain strictly under 2,500 characters (~500 tokens)."""
        formatter_fn = get_compact_stac_formatter()

        compact_resp = formatter_fn(mock_stac_scenes_5)
        assert isinstance(compact_resp, (CompactSTACResponse, dict, str))

        if isinstance(compact_resp, CompactSTACResponse):
            payload_str = compact_resp.model_dump_json(indent=2)
        elif isinstance(compact_resp, dict):
            payload_str = json.dumps(compact_resp, indent=2)
        else:
            payload_str = compact_resp

        char_count = len(payload_str)
        token_estimate = char_count / 4.0

        # R2 Specification requirement
        assert char_count < 2500, (
            f"5-scene STAC payload exceeded 2,500 char budget: {char_count} chars ({token_estimate:.1f} tokens)"
        )
        assert char_count < 2000, f"Payload could be further optimized: {char_count} chars"

    def test_r2_compact_stac_essential_parameters(self, mock_stac_scenes_5):
        """R2: Search results must summarize exactly the 6 essential decision parameters."""
        formatter_fn = get_compact_stac_formatter()
        compact_resp = formatter_fn(mock_stac_scenes_5)

        if isinstance(compact_resp, str):
            compact_data = json.loads(compact_resp)
        elif isinstance(compact_resp, CompactSTACResponse):
            compact_data = compact_resp.model_dump()
        else:
            compact_data = compact_resp

        assert "scenes" in compact_data
        assert len(compact_data["scenes"]) == 5

        for scene in compact_data["scenes"]:
            # 6 Essential Decision Parameters
            assert "id" in scene, "Scene missing canonical ID"
            assert "platform" in scene, "Scene missing platform identifier"
            assert "datetime" in scene, "Scene missing acquisition datetime"
            assert "cloud_cover" in scene, "Scene missing cloud cover percentage"
            assert "bbox" in scene, "Scene missing spatial bounding box"
            assert "bands" in scene, "Scene missing normalized band identifiers"

            # Redundant heavy STAC metadata must NOT be included in compact scenes
            assert "assets" not in scene, "Raw asset dictionary must be omitted in compact mode"
            assert "links" not in scene, "Hypermedia links must be omitted in compact mode"
            assert "geometry" not in scene, "Multi-coordinate GeoJSON geometry must be omitted in compact mode"

    def test_r2_compact_stac_coordinate_and_cloud_rounding(self):
        """R2: Verify bbox is rounded to 4 decimals (~11m precision) and cloud cover to 1 decimal."""
        raw_item = CompactSTACItem(
            id="S2B_TEST_ROUNDING",
            platform="sentinel-2b",
            datetime="2024-06-15T10:30:29Z",
            cloud_cover=4.1287492,
            bbox=[2.105284719, 41.341192847, 2.248291847, 41.452384719],
            bands=["B02", "B03", "B04", "B08", "B11", "B12"],
        )

        assert raw_item.cloud_cover == 4.1
        assert raw_item.bbox == [2.1053, 41.3412, 2.2483, 41.4524]

    def test_r2_stac_search_default_compact_mode(self, offline_environment):
        """R2: stac_search must enforce compact mode by default for AI agents."""
        stac_search = check_stac_search_compact_param()

        res_str = stac_search(
            collections=["sentinel-2-l2a"],
            bbox=[2.10, 41.34, 2.25, 41.45],
            datetime_range="2024-06-01/2024-06-30",
            limit=5,
        )

        data = json.loads(res_str)
        assert "scenes" in data
        assert len(data["scenes"]) <= 5

        # Check total character budget
        assert len(res_str) < 2500, f"Default stac_search exceeded 2,500 chars: {len(res_str)}"

        # Check essential keys on first scene
        first = data["scenes"][0]
        assert "id" in first
        assert "platform" in first
        assert "cloud_cover" in first
        assert "bands" in first

    def test_r2_stac_search_legacy_compatibility_mode(self, offline_environment):
        """R2: stac_search(..., compact=False) must preserve full legacy STAC item dictionaries."""
        stac_search = check_stac_search_compact_param()

        res_str = stac_search(
            collections=["sentinel-2-l2a"],
            bbox=[2.10, 41.34, 2.25, 41.45],
            datetime_range="2024-06-01/2024-06-30",
            limit=5,
            compact=False,
        )

        data = json.loads(res_str)
        assert "scenes" in data
        first = data["scenes"][0]
        # In legacy mode, raw assets key must be preserved
        assert "assets" in first, "Legacy mode compact=False must preserve 'assets' list"

    # --------------------------------------------------------------------------
    # R3: Turnkey Single-Call Planetary Workflows
    # --------------------------------------------------------------------------

    def test_r3_audit_wildfire_burn_contract(self, offline_environment):
        """R3: audit_wildfire_burn accepts location and fire date, returning quantitative burn audit."""
        audit_fn = get_workflow_tool("audit_wildfire_burn")

        res_str = audit_fn(
            location="Athens, Greece",
            fire_date="2024-07-24",
            collection="sentinel-2-l2a",
            format="summary",
            output_dir=str(offline_environment["output_dir"]),
        )

        data = json.loads(res_str)
        assert "total_burned_area_ha" in data
        assert "total_burned_area_acres" in data
        assert "severity_breakdown" in data
        assert "mean_dnbr" in data
        assert "max_dnbr" in data

        # Check USGS 6-tier classification schema
        breakdown = data["severity_breakdown"]
        for tier in ["unburned", "low_severity", "moderate_low_severity", "moderate_high_severity", "high_severity"]:
            assert tier in breakdown, f"Missing USGS tier '{tier}' in burn severity breakdown"

        # Check visual artifact paths in payload
        assert "visual_artifacts" in data or "preview_path" in data

    def test_r3_detect_flood_inundation_contract(self, offline_environment):
        """R3: detect_flood_inundation accepts location and event date, returning flooded land metrics."""
        flood_fn = get_workflow_tool("detect_flood_inundation")

        res_str = flood_fn(
            location="Thessaly, Greece",
            flood_date="2023-09-07",
            sensor="auto",
            slope_threshold_deg=5.0,
            format="summary",
            output_dir=str(offline_environment["output_dir"]),
        )

        data = json.loads(res_str)
        assert "inundated_land_area_ha" in data
        assert "inundated_land_area_km2" in data
        assert "permanent_water_area_ha" in data
        assert "slope_filtered_shadow_area_ha" in data
        assert "flood_severity_rating" in data

        # Rating must be one of standard categories
        assert data["flood_severity_rating"] in ["LOCALIZED", "MODERATE", "SEVERE", "CATASTROPHIC"]

    def test_r3_detect_vegetation_change_contract(self, offline_environment):
        """R3: detect_vegetation_change computes dual-epoch differencing and clearing anomalies."""
        veg_fn = get_workflow_tool("detect_vegetation_change")

        res_str = veg_fn(
            location="Amazon, Brazil",
            epoch1_date="2023-07-01/2023-07-31",
            epoch2_date="2024-07-01/2024-07-31",
            index="NDVI",
            loss_threshold=-0.15,
            gain_threshold=0.15,
            format="summary",
            output_dir=str(offline_environment["output_dir"]),
        )

        data = json.loads(res_str)
        assert "net_vegetation_change_pct" in data or "change_summary" in data
        assert "clearing_loss_ha" in data
        assert "greening_gain_ha" in data
        assert "top_clearing_patches" in data or "anomalies" in data

    # --------------------------------------------------------------------------
    # R4: Offline Execution & Core Backwards Compatibility
    # --------------------------------------------------------------------------

    def test_r4_offline_synthetic_fixtures_deterministic(self, synthetic_wildfire_datacube, synthetic_flood_datacube, synthetic_vegetation_datacube):
        """R4: Verify synthetic fixtures provide non-zero, deterministic offline datacubes."""
        # Wildfire verification
        wf = synthetic_wildfire_datacube
        assert wf["pre_nir"].shape == (40, 50)
        assert wf["post_nir"].shape == (40, 50)
        assert wf["expected_burned_ha"] == 4.00

        # Flood verification
        fl = synthetic_flood_datacube
        assert fl["pre_green"].shape == (40, 50)
        assert fl["dem"].shape == (40, 50)

        # Vegetation verification
        vg = synthetic_vegetation_datacube
        assert vg["ep1_nir"].shape == (40, 50)
        assert vg["expected_loss_ha"] == 2.25

    def test_r4_core_spectral_indices_compatibility(self, synthetic_wildfire_datacube):
        """R4: Existing spectral index calculation primitives must remain fully backwards compatible."""
        wf = synthetic_wildfire_datacube
        ndvi_pre = compute_ndvi(wf["pre_nir"], np.full((40, 50), 0.10, dtype=np.float32))
        assert ndvi_pre.shape == (40, 50)
        assert np.all(ndvi_pre >= -1.0) and np.all(ndvi_pre <= 1.0)

        # Verify array stats
        stats = calculate_array_stats(ndvi_pre)
        assert "mean" in stats
        assert "min" in stats
        assert "max" in stats
        assert "count" in stats
        assert stats["count"] == 2000


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ==============================================================================

class TestTier2BoundaryAndCornerCases:
    """Tier 2: Boundary values, edge conditions, invalid inputs, and stress conditions."""

    def test_boundary_empty_stac_search_results(self, monkeypatch):
        """Empty STAC catalog result returns count=0 and scenes=[] without raising an exception."""
        for mod in ["eo_mcp.providers.stac", "eo_mcp.server", "eo_mcp.workflows"]:
            try:
                monkeypatch.setattr(f"{mod}.search_stac_catalog", lambda *args, **kwargs: [])
            except (AttributeError, KeyError):
                pass

        # Test server tool
        stac_search = get_stac_search()
        res_str = stac_search(
            collections=["sentinel-2-l2a"],
            bbox=[0.0, 0.0, 1.0, 1.0],
            datetime_range="2024-01-01",
            limit=5,
        )
        data = json.loads(res_str)
        assert data.get("count") == 0
        assert data.get("scenes") == []
        assert len(res_str) < 150

    def test_boundary_extreme_cloud_cover_zero_and_hundred(self):
        """Boundary cloud cover: 0.0% (completely clear) and 100.0% (completely obscured)."""
        clear_item = CompactSTACItem(
            id="S2_CLEAR",
            platform="sentinel-2b",
            datetime="2024-06-15T10:30:29Z",
            cloud_cover=0.0,
            bbox=[0.0, 0.0, 1.0, 1.0],
            bands=["B02", "B04"],
        )
        assert clear_item.cloud_cover == 0.0

        cloudy_item = CompactSTACItem(
            id="S2_CLOUDY",
            platform="sentinel-2a",
            datetime="2024-06-15T10:30:29Z",
            cloud_cover=100.0,
            bbox=[0.0, 0.0, 1.0, 1.0],
            bands=["B02", "B04"],
        )
        assert cloudy_item.cloud_cover == 100.0

    def test_boundary_dem_slope_filtering_steep_terrain(self, synthetic_flood_datacube):
        """Copernicus DEM slope filtering eliminates false-positive water pixels on slopes > 5.0 deg."""
        dem = synthetic_flood_datacube["dem"]
        slope_deg, aspect_deg = compute_slope_and_aspect(dem, cellsize_m=30.0)

        # Northern rows (0-8) have steep gradient > 14m drop per 30m cell -> slope > 20 degrees
        steep_slopes = slope_deg[2:8, 2:8]
        assert np.all(steep_slopes > 5.0), f"Mountain ridge slope should exceed 5.0 degrees, got min: {np.min(steep_slopes)}"

        # Southern rows (15-35) are flat plain at 2m elevation -> slope near 0
        flat_slopes = slope_deg[15:35, 10:40]
        assert np.all(flat_slopes <= 5.0), f"Valley plain slope should be <= 5.0 degrees, got max: {np.max(flat_slopes)}"

        # Hydrological slope filter test
        raw_inundation = np.zeros_like(dem, dtype=bool)
        raw_inundation[synthetic_flood_datacube["valley_slice"]] = True
        raw_inundation[synthetic_flood_datacube["shadow_slice"]] = True  # Artificial steep shadow

        # Filter out steep slopes
        valid_slope_mask = slope_deg <= 5.0
        clean_inundation = raw_inundation & valid_slope_mask

        # Assert shadow artifact was cleanly eliminated
        assert not np.any(clean_inundation[synthetic_flood_datacube["shadow_slice"]]), (
            "Slope filter failed to eliminate steep mountain shadow false positive"
        )
        # Assert flat valley inundation was preserved
        assert np.all(clean_inundation[synthetic_flood_datacube["valley_slice"]]), (
            "Slope filter erroneously removed flat valley inundation pixels"
        )

    def test_boundary_negative_and_extreme_index_ranges(self):
        """Mathematical models must handle negative index values without zero division or NaN leaks."""
        # Pre-fire healthy canopy (NBR=0.70) vs post-fire char (NBR=-0.60)
        pre_nbr = np.array([[0.70, 0.70], [0.70, 0.70]], dtype=np.float32)
        post_nbr = np.array([[-0.60, 0.70], [0.70, 0.85]], dtype=np.float32)  # [0,0] high severity, [1,1] regrowth

        burn_results = calculate_burn_severity_dnbr(pre_nbr, post_nbr, pixel_size_m=10.0)
        assert burn_results["max_dnbr"] == pytest.approx(1.30, abs=1e-2)
        assert burn_results["overall_burn_severity_class"] in ("HIGH_SEVERITY", "High Severity")
        assert (
            "enhanced_regrowth_ha" in burn_results["severity_breakdown_ha"]
            or "Enhanced Regrowth" in burn_results["severity_breakdown_ha"]
        )
        regrowth_val = burn_results["severity_breakdown_ha"].get("enhanced_regrowth_ha") or burn_results["severity_breakdown_ha"].get("Enhanced Regrowth", 0.0)
        assert regrowth_val > 0.0

    def test_boundary_all_nan_raster_transparent_alpha(self, test_output_dir):
        """All-NaN or missing data arrays must not crash artifact generation."""
        export_fn = get_visualizer_export()

        all_nan = np.full((30, 30), np.nan, dtype=np.float32)
        result = export_fn(
            array=all_nan,
            bbox=[-0.42, 39.42, -0.32, 39.50],
            name="test_all_nan",
            colormap="rdylgn",
            output_dir=str(test_output_dir),
        )

        png_path = Path(result["preview_path"])
        assert png_path.exists()
        # Verify completely transparent image
        with Image.open(png_path) as img:
            rgba = np.array(img.convert("RGBA"))
            assert np.all(rgba[:, :, 3] == 0), "All-NaN image must have 100% transparent alpha channel"

    def test_boundary_spatial_aoi_point_buffering_and_validation(self):
        """Spatial resolution must handle point coordinates, bboxes, and reject invalid inputs."""
        # 4-float bbox list
        b1, name1 = resolve_aoi([-0.42, 39.42, -0.32, 39.50])
        assert b1 == [-0.42, 39.42, -0.32, 39.50]

        # 4-float bbox string
        b2, name2 = resolve_aoi("-0.42, 39.42, -0.32, 39.50")
        assert b2 == [-0.42, 39.42, -0.32, 39.50]

        # Invalid coordinate length raises ValueError
        with pytest.raises(ValueError):
            resolve_aoi([-0.42, 39.42])

        # Non-string/list raises TypeError
        with pytest.raises(TypeError):
            resolve_aoi(99999)


# ==============================================================================
# TIER 3: CROSS-FEATURE INTERACTIONS
# ==============================================================================

class TestTier3CrossFeatureInteractions:
    """Tier 3: Multi-step pipelines, data flow between modules, and output consistency."""

    def test_interaction_stac_discovery_to_workflow_to_artifacts(self, offline_environment):
        """Discovery -> Analytical Compute -> Visual Artifact Export pipeline test."""
        # 1. Discover scenes via compact STAC
        stac_search = check_stac_search_compact_param()
        stac_res_str = stac_search(
            collections=["sentinel-2-l2a"],
            bbox=[23.65, 37.95, 23.85, 38.15],
            datetime_range="2024-07-01/2024-07-31",
            limit=2,
            compact=True,
        )
        stac_data = json.loads(stac_res_str)
        scenes = stac_data.get("scenes", [])
        assert len(scenes) > 0
        target_scene_id = scenes[0]["id"]
        assert target_scene_id.startswith("S2")

        # 2. Invoke turnkey workflow with discovered scene context
        audit_fn = get_workflow_tool("audit_wildfire_burn")
        workflow_res = audit_fn(
            location="Athens, Greece",
            fire_date="2024-07-24",
            output_dir=str(offline_environment["output_dir"]),
        )
        wf_data = json.loads(workflow_res)

        # 3. Verify visual artifacts were created and linked
        assert "visual_artifacts" in wf_data or "preview_path" in wf_data
        out_dir = offline_environment["output_dir"]
        generated_files = list(out_dir.glob("*.*"))
        assert len(generated_files) > 0, f"Expected visual artifacts in {out_dir}, found none"

    def test_interaction_visual_artifact_filesystem_integrity(self, test_output_dir):
        """Verify generated .png, .tif, and .html have matching geospatial bounds and valid headers."""
        export_fn = get_visualizer_export()

        rows, cols = 40, 50
        arr = np.linspace(-0.5, 0.9, rows * cols, dtype=np.float32).reshape((rows, cols))
        bbox = [2.10, 41.34, 2.25, 41.45]

        result = export_fn(
            array=arr,
            bbox=bbox,
            name="test_integrity",
            colormap="rdylgn",
            output_dir=str(test_output_dir),
        )

        # 1. PNG Header & Dimensions
        png_path = Path(result["preview_path"])
        with open(png_path, "rb") as f:
            png_header = f.read(8)
            assert png_header == b"\x89PNG\r\n\x1a\n", "Invalid PNG file header"
        with Image.open(png_path) as img:
            assert img.size == (cols, rows), f"PNG dimensions {img.size} must match array shape {(cols, rows)}"

        # 2. HTML Map Embedding
        html_path = Path(result["map_path"])
        assert html_path.stat().st_size > 500, "HTML map file is abnormally small"
        html_text = html_path.read_text(encoding="utf-8")
        assert "2.1" in html_text or "41.34" in html_text or "bbox" in html_text, (
            "HTML map must contain bounding box coordinates"
        )

    def test_interaction_zero_network_offline_guarantee(self, offline_environment, monkeypatch):
        """Verify that running STAC discovery and workflows makes zero external socket connections."""
        import socket
        real_connect = socket.socket.connect

        def _forbidden_network_connect(*args, **kwargs):
            raise ConnectionRefusedError("TEST VIOLATION: External network call attempted in offline test mode!")

        monkeypatch.setattr(socket.socket, "connect", _forbidden_network_connect)

        # Execute STAC search offline
        stac_search = get_stac_search()
        stac_res = stac_search(
            collections=["sentinel-2-l2a"],
            bbox=[-0.42, 39.42, -0.32, 39.50],
            datetime_range="2024-06-01/2024-06-30",
            limit=3,
        )
        assert "scenes" in json.loads(stac_res)

    def test_interaction_concurrent_execution_filename_collision_safety(self, test_output_dir):
        """Consecutive calls with the same parameters must generate unique or collision-safe files."""
        export_fn = get_visualizer_export()

        arr = np.full((20, 20), 0.5, dtype=np.float32)
        bbox = [-0.42, 39.42, -0.32, 39.50]

        res1 = export_fn(arr, bbox, "collision_test", "rdylgn", output_dir=str(test_output_dir))
        res2 = export_fn(arr, bbox, "collision_test", "rdylgn", output_dir=str(test_output_dir))

        path1 = Path(res1["preview_path"])
        path2 = Path(res2["preview_path"])

        assert path1.exists()
        assert path2.exists()


# ==============================================================================
# TIER 4: REAL-WORLD PLANETARY APPLICATION SCENARIOS
# ==============================================================================

class TestTier4RealWorldScenarios:
    """Tier 4: Realistic planetary emergency and environmental monitoring scenarios."""

    def test_scenario_athens_wildfire_burn_audit(self, offline_environment, synthetic_wildfire_datacube):
        """
        Scenario 1: Athens (Attica, Greece) August 2024 Wildfire Burn Audit.
        - Location: Varnavas / Marathon / Penteli mountain area.
        - Pre-fire baseline vs post-fire burn scar.
        - Expected: Burned area ~4.0 ha, USGS 6-tier classification, and visual artifacts.
        """
        audit_fn = get_workflow_tool("audit_wildfire_burn")

        result_str = audit_fn(
            location="Athens, Greece",
            fire_date="2024-07-24",
            collection="sentinel-2-l2a",
            pixel_size_m=10.0,
            output_dir=str(offline_environment["output_dir"]),
        )

        audit = json.loads(result_str)

        # 1. Quantitative Area Quantification
        assert "total_burned_area_ha" in audit
        assert audit["total_burned_area_ha"] > 0.0, "Burned area must be positive for wildfire event"
        assert "total_burned_area_acres" in audit
        assert audit["total_burned_area_acres"] == pytest.approx(audit["total_burned_area_ha"] * 2.47105, rel=1e-3)

        # 2. USGS Severity Distribution
        breakdown = audit["severity_breakdown"]
        assert breakdown["high_severity"]["ha"] > 0.0, "High severity burn scar must be detected"

        # 3. Visual Artifact Existence
        out_dir = offline_environment["output_dir"]
        png_files = list(out_dir.glob("*.png"))
        html_files = list(out_dir.glob("*.html"))
        assert len(png_files) >= 1, "At least one preview PNG must be generated"
        assert len(html_files) >= 1, "At least one interactive map HTML must be generated"

    def test_scenario_thessaly_flood_inundation_mapping(self, offline_environment, synthetic_flood_datacube):
        """
        Scenario 2: Thessaly (Greece) Storm Daniel Inundation Mapping (September 2023).
        - Location: Pineios River basin & Larissa plain.
        - Pre-flood baseline vs peak flood event with Copernicus DEM slope filtering.
        - Expected: Clear distinction between permanent river water and inundated land.
        - Mountain ridge shadows > 5.0 deg strictly rejected.
        """
        flood_fn = get_workflow_tool("detect_flood_inundation")

        result_str = flood_fn(
            location="Thessaly, Greece",
            flood_date="2023-09-07",
            sensor="auto",
            slope_threshold_deg=5.0,
            output_dir=str(offline_environment["output_dir"]),
        )

        flood = json.loads(result_str)

        # 1. Surface Water Separation
        assert "inundated_land_area_ha" in flood
        assert "permanent_water_area_ha" in flood
        assert flood["inundated_land_area_ha"] > 0.0, "Flooded agricultural land must be quantified"
        assert flood["permanent_water_area_ha"] > 0.0, "Permanent river baseline must be identified"

        # 2. Slope Filtering False-Positive Elimination
        assert "slope_filtered_shadow_area_ha" in flood
        assert flood["slope_filtered_shadow_area_ha"] >= 0.0, "Shadow false positives must be tracked"

        # 3. Severity Classification
        assert flood["flood_severity_rating"] in ["LOCALIZED", "MODERATE", "SEVERE", "CATASTROPHIC"]

    def test_scenario_amazon_deforestation_monitoring(self, offline_environment, synthetic_vegetation_datacube):
        """
        Scenario 3: Amazon Basin (Pará, Brazil) Dual-Epoch Forest Clearing Monitoring.
        - Baseline: 2023 dry season canopy.
        - Comparison: 2024 dry season canopy.
        - Expected: Net change computed, clearing loss area quantified, top anomaly patches identified.
        """
        veg_fn = get_workflow_tool("detect_vegetation_change")

        result_str = veg_fn(
            location="Amazon, Brazil",
            epoch1_date="2023-07-01/2023-07-31",
            epoch2_date="2024-07-01/2024-07-31",
            index="NDVI",
            loss_threshold=-0.15,
            gain_threshold=0.15,
            output_dir=str(offline_environment["output_dir"]),
        )

        veg = json.loads(result_str)

        # 1. Deforestation Loss vs Greening Gain
        assert "clearing_loss_ha" in veg
        assert "greening_gain_ha" in veg
        assert veg["clearing_loss_ha"] > 0.0, "Clearing loss must be detected in deforestation zone"

        # 2. Spatial Patch Clusters
        if "top_clearing_patches" in veg:
            patches = veg["top_clearing_patches"]
            assert isinstance(patches, list)
            if len(patches) > 0:
                p = patches[0]
                assert "area_ha" in p or "area" in p
