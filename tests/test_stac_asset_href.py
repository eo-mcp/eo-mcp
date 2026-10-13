"""Tests for STAC asset href resolution used by calculate_spectral_index."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from eo_mcp.providers.stac import resolve_stac_asset_href


def _asset(href: str) -> SimpleNamespace:
    return SimpleNamespace(href=href)


def test_resolve_stac_asset_href_prefers_first_match():
    item = SimpleNamespace(
        assets={
            "nir": _asset("https://example.com/nir.tif"),
            "B08": _asset("https://example.com/B08.tif"),
        }
    )
    assert resolve_stac_asset_href(item, "nir", "B08") == "https://example.com/nir.tif"


def test_resolve_stac_asset_href_falls_back_across_keys():
    item = SimpleNamespace(
        assets={
            "nir08": _asset("https://example.com/nir08.tif"),
            "red": _asset("https://example.com/red.tif"),
        }
    )
    assert resolve_stac_asset_href(item, "nir", "nir08", "B08") == "https://example.com/nir08.tif"


def test_resolve_stac_asset_href_missing_raises_with_available_keys():
    item = SimpleNamespace(assets={"visual": _asset("https://example.com/visual.tif")})
    with pytest.raises(KeyError) as exc:
        resolve_stac_asset_href(item, "nir", "B08")
    assert "nir" in str(exc.value)
    assert "visual" in str(exc.value)


def test_calculate_spectral_index_uses_stac_hrefs_not_invented_s3_keys():
    """Regression: never build sentinel-cogs.s3.../{scene_id}/B08.tif."""
    from eo_mcp.core.models import STACSearchResultItem
    from eo_mcp import server as server_mod

    scene = STACSearchResultItem(
        id="S2C_43QDU_20251214_0_L2A",
        collection="sentinel-2-l2a",
        datetime="2025-12-14T05:44:30Z",
        cloud_cover=0.0,
        bbox=[74.7, 17.0, 74.8, 17.1],
        assets=["nir", "red", "green", "blue"],
        thumbnail_url=None,
        platform="sentinel-2c",
        bands=["B02", "B03", "B04", "B08"],
    )

    item = MagicMock()
    item.assets = {
        "nir": _asset(
            "https://sentinel-cogs.s3.us-west-2.amazonaws.com/"
            "sentinel-s2-l2a-cogs/43/Q/DU/2025/12/S2C_43QDU_20251214_0_L2A/B08.tif"
        ),
        "red": _asset(
            "https://sentinel-cogs.s3.us-west-2.amazonaws.com/"
            "sentinel-s2-l2a-cogs/43/Q/DU/2025/12/S2C_43QDU_20251214_0_L2A/B04.tif"
        ),
    }

    client = MagicMock()
    client.get_collection.return_value.get_item.return_value = item

    streamed_urls = []

    def fake_stream(url, bbox, resampling_factor=0.5):
        streamed_urls.append(url)
        import numpy as np

        return np.ones((4, 4), dtype=np.float32) * (0.4 if "B08" in url or "nir" in url else 0.1), {}

    fake_vis = {
        "preview_path": "/tmp/x.png",
        "preview_uri": "file:///tmp/x.png",
        "map_path": "/tmp/x.html",
        "map_uri": "file:///tmp/x.html",
        "geotiff_path": "/tmp/x.tif",
        "geotiff_uri": "file:///tmp/x.tif",
        "visual_artifacts": [],
    }

    with patch.object(server_mod, "search_stac_catalog", return_value=[scene]), \
         patch.object(server_mod, "get_stac_client", return_value=client), \
         patch.object(server_mod, "stream_cog_window", side_effect=fake_stream), \
         patch.object(server_mod, "export_visual_artifacts", return_value=fake_vis):
        payload = server_mod.calculate_spectral_index(
            collection="sentinel-2-l2a",
            index="NDVI",
            bbox=[74.6997, 16.9761, 74.8197, 17.0961],
            datetime_range="2025-12-14",
        )

    assert '"error"' not in payload
    # Broken pattern was bucket-root /{scene_id}/Bxx.tif (no MGRS prefix).
    bad_prefix = "amazonaws.com/S2C_43QDU_20251214_0_L2A/"
    assert all(bad_prefix not in u for u in streamed_urls), streamed_urls
    assert all("sentinel-s2-l2a-cogs/43/Q/DU/2025/12/" in u for u in streamed_urls), streamed_urls
    assert len(streamed_urls) == 2
    assert '"index": "NDVI"' in payload or '"index":"NDVI"' in payload
