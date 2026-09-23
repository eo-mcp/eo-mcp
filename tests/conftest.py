"""Shared pytest fixtures for 100% offline, deterministic testing of eo-mcp.

Provides:
- Synthetic multi-band datacubes for wildfire, flood, and vegetation change.
- Realistic 5-scene STAC mock responses for Sentinel-2, Landsat, and Copernicus DEM.
- Offline monkeypatch fixtures for STAC searches, raster COG streaming, Nominatim geocoding,
  and NASA FIRMS hotspots to guarantee sub-second execution without network access.
- Isolated output directory fixtures to prevent disk pollution.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from unittest.mock import MagicMock
import numpy as np
import pytest

from eo_mcp.core.models import (
    STACSearchResultItem,
    CompactSTACItem,
    CompactSTACResponse,
    BoundingBox,
)


@pytest.fixture
def synthetic_wildfire_datacube() -> Dict[str, Any]:
    """
    Synthetic multi-band datacube (40x50 pixels) with known burn scar:
    - Pre-fire: Uniform healthy canopy (NIR=0.60, SWIR2=0.10 -> NBR=0.714)
    - Post-fire: Central scar at [10:30, 15:35] (NIR=0.12, SWIR2=0.50 -> NBR=-0.613)
    - Expected dNBR in scar: 0.714 - (-0.613) = 1.327 (High Severity per USGS, dNBR >= 0.660)
    - Expected dNBR outside scar: 0.0 (Unburned, -0.100 <= dNBR < 0.100)
    - Dimensions: 40 rows x 50 columns = 2000 total pixels
    - Scar size: 20 rows x 20 columns = 400 burned pixels (20.0% of AOI)
    - Pixel resolution: 10.0m -> 0.01 ha per pixel -> 4.00 ha burned (9.884 acres)
    """
    rows, cols = 40, 50
    pre_nir = np.full((rows, cols), 0.60, dtype=np.float32)
    pre_swir2 = np.full((rows, cols), 0.10, dtype=np.float32)

    post_nir = np.full((rows, cols), 0.60, dtype=np.float32)
    post_swir2 = np.full((rows, cols), 0.10, dtype=np.float32)

    scar_slice = (slice(10, 30), slice(15, 35))
    post_nir[scar_slice] = 0.12
    post_swir2[scar_slice] = 0.50

    return {
        "rows": rows,
        "cols": cols,
        "pre_nir": pre_nir,
        "pre_swir2": pre_swir2,
        "post_nir": post_nir,
        "post_swir2": post_swir2,
        "scar_slice": scar_slice,
        "scar_pixel_count": 400,
        "total_pixels": 2000,
        "pixel_size_m": 10.0,
        "expected_burned_ha": 4.00,
        "expected_burned_acres": 4.00 * 2.4710538,
        "expected_burned_pct": 20.0,
        "expected_scar_dnbr": 1.327,
        "expected_unburned_dnbr": 0.0,
        "bbox": [23.65, 37.95, 23.85, 38.15],
    }


@pytest.fixture
def synthetic_flood_datacube() -> Dict[str, Any]:
    """
    Synthetic flood scenario with DEM slope masking (40x50 pixels):
    - Pre-event:
      - Permanent river at columns 20-23 (Green=0.40, SWIR1=0.05 -> MNDWI=+0.778 > 0.0)
      - Dry terrain elsewhere (Green=0.10, SWIR1=0.25 -> MNDWI=-0.429 < 0.0)
    - Post-event:
      - Permanent river (MNDWI=+0.778)
      - Inundated valley: rows 15-34, cols 10-39 (Green=0.45, SWIR1=0.08 -> MNDWI=+0.698 > 0.0)
      - Steep mountain shadow artifact: rows 2-7, cols 2-7 (Green=0.45, SWIR1=0.08 -> MNDWI=+0.698)
    - Digital Elevation Model (Copernicus DEM GLO-30 simulation):
      - Valley & plain: rows 10-39, cols 0-49: elevation 2.0m (flat plain, slope < 1.0 deg)
      - Steep mountain ridge: rows 0-9, cols 0-49: elevation gradient 150m down to 10m (slope > 20 deg)
    - Expected Slope Masking:
      - Shadow false-positive pixels in rows 2-7 (slope > 5.0 deg) are eliminated from inundation.
      - Permanent river pixels are separated from newly flooded land.
      - Net flooded land area strictly isolated to the flat valley floor.
    """
    rows, cols = 40, 50

    pre_green = np.full((rows, cols), 0.10, dtype=np.float32)
    pre_swir1 = np.full((rows, cols), 0.25, dtype=np.float32)
    # Permanent river (columns 20 to 23 inclusive)
    pre_green[:, 20:24] = 0.40
    pre_swir1[:, 20:24] = 0.05

    post_green = pre_green.copy()
    post_swir1 = pre_swir1.copy()
    # Flooded valley (rows 15 to 34, cols 10 to 39)
    valley_slice = (slice(15, 35), slice(10, 40))
    post_green[valley_slice] = 0.45
    post_swir1[valley_slice] = 0.08

    # Steep mountain shadow artifact (rows 2 to 7, cols 2 to 7)
    shadow_slice = (slice(2, 8), slice(2, 8))
    post_green[shadow_slice] = 0.45
    post_swir1[shadow_slice] = 0.08

    # DEM elevation grid
    dem = np.full((rows, cols), 2.0, dtype=np.float32)
    # Mountain ridge in northern rows (0 to 9)
    for r in range(10):
        dem[r, :] = 150.0 - (r * 14.0)  # 150m down to 24m over 10 cells -> steep slope > 20 deg

    return {
        "rows": rows,
        "cols": cols,
        "pre_green": pre_green,
        "pre_swir1": pre_swir1,
        "post_green": post_green,
        "post_swir1": post_swir1,
        "dem": dem,
        "cellsize_m": 30.0,
        "slope_threshold_deg": 5.0,
        "valley_slice": valley_slice,
        "shadow_slice": shadow_slice,
        "river_cols": (20, 24),
        "bbox": [21.80, 39.20, 22.80, 39.80],
    }


@pytest.fixture
def synthetic_vegetation_datacube() -> Dict[str, Any]:
    """
    Synthetic dual-epoch vegetation change datacube (40x50 pixels):
    - Epoch 1 (Baseline): Uniform healthy canopy (NIR=0.55, Red=0.08 -> NDVI=0.746)
    - Epoch 2 (Monitoring):
      - Clearing/Deforestation in northwest block [5:20, 5:20]:
        NIR=0.15, Red=0.22 -> NDVI=-0.189, Delta NDVI = -0.935 (Severe Loss, Delta NDVI < -0.25)
        Loss pixels: 15 x 15 = 225 pixels
      - Regrowth/Greening in southeast block [25:35, 30:45]:
        NIR=0.70, Red=0.05 -> NDVI=0.867, Delta NDVI = +0.121 (Greening gain)
        Gain pixels: 10 x 15 = 150 pixels
      - Elsewhere: Stable canopy (NIR=0.55, Red=0.08 -> Delta NDVI=0.0)
    """
    rows, cols = 40, 50
    ep1_nir = np.full((rows, cols), 0.55, dtype=np.float32)
    ep1_red = np.full((rows, cols), 0.08, dtype=np.float32)

    ep2_nir = ep1_nir.copy()
    ep2_red = ep1_red.copy()

    # Clearing / Deforestation block
    loss_slice = (slice(5, 20), slice(5, 20))
    ep2_nir[loss_slice] = 0.15
    ep2_red[loss_slice] = 0.22

    # Regrowth / Greening block
    gain_slice = (slice(25, 35), slice(30, 45))
    ep2_nir[gain_slice] = 0.70
    ep2_red[gain_slice] = 0.05

    return {
        "rows": rows,
        "cols": cols,
        "ep1_nir": ep1_nir,
        "ep1_red": ep1_red,
        "ep2_nir": ep2_nir,
        "ep2_red": ep2_red,
        "loss_slice": loss_slice,
        "gain_slice": gain_slice,
        "loss_pixel_count": 225,
        "gain_pixel_count": 150,
        "pixel_size_m": 10.0,
        "expected_loss_ha": 2.25,
        "expected_loss_acres": 2.25 * 2.4710538,
        "expected_gain_ha": 1.50,
        "bbox": [-55.0, -3.5, -54.0, -2.5],
    }


@pytest.fixture
def mock_stac_scenes_5() -> List[STACSearchResultItem]:
    """Realistic 5-scene STAC Item fixture for token budget and discovery tests."""
    return [
        STACSearchResultItem(
            id="S2B_31TCJ_20240615_0_L2A",
            collection="sentinel-2-l2a",
            datetime="2024-06-15T10:30:29Z",
            cloud_cover=4.1234,
            bbox=[2.105284, 41.341192, 2.248291, 41.452384],
            assets=[
                "blue", "green", "red", "nir", "nir08", "swir16", "swir22",
                "scl", "visual", "thumbnail", "granule_metadata",
                "blue-jp2", "green-jp2", "red-jp2", "nir-jp2"
            ],
            thumbnail_url="https://sentinel-cogs.s3.us-west-2.amazonaws.com/S2B_31TCJ_20240615/thumbnail.jpg",
            platform="sentinel-2b",
            bands=["B02", "B03", "B04", "B08", "B11", "B12"],
        ),
        STACSearchResultItem(
            id="S2A_31TCJ_20240610_0_L2A",
            collection="sentinel-2-l2a",
            datetime="2024-06-10T10:35:01Z",
            cloud_cover=1.8492,
            bbox=[2.105284, 41.341192, 2.248291, 41.452384],
            assets=[
                "blue", "green", "red", "nir", "nir08", "swir16", "swir22",
                "scl", "visual", "thumbnail", "granule_metadata"
            ],
            thumbnail_url="https://sentinel-cogs.s3.us-west-2.amazonaws.com/S2A_31TCJ_20240610/thumbnail.jpg",
            platform="sentinel-2a",
            bands=["B02", "B03", "B04", "B08", "B11", "B12"],
        ),
        STACSearchResultItem(
            id="S2B_31TCJ_20240605_0_L2A",
            collection="sentinel-2-l2a",
            datetime="2024-06-05T10:30:19Z",
            cloud_cover=12.3811,
            bbox=[2.105284, 41.341192, 2.248291, 41.452384],
            assets=[
                "blue", "green", "red", "nir", "nir08", "swir16", "swir22",
                "scl", "visual", "thumbnail", "granule_metadata"
            ],
            thumbnail_url="https://sentinel-cogs.s3.us-west-2.amazonaws.com/S2B_31TCJ_20240605/thumbnail.jpg",
            platform="sentinel-2b",
            bands=["B02", "B03", "B04", "B08", "B11", "B12"],
        ),
        STACSearchResultItem(
            id="S2A_31TCJ_20240531_0_L2A",
            collection="sentinel-2-l2a",
            datetime="2024-05-31T10:34:51Z",
            cloud_cover=0.4912,
            bbox=[2.105284, 41.341192, 2.248291, 41.452384],
            assets=[
                "blue", "green", "red", "nir", "nir08", "swir16", "swir22",
                "scl", "visual", "thumbnail", "granule_metadata"
            ],
            thumbnail_url="https://sentinel-cogs.s3.us-west-2.amazonaws.com/S2A_31TCJ_20240531/thumbnail.jpg",
            platform="sentinel-2a",
            bands=["B02", "B03", "B04", "B08", "B11", "B12"],
        ),
        STACSearchResultItem(
            id="S2B_31TCJ_20240526_0_L2A",
            collection="sentinel-2-l2a",
            datetime="2024-05-26T10:30:21Z",
            cloud_cover=6.7203,
            bbox=[2.105284, 41.341192, 2.248291, 41.452384],
            assets=[
                "blue", "green", "red", "nir", "nir08", "swir16", "swir22",
                "scl", "visual", "thumbnail", "granule_metadata"
            ],
            thumbnail_url="https://sentinel-cogs.s3.us-west-2.amazonaws.com/S2B_31TCJ_20240526/thumbnail.jpg",
            platform="sentinel-2b",
            bands=["B02", "B03", "B04", "B08", "B11", "B12"],
        ),
    ]


@pytest.fixture
def mock_stac_search_engine(monkeypatch, mock_stac_scenes_5):
    """
    Mocks STAC catalog search and client abstraction functions to return
    instant synthetic STAC items with zero network calls across all modules.
    """
    def _mock_search_stac_catalog(catalog_url, collections, bbox, datetime_range, max_cloud_cover=None, limit=5):
        filtered = list(mock_stac_scenes_5)
        if max_cloud_cover is not None:
            filtered = [s for s in filtered if s.cloud_cover is not None and s.cloud_cover <= max_cloud_cover]
        return filtered[:limit]

    for mod in ["eo_mcp.providers.stac", "eo_mcp.server", "eo_mcp.workflows"]:
        try:
            monkeypatch.setattr(f"{mod}.search_stac_catalog", _mock_search_stac_catalog)
        except (AttributeError, KeyError):
            pass

    monkeypatch.setattr("eo_mcp.providers.stac.search_sentinel2_scenes", lambda bbox, datetime_range, max_cloud_cover=20.0, limit=5: _mock_search_stac_catalog("", ["sentinel-2-l2a"], bbox, datetime_range, max_cloud_cover, limit))
    monkeypatch.setattr("eo_mcp.providers.stac.search_landsat_scenes", lambda bbox, datetime_range, max_cloud_cover=20.0, limit=5: _mock_search_stac_catalog("", ["landsat-c2-l2"], bbox, datetime_range, max_cloud_cover, limit))

    return _mock_search_stac_catalog


@pytest.fixture
def mock_raster_streaming_engine(monkeypatch, synthetic_wildfire_datacube, synthetic_flood_datacube, synthetic_vegetation_datacube):
    """
    Mocks stream_cog_window to return synthetic arrays immediately without GDAL, VSI, or HTTP requests.
    """
    def _mock_stream(url, bbox, resampling_factor=1.0):
        url_str = str(url).lower()

        # Wildfire bands
        if "b08" in url_str or "nir" in url_str:
            if "pre" in url_str:
                arr = synthetic_wildfire_datacube["pre_nir"]
            else:
                arr = synthetic_wildfire_datacube["post_nir"]
        elif "b12" in url_str or "swir2" in url_str:
            if "pre" in url_str:
                arr = synthetic_wildfire_datacube["pre_swir2"]
            else:
                arr = synthetic_wildfire_datacube["post_swir2"]
        # Flood bands
        elif "b03" in url_str or "green" in url_str:
            arr = synthetic_flood_datacube["post_green"]
        elif "b11" in url_str or "swir1" in url_str:
            arr = synthetic_flood_datacube["post_swir1"]
        # Elevation DEM
        elif "dem" in url_str or "elev" in url_str:
            arr = synthetic_flood_datacube["dem"]
        # Vegetation / Red band
        elif "b04" in url_str or "red" in url_str:
            arr = synthetic_vegetation_datacube["ep2_red"]
        else:
            arr = np.full((40, 50), 0.20, dtype=np.float32)

        profile = {
            "driver": "GTiff",
            "height": arr.shape[0],
            "width": arr.shape[1],
            "count": 1,
            "dtype": "float32",
            "crs": "EPSG:4326"
        }
        return np.expand_dims(arr, 0), profile

    for mod in ["eo_mcp.core.raster", "eo_mcp.server", "eo_mcp.workflows"]:
        try:
            monkeypatch.setattr(f"{mod}.stream_cog_window", _mock_stream)
        except (AttributeError, KeyError):
            pass

    return _mock_stream


@pytest.fixture
def mock_offline_geocoding(monkeypatch):
    """
    Mocks Nominatim geocoding to resolve known test locations instantly offline across all modules.
    """
    LOCATIONS_DB = {
        "athens": {
            "display_name": "Athens, Attica, Greece",
            "lat": 37.9838,
            "lon": 23.7275,
            "bbox": [23.65, 37.95, 23.85, 38.15]
        },
        "thessaly": {
            "display_name": "Thessaly, Greece",
            "lat": 39.5,
            "lon": 22.3,
            "bbox": [21.80, 39.20, 22.80, 39.80]
        },
        "amazon": {
            "display_name": "Amazon Basin, Para, Brazil",
            "lat": -3.0,
            "lon": -54.5,
            "bbox": [-55.0, -3.5, -54.0, -2.5]
        },
        "valencia": {
            "display_name": "Valencia, Spain",
            "lat": 39.4699,
            "lon": -0.3763,
            "bbox": [-0.42, 39.42, -0.32, 39.50]
        }
    }

    def _mock_geocode(place_name: str):
        name_lower = place_name.lower()
        for key, entry in LOCATIONS_DB.items():
            if key in name_lower:
                return entry
        # Default fallback bbox
        return {
            "display_name": f"Mock Location ({place_name})",
            "lat": 0.0,
            "lon": 0.0,
            "bbox": [-1.0, -1.0, 1.0, 1.0]
        }

    for mod in ["eo_mcp.utils.geo", "eo_mcp.workflows"]:
        try:
            monkeypatch.setattr(f"{mod}.geocode_place_name", _mock_geocode)
        except (AttributeError, KeyError):
            pass

    return _mock_geocode


@pytest.fixture
def mock_firms_offline(monkeypatch):
    """Mocks NASA FIRMS hotspot retrieval to return synthetic fire hotspots across all modules."""
    def _mock_firms(bbox, days=2, source="VIIRS_NOAA20_NRT"):
        return [
            {
                "latitude": 38.05,
                "longitude": 23.75,
                "brightness": 345.2,
                "scan": 0.39,
                "track": 0.36,
                "acq_date": "2024-07-24",
                "acq_time": "1130",
                "satellite": "N",
                "instrument": "VIIRS",
                "confidence": "high",
                "version": "2.0NRT",
                "bright_t31": 298.5,
                "frp": 42.8,
                "daynight": "D",
                "fire_radiative_power_mw": 42.8
            },
            {
                "latitude": 38.07,
                "longitude": 23.77,
                "brightness": 360.1,
                "scan": 0.39,
                "track": 0.36,
                "acq_date": "2024-07-24",
                "acq_time": "1130",
                "satellite": "N",
                "instrument": "VIIRS",
                "confidence": "high",
                "version": "2.0NRT",
                "bright_t31": 305.2,
                "frp": 85.3,
                "daynight": "D",
                "fire_radiative_power_mw": 85.3
            }
        ]

    for mod in ["eo_mcp.core.wildfire", "eo_mcp.server", "eo_mcp.workflows"]:
        try:
            monkeypatch.setattr(f"{mod}.fetch_firms_hotspots", _mock_firms)
        except (AttributeError, KeyError):
            pass

    return _mock_firms


@pytest.fixture
def test_output_dir(tmp_path, monkeypatch) -> Path:
    """
    Creates an isolated temporary output directory for visual artifacts
    and sets the EO_OUTPUT_DIR environment variable to point to it.
    """
    out_dir = tmp_path / "eo_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("EO_OUTPUT_DIR", str(out_dir))
    return out_dir


@pytest.fixture
def offline_environment(mock_stac_search_engine, mock_raster_streaming_engine, mock_offline_geocoding, mock_firms_offline, test_output_dir):
    """Composite fixture enabling complete offline deterministic execution across all services."""
    return {
        "output_dir": test_output_dir,
        "stac_search": mock_stac_search_engine,
        "raster_stream": mock_raster_streaming_engine,
        "geocode": mock_offline_geocoding,
        "firms": mock_firms_offline,
    }
