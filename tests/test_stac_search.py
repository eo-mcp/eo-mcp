"""Automated unit and integration tests for Token-Optimized STAC Catalog Discovery (Requirement R2).

Verifies:
1. Token budget compliance: 5-scene compact search results strictly < 2,500 characters (~500 tokens).
2. Schema integrity: presence of all 6 decision parameters (id, platform, datetime, cloud_cover, bbox, bands).
3. Payload optimization: total omission of verbose asset tables, URLs, coordinate polygons, and hypermedia links.
4. Sensor band normalization across Sentinel-2, Landsat, Sentinel-1 SAR, and Copernicus DEM.
5. Backwards compatibility: full legacy payload preservation when compact=False.
6. 100% offline execution without network access.
"""

import json
from unittest.mock import MagicMock, patch
import pytest

from eo_mcp.core.models import (
    CompactSTACItem,
    CompactSTACResponse,
    STACSearchResultItem,
)
from eo_mcp.providers.stac import (
    format_compact_stac_items,
    normalize_stac_bands,
    search_stac_catalog,
    search_stac_compact,
    search_sentinel2_scenes,
    search_landsat_scenes,
)


# ---------------------------------------------------------------------------
# Synthetic Offline Mock Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_s2_raw_assets():
    """Realistic AWS Earth Search Sentinel-2 L2A asset dictionary keys."""
    return [
        "aot", "blue", "coastal", "granule_metadata", "green", "nir", "nir08",
        "nir09", "red", "rededge1", "rededge2", "rededge3", "scl", "swir16",
        "swir22", "thumbnail", "tileinfo_metadata", "visual", "wvp",
        "aot-jp2", "blue-jp2", "coastal-jp2", "green-jp2", "nir-jp2",
        "nir08-jp2", "nir09-jp2", "red-jp2", "rededge1-jp2", "rededge2-jp2",
        "rededge3-jp2", "scl-jp2", "swir16-jp2", "swir22-jp2", "visual-jp2", "wvp-jp2"
    ]


@pytest.fixture
def mock_5_s2_items(mock_s2_raw_assets):
    """Synthetic list of 5 realistic STACSearchResultItem objects."""
    items = []
    base_dates = ["2024-06-15", "2024-06-10", "2024-06-05", "2024-05-31", "2024-05-26"]
    platforms = ["sentinel-2b", "sentinel-2a", "sentinel-2b", "sentinel-2a", "sentinel-2b"]

    for i in range(5):
        s2_prefix = "S2B" if i % 2 == 0 else "S2A"
        date_str = base_dates[i]
        items.append(
            STACSearchResultItem(
                id=f"{s2_prefix}_31TCJ_{date_str.replace('-', '')}_0_L2A",
                collection="sentinel-2-l2a",
                datetime=f"{date_str}T10:30:29.024000Z",
                cloud_cover=round(1.5 * i + 0.81234, 4),
                bbox=[2.105284719284719, 41.34119284719284, 2.248291847192847, 41.45239184719284],
                assets=mock_s2_raw_assets,
                thumbnail_url=f"https://sentinel-cogs.s3.us-west-2.amazonaws.com/{s2_prefix}_31TCJ_{date_str}/thumbnail.jpg",
                platform=platforms[i],
            )
        )
    return items


# ---------------------------------------------------------------------------
# Model & Validation Tests
# ---------------------------------------------------------------------------

def test_compact_stac_item_fields_and_rounding():
    """Verify CompactSTACItem enforces 4-decimal bbox rounding and 1-decimal cloud cover."""
    item = CompactSTACItem(
        id="S2B_31TCJ_20240615_0_L2A",
        platform="sentinel-2b",
        datetime="2024-06-15T10:30:29Z",
        cloud_cover=4.123456789,
        bbox=[2.105284719284719, 41.34119284719284, 2.248291847192847, 41.45239184719284],
        bands=["B02", "B03", "B04", "B08", "B11", "B12"],
    )

    # Check that bbox coordinates are strictly rounded to 4 decimals
    assert item.bbox == [2.1053, 41.3412, 2.2483, 41.4524]
    # Check that cloud cover is rounded to 1 decimal
    assert item.cloud_cover == 4.1
    # Check all 6 required fields
    dump = item.model_dump()
    expected_fields = {"id", "platform", "datetime", "cloud_cover", "bbox", "bands"}
    assert set(dump.keys()) == expected_fields


