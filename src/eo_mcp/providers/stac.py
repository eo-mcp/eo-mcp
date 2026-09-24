"""Generic STAC Client for multi-catalog satellite discovery."""

from typing import List, Optional, Dict, Any, Union
import httpx
from pystac_client import Client
from pystac_client.stac_api_io import StacApiIO
from eo_mcp.config import (
    EARTH_SEARCH_STAC_URL,
    PLANETARY_COMPUTER_STAC_URL,
    NASA_CMR_STAC_URL,
    CDSE_STAC_URL
)
from eo_mcp.core.models import (
    STACSearchResultItem,
    CompactSTACItem,
    CompactSTACResponse
)


class HttpxStacApiIO(StacApiIO):
    """Resilient HTTPX-backed STAC API I/O avoiding urllib3 OpenSSL handshake issues on Windows."""

    def __init__(self, headers: Optional[Dict[str, str]] = None, timeout: float = 30.0):
        super().__init__(headers=headers)
        self._client = httpx.Client(timeout=timeout, follow_redirects=True, headers=headers or {})

    def request(
        self,
        href: str,
        method: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> str:
        m = (method or "GET").upper()
        if m == "POST":
            r = self._client.post(str(href), json=parameters, headers=headers)
        else:
            r = self._client.get(str(href), params=parameters, headers=headers)
        if r.status_code != 200:
            import pystac_client.exceptions
            raise pystac_client.exceptions.APIError(f"HTTP {r.status_code}: {r.text}")
        return r.text


def get_stac_client(catalog_url: str = EARTH_SEARCH_STAC_URL, headers: Optional[Dict[str, str]] = None) -> Client:
    """Return a STAC client, preferring resilient HTTPX IO over standard requests on Windows."""
    try:
        return Client.open(catalog_url, headers=headers, stac_io=HttpxStacApiIO(headers=headers))
    except Exception:
        return Client.open(catalog_url, headers=headers)


# Standard Science Band Mapping Dictionaries
S2_BAND_MAP: Dict[str, str] = {
    "coastal": "B01", "b01": "B01",
    "blue": "B02", "b02": "B02",
    "green": "B03", "b03": "B03",
    "red": "B04", "b04": "B04",
    "rededge1": "B05", "b05": "B05",
    "rededge2": "B06", "b06": "B06",
    "rededge3": "B07", "b07": "B07",
    "nir": "B08", "b08": "B08",
    "nir08": "B8A", "b8a": "B8A",
    "nir09": "B09", "b09": "B09",
    "cirrus": "B10", "b10": "B10",
    "swir16": "B11", "b11": "B11",
    "swir22": "B12", "b12": "B12",
    "scl": "SCL",
}

LANDSAT_BAND_MAP: Dict[str, str] = {
    "coastal": "B01", "b01": "B01", "b1": "B01",
    "blue": "B02", "b02": "B02", "b2": "B02",
    "green": "B03", "b03": "B03", "b3": "B03",
    "red": "B04", "b04": "B04", "b4": "B04",
    "nir08": "B05", "nir": "B05", "b05": "B05", "b5": "B05",
    "swir16": "B06", "b06": "B06", "b6": "B06",
    "swir22": "B07", "b07": "B07", "b7": "B07",
    "thermal": "B10", "b10": "B10",
    "qa_pixel": "QA_PIXEL",
}

SAR_BAND_MAP: Dict[str, str] = {
    "vv": "VV",
    "vh": "VH",
    "hh": "HH",
    "hv": "HV",
}

DEM_BAND_MAP: Dict[str, str] = {
    "elevation": "ELEVATION",
    "data": "ELEVATION",
    "dem": "ELEVATION",
}


def normalize_stac_bands(asset_keys: List[str], collection: str = "") -> List[str]:
    """
    Map raw STAC asset keys into clean, standard science band identifiers.

    Filters out thumbnails, metadata, overview renders, and redundant jp2/format keys.
    Returns normalized band names sorted logically (e.g. ['B02', 'B03', 'B04', 'B08', 'B11', 'B12'],
    ['VV', 'VH'], or ['ELEVATION']).
    """
    coll_lower = collection.lower() if collection else ""

    is_s2 = "sentinel-2" in coll_lower or "s2" in coll_lower
    is_landsat = "landsat" in coll_lower or "lc08" in coll_lower or "lc09" in coll_lower
    is_sar = "sentinel-1" in coll_lower or "s1" in coll_lower or any(k.lower() in ("vv", "vh", "hh", "hv") for k in asset_keys)
    is_dem = "dem" in coll_lower or "elevation" in coll_lower or "cop-dem" in coll_lower or any(k.lower() in ("elevation", "dem") for k in asset_keys)

    normalized: List[str] = []
    seen = set()

    s2_core = ["B02", "B03", "B04", "B08", "B11", "B12"]
    s2_order = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B11", "B12", "SCL"]
    landsat_core = ["B02", "B03", "B04", "B05", "B06", "B07"]
    landsat_order = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B10", "QA_PIXEL"]
    sar_order = ["VV", "VH", "HH", "HV"]
    dem_order = ["ELEVATION"]

    for raw_key in asset_keys:
        k = raw_key.lower().strip()
        if k.endswith("-jp2") or k.endswith(".jp2") or k.endswith("-cogs") or k.endswith("-cog"):
            continue
        if k in ("thumbnail", "overview", "rendered_preview", "visual", "granule_metadata",
                 "tileinfo_metadata", "metadata", "preview", "wvp", "aot", "ang", "mtl"):
            continue

        band_name = None
        if is_dem:
            if k in DEM_BAND_MAP:
                band_name = DEM_BAND_MAP[k]
        elif is_sar:
            if k in SAR_BAND_MAP:
                band_name = SAR_BAND_MAP[k]
        elif is_landsat:
            if k in LANDSAT_BAND_MAP:
                band_name = LANDSAT_BAND_MAP[k]
        elif is_s2:
            if k in S2_BAND_MAP:
                band_name = S2_BAND_MAP[k]
        else:
            if k in SAR_BAND_MAP:
                band_name = SAR_BAND_MAP[k]
            elif k in DEM_BAND_MAP:
                band_name = DEM_BAND_MAP[k]
            elif k in S2_BAND_MAP:
                band_name = S2_BAND_MAP[k]
            elif k in LANDSAT_BAND_MAP:
                band_name = LANDSAT_BAND_MAP[k]
            elif k.startswith("b") and len(k) <= 4 and k[1:].isalnum():
                band_name = k.upper()

        if band_name and band_name not in seen:
            seen.add(band_name)
            normalized.append(band_name)

    if is_dem:
        return [b for b in dem_order if b in seen] or normalized or ["ELEVATION"]
    elif is_sar:
        return [b for b in sar_order if b in seen] or normalized
    elif is_landsat:
        if all(cb in seen for cb in landsat_core):
            return landsat_core
        return [b for b in landsat_order if b in seen] or normalized
    elif is_s2:
        if all(cb in seen for cb in s2_core):
            return s2_core
        return [b for b in s2_order if b in seen] or normalized

    return sorted(normalized) if normalized else [k.upper() for k in asset_keys if not k.endswith("-jp2")][:6]


def format_compact_stac_items(
    items: List[STACSearchResultItem],
    collection: Optional[str] = None
) -> CompactSTACResponse:
    """
    Format a list of STACSearchResultItem objects into a high-signal,
    token-optimized CompactSTACResponse strictly under 2,500 characters for 5 scenes.
    """
    compact_scenes: List[CompactSTACItem] = []

    for item in items:
        # Determine platform
        platform = item.platform
        if not platform:
            cid = item.id.lower()
            coll = (item.collection or collection or "").lower()
            if "s2a" in cid or "sentinel-2a" in coll:
                platform = "sentinel-2a"
            elif "s2b" in cid or "sentinel-2b" in coll:
                platform = "sentinel-2b"
            elif "sentinel-2" in coll:
                platform = "sentinel-2"
            elif "lc08" in cid or "landsat-8" in coll:
                platform = "landsat-8"
            elif "lc09" in cid or "landsat-9" in coll:
                platform = "landsat-9"
            elif "landsat" in coll:
                platform = "landsat"
            elif "s1a" in cid:
                platform = "sentinel-1a"
            elif "s1b" in cid:
                platform = "sentinel-1b"
            elif "sentinel-1" in coll:
                platform = "sentinel-1"
            elif "cop-dem" in coll or "dem" in coll:
                platform = "copernicus-dem"
            else:
                platform = item.collection or collection or "unknown"

        # Determine bands (cap at 6 key science bands to guarantee tight agent token budgets)
        if item.bands:
            bands = item.bands[:6] if len(item.bands) > 6 else item.bands
        elif item.assets:
            bands = normalize_stac_bands(item.assets, collection=item.collection or collection or "")[:6]
        else:
            bands = []

        # Round bbox coordinates to 4 decimal places (~11m precision)
        clean_bbox = [round(float(c), 4) for c in item.bbox] if item.bbox else []

        # Cloud cover rounded to 1 decimal place
        clean_cloud = round(float(item.cloud_cover), 1) if item.cloud_cover is not None else None

        # Clean datetime string (strip sub-second noise if present)
        dt_str = str(item.datetime)
        if "." in dt_str and (dt_str.endswith("Z") or "+00:00" in dt_str):
            base_part = dt_str.split(".")[0]
            dt_str = f"{base_part}Z"

        compact_scenes.append(
            CompactSTACItem(
                id=item.id,
                platform=platform,
                datetime=dt_str,
                cloud_cover=clean_cloud,
                bbox=clean_bbox,
                bands=bands
            )
        )

    target_coll = collection or (items[0].collection if items else "unknown")
    return CompactSTACResponse(
        count=len(compact_scenes),
        scenes=compact_scenes,
        collection=target_coll
    )


def search_stac_catalog(
    catalog_url: str,
    collections: List[str],
    bbox: List[float],
    datetime_range: str,
    max_cloud_cover: Optional[float] = None,
    limit: int = 5,
    compact: bool = False
) -> Union[List[STACSearchResultItem], CompactSTACResponse]:
    """
    Query a STAC API catalog for items matching spatial, temporal, and cloud criteria.

    Args:
        catalog_url: STAC API root endpoint URL.
        collections: List of collection names (e.g. ['sentinel-2-l2a']).
        bbox: [min_lon, min_lat, max_lon, max_lat] in WGS84.
        datetime_range: RFC3339 datetime range (e.g. '2024-01-01/2024-03-31' or single date).
        max_cloud_cover: Max allowed cloud percentage (0 - 100).
        limit: Maximum number of items to return.
        compact: When True, return high-signal CompactSTACResponse under token budget.
                 When False (default), return List[STACSearchResultItem] with all asset keys.

    Returns:
        List of STACSearchResultItem objects or CompactSTACResponse if compact=True.
    """
    client = get_stac_client(catalog_url)

    query = {}
    if max_cloud_cover is not None:
        query["eo:cloud_cover"] = {"lt": max_cloud_cover}

    search = client.search(
        collections=collections,
        bbox=bbox,
        datetime=datetime_range,
        query=query if query else None,
        max_items=limit
    )

    results: List[STACSearchResultItem] = []
    for item in search.items():
        props = item.properties
        cloud = props.get("eo:cloud_cover", props.get("cloud_cover", None))

        # Determine platform
        platform = props.get("platform", props.get("constellation", None))
        if not platform:
            cid = item.id.lower()
            if "s2a" in cid:
                platform = "sentinel-2a"
            elif "s2b" in cid:
                platform = "sentinel-2b"
            elif "lc08" in cid:
                platform = "landsat-8"
            elif "lc09" in cid:
                platform = "landsat-9"
            elif "s1a" in cid:
                platform = "sentinel-1a"
            elif "s1b" in cid:
                platform = "sentinel-1b"
            else:
                platform = item.collection_id or (collections[0] if collections else "unknown")

        # Determine thumbnail URL if available
        thumbnail_url = None
        for key in ["thumbnail", "overview", "rendered_preview"]:
            if key in item.assets:
                href_val = getattr(item.assets[key], "href", None)
                if href_val is not None:
                    thumbnail_url = str(href_val)
                break

        raw_assets = list(item.assets.keys())
        coll_name = item.collection_id or (collections[0] if collections else "")
        normalized_bands = normalize_stac_bands(raw_assets, collection=coll_name)

        raw_bbox = list(item.bbox) if item.bbox else bbox
        clean_bbox = [round(float(c), 4) for c in raw_bbox]

        results.append(
            STACSearchResultItem(
                id=item.id,
                collection=coll_name or "unknown",
                datetime=str(item.datetime or props.get("datetime", "")),
                cloud_cover=round(float(cloud), 1) if cloud is not None else None,
                bbox=clean_bbox,
                assets=raw_assets,
                thumbnail_url=thumbnail_url,
                platform=platform,
                bands=normalized_bands
            )
        )

    if compact:
        return format_compact_stac_items(results, collection=collections[0] if collections else None)

    return results


def search_stac_compact(
    catalog_url: str,
    collections: List[str],
    bbox: List[float],
    datetime_range: str,
    max_cloud_cover: Optional[float] = None,
    limit: int = 5
) -> CompactSTACResponse:
    """Convenience helper to search STAC and return a token-optimized CompactSTACResponse directly."""
    return search_stac_catalog(
        catalog_url=catalog_url,
        collections=collections,
        bbox=bbox,
        datetime_range=datetime_range,
        max_cloud_cover=max_cloud_cover,
        limit=limit,
        compact=True
    )


def search_sentinel2_scenes(
    bbox: List[float],
    datetime_range: str,
    max_cloud_cover: float = 20.0,
    limit: int = 5,
    compact: bool = False
) -> Union[List[STACSearchResultItem], CompactSTACResponse]:
    """Zero-config search for Sentinel-2 L2A on AWS Earth Search."""
    return search_stac_catalog(
        catalog_url=EARTH_SEARCH_STAC_URL,
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime_range=datetime_range,
        max_cloud_cover=max_cloud_cover,
        limit=limit,
        compact=compact
    )


def search_landsat_scenes(
    bbox: List[float],
    datetime_range: str,
    max_cloud_cover: float = 20.0,
    limit: int = 5,
    compact: bool = False
) -> Union[List[STACSearchResultItem], CompactSTACResponse]:
    """Zero-config search for Landsat Collection 2 Level-2 on AWS Earth Search."""
    return search_stac_catalog(
        catalog_url=EARTH_SEARCH_STAC_URL,
        collections=["landsat-c2-l2"],
        bbox=bbox,
        datetime_range=datetime_range,
        max_cloud_cover=max_cloud_cover,
        limit=limit,
        compact=compact
    )
