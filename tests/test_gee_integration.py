"""Unit tests for Google Earth Engine (GEE) integration in eo-mcp.

Verifies:
1. 50-year sensor selection priorities and nominal scales across all eras (1972 to present).
2. Standard band harmonization mappings and computable spectral index feasibility.
3. In-memory session composite registry lifecycle.
4. Scientific factuality assumption auditing and Mermaid pipeline diagram synthesis.
5. Cached catalog search ranking and fallback catalog integrity.
6. Season date range calculations including cross-year wrapping.
7. Registry tool category and profile discovery.
8. Soft-import resilience and informative diagnostics when GEE is uninitialized.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from eo_mcp.core.gee.sensors import (
    COLLECTIONS,
    STANDARD_BANDS,
    LANDSAT57_BAND_MAP,
    LANDSAT89_BAND_MAP,
    SENTINEL2_BAND_MAP,
    MSS_BAND_MAP,
    get_sensors_for_year,
    get_nominal_scale,
    harmonized_bands_for,
)
from eo_mcp.core.gee.indices import (
    KNOWN_INDICES,
    computable_indices,
)
from eo_mcp.core.gee.composite_registry import (
    register_composite,
    get_composite,
    list_composites,
    update_composite,
    clear_composites,
)
from eo_mcp.core.gee.composite_builder import (
    build_date_range,
)
from eo_mcp.core.gee.factuality import (
    audit_factuality_assumptions,
    generate_mermaid_pipeline,
)
from eo_mcp.core.gee.catalog import (
    search_catalog,
    get_dataset_entry,
    _FALLBACK_CURATED_DATASETS,
)
from eo_mcp.core.gee.session import (
    is_ee_installed,
    is_ee_initialized,
    is_ee_available,
    get_ee_status,
)
from eo_mcp.registry import (
    TOOL_CATEGORIES,
    PROFILES,
    is_tool_enabled,
    get_allowed_tools,
)


class TestGEESensorsAndHarmonization:
    """Tests for multi-sensor era mapping and band standardization."""

    def test_era_sensor_priorities(self):
        # 1975 -> Landsat MSS 1/2/3
        mss_sensors = get_sensors_for_year(1975)
        assert mss_sensors[0] == "landsat_mss_l1"
        assert get_nominal_scale(mss_sensors[0]) == 60

        # 1990 -> Landsat 5 TM
        l5_sensors = get_sensors_for_year(1990)
        assert l5_sensors[0] == "landsat5_t1_sr"
        assert get_nominal_scale(l5_sensors[0]) == 30

        # 2005 -> Landsat 5 TM + Landsat 7 ETM+
        l7_sensors = get_sensors_for_year(2005)
        assert "landsat5_t1_sr" in l7_sensors
        assert "landsat7_t1_sr" in l7_sensors

        # 2013 -> Landsat 8 OLI
        l8_sensors = get_sensors_for_year(2013)
        assert l8_sensors[0] == "landsat8_sr"

        # 2018 -> Sentinel-2 + Landsat 8
        s2_sensors = get_sensors_for_year(2018)
        assert s2_sensors[0] == "sentinel2_sr"
        assert s2_sensors[1] == "landsat8_sr"
        assert get_nominal_scale("sentinel2_sr") == 10

        # 2024 -> Sentinel-2 + Landsat 9
        recent_sensors = get_sensors_for_year(2024)
        assert recent_sensors[0] == "sentinel2_sr"
        assert recent_sensors[1] == "landsat9_sr"

    def test_harmonized_bands_for_sensors(self):
        s2_bands = harmonized_bands_for("sentinel2_sr")
        assert "Blue" in s2_bands
        assert "Green" in s2_bands
        assert "Red" in s2_bands
        assert "NIR" in s2_bands
        assert "SWIR1" in s2_bands
        assert "SWIR2" in s2_bands
        assert "RedEdge1" in s2_bands

        l8_bands = harmonized_bands_for("landsat8_sr")
        assert l8_bands == ["Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2"]

        mss_bands = harmonized_bands_for("landsat_mss_l1")
        assert "Green" in mss_bands
        assert "Red" in mss_bands
        assert "NIR" in mss_bands
        assert "Blue" not in mss_bands
        assert "SWIR1" not in mss_bands


class TestGEEIndicesFeasibility:
    """Tests for spectral index registry and computable validation."""

    def test_computable_indices_sentinel2(self):
        s2_bands = ["Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2", "RedEdge1"]
        requested = ["NDVI", "EVI", "SAVI", "NDWI", "NDRE", "NBR", "NDBI"]
        computable = computable_indices(requested, s2_bands)
        assert len(computable) == len(requested)
        assert "NDRE" in computable
        assert "EVI" in computable

    def test_computable_indices_mss_omits_unfeasible(self):
        # Landsat MSS only has Green, Red, NIR, NIR2
        mss_bands = ["Green", "Red", "NIR", "NIR2"]
        requested = ["NDVI", "EVI", "NDWI", "NDMI", "NBR", "GreenRed"]
        computable = computable_indices(requested, mss_bands)
        # NDVI (NIR, Red) and GreenRed (Green, Red) and NDWI (Green, NIR) can be computed
        assert "NDVI" in computable
        assert "GreenRed" in computable
        assert "NDWI" in computable
        # EVI requires Blue, NDMI requires SWIR1, NBR requires SWIR2 -> must be skipped
        assert "EVI" not in computable
        assert "NDMI" not in computable
        assert "NBR" not in computable


class TestGEECompositeRegistry:
    """Tests for the session-scoped composite registry."""

    def setup_method(self):
        clear_composites()

    def teardown_method(self):
        clear_composites()

    def test_register_and_retrieve_composite(self):
        mock_img = MagicMock()
        mock_region = MagicMock()
        cid = register_composite(
            image=mock_img,
            region=mock_region,
            scale=10,
            bands=["Blue", "Green", "Red", "NIR"],
            sensor="sentinel2_sr",
            year=2023,
            metadata={"method": "median"},
        )
        assert cid == "composite_1"

        entry = get_composite(cid)
        assert entry["scale"] == 10
        assert entry["sensor"] == "sentinel2_sr"
        assert entry["year"] == 2023
        assert entry["bands"] == ["Blue", "Green", "Red", "NIR"]

    def test_update_and_list_composites(self):
        mock_img = MagicMock()
        cid = register_composite(
            image=mock_img,
            region=MagicMock(),
            scale=30,
            bands=["Red", "NIR"],
            sensor="landsat8_sr",
            year=2021,
        )
        # Update with new index band
        update_composite(cid, mock_img, ["Red", "NIR", "NDVI"])

        summaries = list_composites()
        assert len(summaries) == 1
        assert summaries[0]["composite_id"] == cid
        assert "NDVI" in summaries[0]["bands"]
        assert summaries[0]["band_count"] == 3

    def test_unknown_composite_raises_error(self):
        with pytest.raises(ValueError, match="Unknown composite_id"):
            get_composite("composite_999")


class TestGEECompositeBuilderHelpers:
    """Tests for date calculations and seasonal window wrapping."""

    def test_standard_season_window(self):
        start, end = build_date_range(2022, 6, 8)
        assert start == "2022-06-01"
        assert end == "2022-08-31"

    def test_cross_year_season_window(self):
        # Window starting in November and ending in February wraps into next year
        start, end = build_date_range(2022, 11, 2)
        assert start == "2022-11-01"
        assert end == "2023-02-28"

    def test_year_offset_fallback(self):
        start, end = build_date_range(2020, 1, 12, offset_yr=-1)
        assert start == "2019-01-01"
        assert end == "2019-12-31"


class TestGEEFactualityAndPipeline:
    """Tests for scientific factuality auditing and Mermaid graph generation."""

    def test_audit_mss_toa_assumption(self):
        findings = audit_factuality_assumptions({
            "sensor": "landsat_mss_l1",
            "year": 1976,
            "reducer": "median",
            "indices": ["NDVI"],
        })
        titles = [f["title"] for f in findings]
        assert any("Top-of-Atmosphere" in t for t in titles)

    def test_audit_cross_sensor_assumption(self):
        findings = audit_factuality_assumptions({
            "sensor": "sentinel2_sr",
            "year": 2022,
            "reducer": "median",
            "indices": ["NDVI", "EVI"],
        })
        titles = [f["title"] for f in findings]
        assert any("Cross-Sensor Spectral Bandpass" in t for t in titles)

    def test_audit_water_shadow_confusion(self):
        findings = audit_factuality_assumptions({
            "sensor": "sentinel2_sr",
            "year": 2023,
            "reducer": "median",
            "indices": ["NDWI"],
        })
        titles = [f["title"] for f in findings]
        assert any("Cloud Shadow Spectral Confusion" in t for t in titles)

    def test_mermaid_pipeline_generation(self):
        mermaid = generate_mermaid_pipeline({
            "sensor": "Sentinel-2 MSI",
            "year": 2023,
            "reducer": "greenest",
            "indices": ["NDVI", "NDWI"],
            "outputs": ["Zonal Stats", "Thumbnail"],
        })
        assert "flowchart TD" in mermaid
        assert "Sentinel-2 MSI (2023)" in mermaid
        assert "Greenest" in mermaid
        assert "NDVI, NDWI" in mermaid


class TestGEECatalogSearch:
    """Tests for cached dataset catalog search and curated fallbacks."""

    def test_catalog_search_finds_sentinel2(self):
        results = search_catalog("sentinel-2 surface reflectance", limit=5)
        assert len(results) > 0
        ids = [r["id"] for r in results]
        assert any("S2_SR" in rid or "COPERNICUS" in rid for rid in ids)

    def test_catalog_search_finds_worldcover(self):
        results = search_catalog("worldcover land cover", limit=5)
        assert len(results) > 0
        ids = [r["id"] for r in results]
        assert any("WorldCover" in rid for rid in ids)

    def test_get_dataset_entry_exact(self):
        entry = get_dataset_entry("COPERNICUS/DEM/GLO30")
        assert entry is not None
        assert "Copernicus" in entry["title"] or "DSM" in entry["title"]

    def test_empty_query_returns_empty_list(self):
        assert search_catalog("") == []


class TestGEERegistryAndToolScoping:
    """Tests for eo-mcp tool registry integration and profiles."""

    def test_earth_engine_category_registered(self):
        assert "earth_engine" in TOOL_CATEGORIES
        cat = TOOL_CATEGORIES["earth_engine"]
        assert "gee_init" in cat["tools"]
        assert "gee_build_composite" in cat["tools"]
        assert "gee_compute_indices" in cat["tools"]
        assert "gee_zonal_stats" in cat["tools"]
        assert "gee_threshold_area" in cat["tools"]
        assert "gee_thumbnail" in cat["tools"]
        assert "gee_audit_factuality" in cat["tools"]

    def test_earth_engine_profiles(self):
        assert "earth_engine" in PROFILES
        assert "gee" in PROFILES
        assert "earth_engine" in PROFILES["earth_engine"]
        assert "earth_engine" in PROFILES["all"]

    def test_allowed_tools_under_gee_profile(self):
        allowed = get_allowed_tools("gee")
        assert "gee_build_composite" in allowed
        assert "gee_compute_indices" in allowed
        assert "stac_search" in allowed  # core category included in gee profile


class TestGEESessionDiagnostics:
    """Tests for soft-import handling and session status diagnostics."""

    def test_get_ee_status_structure(self):
        status = get_ee_status()
        assert "installed" in status
        assert "initialized" in status
        assert "active_project" in status


class TestGEEServerTools:
    """Tests for server.py GEE tool wrappers."""

    def test_server_catalog_search_tool(self):
        from eo_mcp.server import gee_catalog_search

        raw_res = gee_catalog_search(query="sentinel", limit=3)
        res = json.loads(raw_res)
        assert res["query"] == "sentinel"
        assert res["count"] > 0
        assert len(res["datasets"]) <= 3

    def test_server_init_unauthenticated_returns_help(self):
        from eo_mcp.server import gee_init

        raw_res = gee_init(project_id="nonexistent-project-xyz-123")
        res = json.loads(raw_res)
        # Should fail cleanly with error and helpful instructions
        assert res["status"] == "error"
        assert "help" in res

    def test_server_audit_factuality_tool(self):
        from eo_mcp.server import gee_audit_factuality

        raw_res = gee_audit_factuality(
            sensor="landsat_mss_l1",
            year=1978,
            reducer="median",
            indices=["NDVI", "NDWI"],
        )
        res = json.loads(raw_res)
        assert res["status"] == "success"
        assert res["findings_count"] > 0
        assert "mermaid_pipeline_diagram" in res
        assert "flowchart TD" in res["mermaid_pipeline_diagram"]