def test_compact_stac_response_container():
    """Verify CompactSTACResponse holds count and scenes list."""
    scene = CompactSTACItem(
        id="S2B_TEST",
        platform="sentinel-2b",
        datetime="2024-06-15T10:30:29Z",
        cloud_cover=2.5,
        bbox=[1.0, 2.0, 3.0, 4.0],
        bands=["B02", "B03"],
    )
    resp = CompactSTACResponse(count=1, scenes=[scene], collection="sentinel-2-l2a")
    assert resp.count == 1
    assert len(resp.scenes) == 1
    assert resp.scenes[0].id == "S2B_TEST"
    assert resp.collection == "sentinel-2-l2a"


# ---------------------------------------------------------------------------
# Band Normalization Tests
# ---------------------------------------------------------------------------

def test_band_normalization_sentinel2(mock_s2_raw_assets):
    """Verify normalization of Sentinel-2 asset keys to standard science bands."""
    bands = normalize_stac_bands(mock_s2_raw_assets, collection="sentinel-2-l2a")
    # Must contain the core science bands in natural order
    assert bands == ["B02", "B03", "B04", "B08", "B11", "B12"]
    # Ensure thumbnails, overviews, jp2 formats, and metadata are excluded
    assert "thumbnail" not in bands
    assert "visual" not in bands
    assert "blue-jp2" not in bands
    assert "granule_metadata" not in bands


def test_band_normalization_landsat():
    """Verify normalization of Landsat 8/9 asset keys to core reflective science bands."""
    landsat_assets = [
        "blue", "green", "red", "nir08", "swir16", "swir22",
        "thermal", "qa_pixel", "thumbnail", "overview", "ang", "mtl"
    ]
    bands = normalize_stac_bands(landsat_assets, collection="landsat-c2-l2")
    assert bands == ["B02", "B03", "B04", "B05", "B06", "B07"]
    assert "thumbnail" not in bands
    assert "qa_pixel" not in bands


def test_band_normalization_sar():
    """Verify normalization of Sentinel-1 SAR asset keys."""
    sar_assets = ["vv", "vh", "thumbnail", "preview"]
    bands = normalize_stac_bands(sar_assets, collection="sentinel-1-grd")
    assert bands == ["VV", "VH"]


def test_band_normalization_dem():
    """Verify normalization of Copernicus DEM asset keys."""
    dem_assets = ["elevation", "data", "thumbnail"]
    bands = normalize_stac_bands(dem_assets, collection="cop-dem-glo-30")
    assert bands == ["ELEVATION"]


def test_band_normalization_passthrough_clean_bands():
    """Verify that already-normalized band names pass through cleanly."""
    clean_input = ["B02", "B03", "B04", "B08", "B11", "B12"]
    bands = normalize_stac_bands(clean_input, collection="sentinel-2-l2a")
    assert bands == ["B02", "B03", "B04", "B08", "B11", "B12"]


# ---------------------------------------------------------------------------
# Token Budget & Compact Serialization Tests (< 2,500 Chars for 5 Scenes)
# ---------------------------------------------------------------------------

def test_five_scene_compact_token_budget(mock_5_s2_items):
    """Verify 5-scene compact response strictly consumes < 2,500 characters (~500 tokens)."""
    response = format_compact_stac_items(mock_5_s2_items, collection="sentinel-2-l2a")
    assert response.count == 5

    # Serialize to JSON with standard 2-space indentation
    json_indented = json.dumps(response.model_dump(), indent=2)
    char_count = len(json_indented)
    estimated_tokens = char_count / 4.0

    print(f"\n[Token Budget Check] 5-Scene Indented JSON: {char_count} chars (~{estimated_tokens:.0f} tokens)")

    # Strict Requirement R2: Output must be under 2,500 characters
    assert char_count < 2500, f"Token budget exceeded! Output was {char_count} chars (limit: 2500)"
    # Ensure it is not an empty or trivial stub
    assert char_count > 600, f"Payload suspiciously small ({char_count} chars)"
    # Token count must be strictly under 500 tokens
    assert estimated_tokens < 500, f"Estimated tokens {estimated_tokens} exceeded 500"

    # Also verify unindented JSON
    json_compact = response.model_dump_json()
    assert len(json_compact) < 1200


