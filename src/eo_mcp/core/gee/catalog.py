"""Fast keyword search across 880+ Google Earth Engine public datasets.

Maintains a local file cache of the flat GEE dataset catalog index (mirrored from
samapriya/Earth-Engine-Datasets-List) to enable instant multi-term keyword search
without network crawling latency.
"""

from __future__ import annotations

import json
import logging
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CATALOG_URL = (
    "https://raw.githubusercontent.com/samapriya/Earth-Engine-Datasets-List/"
    "master/gee_catalog.json"
)
_CACHE_TTL_SECONDS = 7 * 24 * 3600  # Refresh index weekly


def _get_cache_path() -> Path:
    return Path(tempfile.gettempdir()) / "eo_mcp_gee_catalog.json"


# Curated high-priority fallback catalog if remote download fails while offline
_FALLBACK_CURATED_DATASETS: List[Dict[str, Any]] = [
    {
        "id": "COPERNICUS/S2_SR_HARMONIZED",
        "title": "Sentinel-2 MSI: MultiSpectral Instrument, Level-2A",
        "type": "image_collection",
        "start_date": "2017-03-28",
        "end_date": None,
        "provider": "European Union / ESA / Copernicus",
        "tags": ["copernicus", "esa", "eu", "msi", "reflectance", "sentinel", "sr"],
    },
    {
        "id": "LANDSAT/LC09/C02/T1_L2",
        "title": "USGS Landsat 9 Level 2, Collection 2, Tier 1",
        "type": "image_collection",
        "start_date": "2021-10-31",
        "end_date": None,
        "provider": "USGS",
        "tags": ["landsat", "oli", "tirs", "usgs", "reflectance", "sr", "c2"],
    },
    {
        "id": "LANDSAT/LC08/C02/T1_L2",
        "title": "USGS Landsat 8 Level 2, Collection 2, Tier 1",
        "type": "image_collection",
        "start_date": "2013-03-18",
        "end_date": None,
        "provider": "USGS",
        "tags": ["landsat", "oli", "tirs", "usgs", "reflectance", "sr", "c2"],
    },
    {
        "id": "LANDSAT/LT05/C02/T1_L2",
        "title": "USGS Landsat 5 TM Level 2, Collection 2, Tier 1",
        "type": "image_collection",
        "start_date": "1984-03-16",
        "end_date": "2012-05-05",
        "provider": "USGS",
        "tags": ["landsat", "tm", "usgs", "reflectance", "sr", "historical"],
    },
    {
        "id": "LANDSAT/LM01/C02/T1",
        "title": "USGS Landsat 1 MSS Raw DN, Collection 2, Tier 1",
        "type": "image_collection",
        "start_date": "1972-07-23",
        "end_date": "1978-01-06",
        "provider": "USGS",
        "tags": ["landsat", "mss", "usgs", "historical", "1972"],
    },
    {
        "id": "COPERNICUS/DEM/GLO30",
        "title": "Copernicus Global DSM 30m",
        "type": "image_collection",
        "start_date": "2019-01-01",
        "end_date": None,
        "provider": "European Space Agency",
        "tags": ["copernicus", "dem", "elevation", "topography", "glo30"],
    },
    {
        "id": "ESA/WorldCover/v200",
        "title": "ESA WorldCover 10m v200 (2021)",
        "type": "image_collection",
        "start_date": "2021-01-01",
        "end_date": "2021-12-31",
        "provider": "ESA",
        "tags": ["esa", "landcover", "worldcover", "10m", "classification"],
    },
    {
        "id": "ECMWF/ERA5_LAND/MONTHLY_AGGR",
        "title": "ERA5-Land Monthly Averaged - ECMWF Climate Reanalysis",
        "type": "image_collection",
        "start_date": "1950-01-01",
        "end_date": None,
        "provider": "ECMWF / Copernicus",
        "tags": ["climate", "ecmwf", "era5", "temperature", "precipitation"],
    },
]


def load_catalog(refresh: bool = False) -> List[Dict[str, Any]]:
    """Load the full Earth Engine dataset catalog from cache or remote source.

    Returns:
        List of dataset metadata dictionaries.
    """
    cache = _get_cache_path()
    now = time.time()

    if not refresh and cache.exists() and (now - cache.stat().st_mtime) < _CACHE_TTL_SECONDS:
        try:
            with open(cache, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed reading cached GEE catalog: %s. Refetching.", e)

    try:
        req = urllib.request.Request(CATALOG_URL, headers={"User-Agent": "eo-mcp/0.1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        cache.write_text(json.dumps(data), encoding="utf-8")
        return data
    except Exception as e:
        logger.warning("Could not download GEE catalog index from GitHub (%s).", e)
        if cache.exists():
            try:
                with open(cache, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        # Return bundled curated subset if network/cache unavailable
        return _FALLBACK_CURATED_DATASETS


def search_catalog(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Perform multi-term keyword ranking search across Earth Engine datasets.

    Args:
        query: Space-separated keywords (e.g. 'sentinel-2 surface reflectance' or 'land cover 10m').
        limit: Maximum results to return.

    Returns:
        List of matching dataset summaries ranked by match score.
    """
    terms = [t.strip().lower() for t in query.split() if t.strip()]
    if not terms:
        return []

    catalog = load_catalog()
    scored = []

    for entry in catalog:
        haystack = " ".join(
            str(entry.get(k, ""))
            for k in ("id", "title", "tags", "provider", "type")
        ).lower()

        score = sum(1 for t in terms if t in haystack)
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda item: -item[0])

    results = []
    for score, entry in scored[:limit]:
        results.append({
            "id": entry.get("id"),
            "title": entry.get("title"),
            "type": entry.get("type"),
            "start_date": entry.get("start_date"),
            "end_date": entry.get("end_date"),
            "provider": entry.get("provider"),
            "match_score": score,
        })

    return results


def get_dataset_entry(dataset_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve the catalog entry for an exact or prefix dataset ID.

    Matches exact ID first, followed by case-insensitive and prefix matches.
    """
    catalog = load_catalog()
    norm_id = dataset_id.strip()

    # 1. Exact match
    for entry in catalog:
        if entry.get("id") == norm_id:
            return entry

    # 2. Case-insensitive match
    for entry in catalog:
        if str(entry.get("id", "")).lower() == norm_id.lower():
            return entry

    # 3. Prefix match (e.g. COPERNICUS/DEM/GLO30 matching COPERNICUS/DEM/GLO30_2024_1)
    for entry in catalog:
        if str(entry.get("id", "")).startswith(norm_id):
            return entry

    return None
