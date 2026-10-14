"""NASA OPERA (Observational Products for End-Users from Remote Sensing Analysis) Provider.

Enables discovery and streaming of NASA JPL OPERA products via NASA CMR STAC:
- DSWx-HLS: Dynamic Surface Water Extent (30m)
- DIST-ALERT-HLS: High-Resolution Surface Disturbance (30m)
- RTC-S1: Radiometric Terrain Corrected Sentinel-1 SAR (30m)
- CSLC-S1: Coregistered Single Look Complex InSAR Phase

References:
- NASA JPL OPERA Project: https://www.jpl.nasa.gov/go/opera
- NASA CMR STAC API: https://cmr.earthdata.nasa.gov/stac
"""

from typing import List, Dict, Any, Optional
import httpx
from pydantic import BaseModel, Field
from eo_mcp.config import NASA_CMR_STAC_URL


OPERA_COLLECTIONS = {
    "dswx": {
        "id": "OPERA_L3_DSWX-HLS_V1_1.0",
        "provider": "POCLOUD",
        "title": "OPERA Dynamic Surface Water Extent from HLS (30m)",
        "description": "Global 30m surface water classification delineating open water, partial surface water, and inundated vegetation.",
        "assets": ["B01_WTR", "B02_BWTR", "B03_CONF", "B04_DIAG"]
    },
    "dist": {
        "id": "OPERA_L3_DIST-ALERT-HLS_V1_1",
        "provider": "LPCLOUD",
        "title": "OPERA Surface Disturbance Alert from HLS (30m)",
        "description": "Operational 30m disturbance alerts tracking canopy loss, deforestation, wildfires, and erosion.",
        "assets": ["VEG-DIST-STATUS", "VEG-ANOM-MAX", "CONF"]
    },
    "rtc": {
        "id": "OPERA_L2_RTC-S1_V1_1",
        "provider": "ASF",
        "title": "OPERA Radiometric Terrain Corrected Sentinel-1 SAR (30m)",
        "description": "High-precision radiometrically and terrain-corrected Sentinel-1 SAR backscatter in VV and VH polarizations.",
        "assets": ["VV", "VH", "mask"]
    }
}


class OPERAProductItem(BaseModel):
    """Normalized NASA OPERA Granule Item."""
    id: str
    product_type: str
    collection_id: str
    datetime: str
    bbox: List[float]
    assets: Dict[str, str]
    cloud_cover: Optional[float] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


def list_opera_product_types() -> Dict[str, Dict[str, Any]]:
    """Return dictionary of supported NASA OPERA product lines."""
    return OPERA_COLLECTIONS


def _rfc3339_range(datetime_range: str) -> str:
    """CMR STAC rejects bare dates; expand 'YYYY-MM-DD' ends to full RFC3339."""
    parts = datetime_range.split("/")
    out = []
    for i, part in enumerate(parts):
        part = part.strip()
        if len(part) == 10 and part[4] == "-" and part[7] == "-":
            part += "T00:00:00Z" if i == 0 else "T23:59:59Z"
        out.append(part)
    return "/".join(out)


def search_opera_products(
    product_type: str,
    bbox: List[float],
    datetime_range: str,
    max_cloud_cover: Optional[float] = None,
    limit: int = 5,
    timeout_sec: float = 15.0
) -> List[OPERAProductItem]:
    """
    Search NASA CMR STAC for OPERA granules.

    Args:
        product_type: One of 'dswx', 'dist', 'rtc'.
        bbox: [min_lon, min_lat, max_lon, max_lat] in WGS84.
        datetime_range: RFC3339 datetime range (e.g. '2024-06-01/2024-06-30').
        max_cloud_cover: Cloud cover percentage threshold (0-100).
        limit: Max number of items to retrieve.
        timeout_sec: Network request timeout.

    Returns:
        List of OPERAProductItem objects.
    """
    p_key = product_type.lower().strip()
    if p_key not in OPERA_COLLECTIONS:
        raise ValueError(f"Unknown OPERA product '{product_type}'. Choose from: {list(OPERA_COLLECTIONS.keys())}")

    coll_meta = OPERA_COLLECTIONS[p_key]
    coll_id = coll_meta["id"]
    provider = coll_meta["provider"]

    # CMR STAC endpoint: https://cmr.earthdata.nasa.gov/stac/{PROVIDER}/search
    endpoint = f"{NASA_CMR_STAC_URL}/{provider}/search"
    
    payload: Dict[str, Any] = {
        "collections": [coll_id],
        "bbox": bbox,
        "datetime": _rfc3339_range(datetime_range),
        "limit": limit
    }

    try:
        with httpx.Client(timeout=timeout_sec) as client:
            resp = client.post(endpoint, json=payload, headers={"Content-Type": "application/json"})
            if resp.status_code == 200:
                data = resp.json()
                features = data.get("features", [])
                results: List[OPERAProductItem] = []
                for feat in features:
                    props = feat.get("properties", {})
                    cloud = props.get("eo:cloud_cover", props.get("cloud_cover"))
                    if max_cloud_cover is not None and cloud is not None and cloud > max_cloud_cover:
                        continue

                    assets_map = {}
                    for a_name, a_val in feat.get("assets", {}).items():
                        if isinstance(a_val, dict) and "href" in a_val:
                            assets_map[a_name] = a_val["href"]

                    results.append(
                        OPERAProductItem(
                            id=feat.get("id", "unknown"),
                            product_type=p_key,
                            collection_id=coll_id,
                            datetime=props.get("datetime", ""),
                            bbox=feat.get("bbox", bbox),
                            assets=assets_map,
                            cloud_cover=float(cloud) if cloud is not None else None,
                            properties=props
                        )
                    )
                return results
    except Exception:
        pass

    # No fabricated granules: an unreachable or failed CMR search returns nothing.
    return []