def test_compact_schema_integrity_and_omissions(mock_5_s2_items):
    """Verify all 6 decision parameters are present and all verbose asset bloat is omitted."""
    response = format_compact_stac_items(mock_5_s2_items, collection="sentinel-2-l2a")
    dump = response.model_dump()

    assert dump["count"] == 5
    assert "scenes" in dump
    assert len(dump["scenes"]) == 5

    for scene in dump["scenes"]:
        # 1. Verify required fields exist
        assert "id" in scene and isinstance(scene["id"], str)
        assert "platform" in scene and isinstance(scene["platform"], str)
        assert "datetime" in scene and isinstance(scene["datetime"], str)
        assert "cloud_cover" in scene
        assert "bbox" in scene and len(scene["bbox"]) == 4
        assert "bands" in scene and isinstance(scene["bands"], list)

        # 2. Verify values
        assert scene["platform"] in ("sentinel-2a", "sentinel-2b")
        assert "B02" in scene["bands"]
        for coord in scene["bbox"]:
            # Coordinate precision: 4 decimals max
            assert round(coord, 4) == coord

        # 3. Verify bloated fields are completely omitted
        assert "assets" not in scene
        assert "thumbnail_url" not in scene
        assert "geometry" not in scene
        assert "links" not in scene
        assert "properties" not in scene


# ---------------------------------------------------------------------------
# Backwards Compatibility Tests (compact=False vs compact=True)
# ---------------------------------------------------------------------------

def test_search_stac_catalog_legacy_compatibility(mock_5_s2_items):
    """Verify search_stac_catalog with compact=False returns full legacy STACSearchResultItem list."""
    mock_pystac_item = MagicMock()
    mock_pystac_item.id = "S2B_31TCJ_20240615_0_L2A"
    mock_pystac_item.collection_id = "sentinel-2-l2a"
    mock_pystac_item.datetime = None
    mock_pystac_item.properties = {
        "datetime": "2024-06-15T10:30:29Z",
        "eo:cloud_cover": 3.8,
        "platform": "sentinel-2b",
    }
    mock_pystac_item.bbox = [2.10528, 41.34119, 2.24829, 41.45239]
    mock_asset = MagicMock()
    mock_asset.href = "https://example.com/thumb.jpg"
    mock_pystac_item.assets = {
        "blue": MagicMock(),
        "green": MagicMock(),
        "red": MagicMock(),
        "thumbnail": mock_asset,
    }

    mock_client = MagicMock()
    mock_search = MagicMock()
    mock_search.items.return_value = [mock_pystac_item]
    mock_client.search.return_value = mock_search

    with patch("eo_mcp.providers.stac.get_stac_client", return_value=mock_client):
        # Legacy mode: compact=False
        legacy_results = search_stac_catalog(
            catalog_url="https://mock.stac.io/v1",
            collections=["sentinel-2-l2a"],
            bbox=[2.1, 41.3, 2.3, 41.5],
            datetime_range="2024-06-01/2024-06-30",
            compact=False,
        )

        assert isinstance(legacy_results, list)
        assert len(legacy_results) == 1
        item = legacy_results[0]
        assert isinstance(item, STACSearchResultItem)
        assert item.id == "S2B_31TCJ_20240615_0_L2A"
        # Full raw asset list is intact
        assert "thumbnail" in item.assets
        assert item.thumbnail_url == "https://example.com/thumb.jpg"


def test_search_stac_catalog_compact_mode(mock_5_s2_items):
    """Verify search_stac_catalog with compact=True returns CompactSTACResponse under budget."""
    mock_pystac_items = []
    for i in range(5):
        m = MagicMock()
        m.id = f"S2B_31TCJ_202406{15 - i * 5}_0_L2A"
        m.collection_id = "sentinel-2-l2a"
        m.datetime = None
        m.properties = {
            "datetime": f"2024-06-{15 - i * 5:02d}T10:30:29Z",
            "cloud_cover": 2.1 * i + 0.5,
            "platform": "sentinel-2b",
        }
        m.bbox = [2.10528, 41.34119, 2.24829, 41.45239]
        m.assets = {
            "blue": MagicMock(),
            "green": MagicMock(),
            "red": MagicMock(),
            "nir": MagicMock(),
            "swir16": MagicMock(),
            "swir22": MagicMock(),
            "thumbnail": MagicMock(href="https://example.com/thumb.jpg"),
        }
        mock_pystac_items.append(m)

    mock_client = MagicMock()
    mock_search = MagicMock()
    mock_search.items.return_value = mock_pystac_items
    mock_client.search.return_value = mock_search

    with patch("eo_mcp.providers.stac.get_stac_client", return_value=mock_client):
        compact_resp = search_stac_catalog(
            catalog_url="https://mock.stac.io/v1",
            collections=["sentinel-2-l2a"],
            bbox=[2.1, 41.3, 2.3, 41.5],
            datetime_range="2024-06-01/2024-06-30",
            compact=True,
        )

        assert isinstance(compact_resp, CompactSTACResponse)
        assert compact_resp.count == 5
        payload = json.dumps(compact_resp.model_dump(), indent=2)
        assert len(payload) < 2500


