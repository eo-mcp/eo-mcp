"""Copernicus Data Space Ecosystem (CDSE) Connector.

Provides direct access to Sentinel-1, Sentinel-2, Sentinel-3, and Sentinel-5P
catalogs via CDSE STAC and OData APIs.
"""

from typing import List, Optional, Dict, Any
import httpx
from eo_mcp.config import CDSE_STAC_URL, CDSE_USERNAME, CDSE_PASSWORD
from eo_mcp.core.models import STACSearchResultItem


def get_cdse_token() -> Optional[str]:
    """Retrieve CDSE OAuth token if credentials are provided in environment."""
    if not CDSE_USERNAME or not CDSE_PASSWORD:
        return None

    token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    try:
        response = httpx.post(
            token_url,
            data={
                "client_id": "cdse-public",
                "username": CDSE_USERNAME,
                "password": CDSE_PASSWORD,
                "grant_type": "password"
            },
            timeout=10.0
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception:
        pass
    return None


def search_cdse_sentinel1(
    bbox: List[float],
    datetime_range: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Search Copernicus Data Space Ecosystem for Sentinel-1 GRD SAR scenes."""
    # Build open OData or STAC search
    endpoint = f"{CDSE_STAC_URL}/search"
    payload = {
        "collections": ["SENTINEL-1"],
        "bbox": bbox,
        "datetime": datetime_range,
        "limit": limit
    }
    
    try:
        response = httpx.post(endpoint, json=payload, timeout=15.0)
        if response.status_code == 200:
            data = response.json()
            items = []
            for feat in data.get("features", []):
                items.append({
                    "id": feat.get("id"),
                    "datetime": feat.get("properties", {}).get("datetime"),
                    "bbox": feat.get("bbox", bbox),
                    "assets": list(feat.get("assets", {}).keys())
                })
            return items
    except Exception as e:
        return [{"error": f"CDSE query error: {str(e)}"}]
    return []
