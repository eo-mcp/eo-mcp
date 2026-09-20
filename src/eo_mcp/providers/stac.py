"""Generic STAC Client for multi-catalog satellite discovery."""

from typing import List, Optional, Dict, Any
import httpx
from pystac_client import Client
from pystac_client.stac_api_io import StacApiIO
from eo_mcp.config import (
    EARTH_SEARCH_STAC_URL,
    PLANETARY_COMPUTER_STAC_URL,
    NASA_CMR_STAC_URL,
    CDSE_STAC_URL
)
from eo_mcp.core.models import STACSearchResultItem


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


def search_stac_catalog(
    catalog_url: str,
    collections: List[str],
    bbox: List[float],
    datetime_range: str,
    max_cloud_cover: Optional[float] = None,
    limit: int = 5
) -> List[STACSearchResultItem]:
    """
    Query a STAC API catalog for items matching spatial, temporal, and cloud criteria.

    Args:
        catalog_url: STAC API root endpoint URL.
        collections: List of collection names (e.g. ['sentinel-2-l2a']).
        bbox: [min_lon, min_lat, max_lon, max_lat] in WGS84.
        datetime_range: RFC3339 datetime range (e.g. '2024-01-01/2024-03-31' or single date).
        max_cloud_cover: Max allowed cloud percentage (0 - 100).
        limit: Maximum number of items to return.

    Returns:
        List of STACSearchResultItem objects.
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
        
        # Determine thumbnail URL if available
        thumbnail_url = None
        for key in ["thumbnail", "overview", "rendered_preview"]:
            if key in item.assets:
                thumbnail_url = item.assets[key].href
                break

        results.append(
            STACSearchResultItem(
                id=item.id,
                collection=item.collection_id or collections[0],
                datetime=str(item.datetime or props.get("datetime", "")),
                cloud_cover=float(cloud) if cloud is not None else None,
                bbox=list(item.bbox) if item.bbox else bbox,
                assets=list(item.assets.keys()),
                thumbnail_url=thumbnail_url
            )
        )

    return results


def search_sentinel2_scenes(
    bbox: List[float],
    datetime_range: str,
    max_cloud_cover: float = 20.0,
    limit: int = 5
) -> List[STACSearchResultItem]:
    """Zero-config search for Sentinel-2 L2A on AWS Earth Search."""
    return search_stac_catalog(
        catalog_url=EARTH_SEARCH_STAC_URL,
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime_range=datetime_range,
        max_cloud_cover=max_cloud_cover,
        limit=limit
    )


def search_landsat_scenes(
    bbox: List[float],
    datetime_range: str,
    max_cloud_cover: float = 20.0,
    limit: int = 5
) -> List[STACSearchResultItem]:
    """Zero-config search for Landsat Collection 2 Level-2 on AWS Earth Search."""
    return search_stac_catalog(
        catalog_url=EARTH_SEARCH_STAC_URL,
        collections=["landsat-c2-l2"],
        bbox=bbox,
        datetime_range=datetime_range,
        max_cloud_cover=max_cloud_cover,
        limit=limit
    )