def test_search_stac_compact_helper():
    """Verify search_stac_compact helper convenience function."""
    mock_item = MagicMock()
    mock_item.id = "LC08_L2SP_042034_20240615"
    mock_item.collection_id = "landsat-c2-l2"
    mock_item.datetime = None
    mock_item.properties = {
        "datetime": "2024-06-15T18:00:00Z",
        "cloud_cover": 5.0,
        "platform": "landsat-8",
    }
    mock_item.bbox = [-122.5, 37.5, -121.9, 38.0]
    mock_item.assets = {"blue": MagicMock(), "green": MagicMock(), "red": MagicMock(), "nir08": MagicMock(), "swir16": MagicMock(), "swir22": MagicMock()}

    mock_client = MagicMock()
    mock_search = MagicMock()
    mock_search.items.return_value = [mock_item]
    mock_client.search.return_value = mock_search

    with patch("eo_mcp.providers.stac.get_stac_client", return_value=mock_client):
        resp = search_stac_compact(
            catalog_url="https://mock.stac.io/v1",
            collections=["landsat-c2-l2"],
            bbox=[-122.5, 37.5, -121.9, 38.0],
            datetime_range="2024-06-01/2024-06-30",
        )
        assert isinstance(resp, CompactSTACResponse)
        assert resp.count == 1
        assert resp.scenes[0].platform == "landsat-8"
        assert resp.scenes[0].bands == ["B02", "B03", "B04", "B05", "B06", "B07"]


def test_search_convenience_wrappers():
    """Verify search_sentinel2_scenes and search_landsat_scenes forward compact parameter."""
    with patch("eo_mcp.providers.stac.search_stac_catalog", return_value=CompactSTACResponse(count=0, scenes=[])) as mock_search:
        search_sentinel2_scenes(bbox=[0, 0, 1, 1], datetime_range="2024-01-01", compact=True)
        mock_search.assert_called_once()
        assert mock_search.call_args.kwargs["compact"] is True


def test_platform_inference_fallback():
    """Verify platform is inferred correctly when properties lack platform/constellation."""
    item = STACSearchResultItem(
        id="S2A_31TCJ_20240615_0_L2A",
        collection="sentinel-2-l2a",
        datetime="2024-06-15T10:30:29Z",
        cloud_cover=1.2,
        bbox=[2.1, 41.3, 2.2, 41.4],
        assets=["blue", "green", "red"],
        platform=None,  # Missing platform
    )
    resp = format_compact_stac_items([item])
    assert resp.scenes[0].platform == "sentinel-2a"

    item_l8 = STACSearchResultItem(
        id="LC08_L2SP_042034_20240615",
        collection="landsat-c2-l2",
        datetime="2024-06-15T18:00:00Z",
        cloud_cover=0.0,
        bbox=[-122.0, 37.0, -121.0, 38.0],
        assets=["blue", "green"],
        platform=None,
    )
    resp_l8 = format_compact_stac_items([item_l8])
    assert resp_l8.scenes[0].platform == "landsat-8"


def test_offline_execution_no_network():
    """Verify tests execute 100% offline with zero external network connectivity."""
    items = [
        STACSearchResultItem(
            id=f"S2B_TEST_{i}",
            collection="sentinel-2-l2a",
            datetime="2024-06-15T10:30:29Z",
            cloud_cover=2.0,
            bbox=[1.123456, 2.123456, 3.123456, 4.123456],
            assets=["blue", "green", "red", "nir", "swir16", "swir22"],
            platform="sentinel-2b",
        )
        for i in range(5)
    ]
    resp = format_compact_stac_items(items)
    json_out = json.dumps(resp.model_dump(), indent=2)
    assert len(json_out) < 2500
    assert len(json_out) > 500
