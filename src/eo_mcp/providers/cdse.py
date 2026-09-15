"""Copernicus Data Space Ecosystem (CDSE) Connector.

Provides direct access to Sentinel-1, Sentinel-2, Sentinel-3, and Sentinel-5P
catalogs via CDSE STAC and OData APIs.
"""

import os
from typing import List, Optional, Dict, Any
import httpx
from eo_mcp.config import CDSE_STAC_URL


def get_cdse_token(username: Optional[str] = None, password: Optional[str] = None) -> Optional[str]:
    """Retrieve CDSE OAuth token if credentials are provided in environment or arguments."""
    u = username or os.getenv("CDSE_USERNAME", "")
    p = password or os.getenv("CDSE_PASSWORD", "")
    if not u or not p:
        return None

    token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    try:
        response = httpx.post(
            token_url,
            data={
                "client_id": "cdse-public",
                "username": u,
                "password": p,
                "grant_type": "password"
            },
            timeout=10.0
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception:
        pass
    return None


def verify_cdse_credentials(username: str, password: str) -> Dict[str, Any]:
    """Verify CDSE credentials against Copernicus Data Space identity endpoint."""
    token = get_cdse_token(username=username, password=password)
    if token:
        return {
            "valid": True,
            "message": "Successfully authenticated with Copernicus Data Space Ecosystem (CDSE).",
            "token_preview": f"{token[:12]}..."
        }
    return {
        "valid": False,
        "message": "Authentication failed. Please verify your Copernicus Data Space username and password."
    }


def generate_cdse_download_info(product_id: str) -> Dict[str, Any]:
    """Generate authenticated Copernicus Data Space download URL and curl snippet."""
    token = get_cdse_token()
    base_download_url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
    
    if not token:
        return {
            "status": "credentials_required",
            "product_id": product_id,
            "download_endpoint": base_download_url,
            "message": "CDSE credentials not found. Use configure_credentials(provider='cdse', username=..., password=...) to unlock direct full-granule downloads.",
            "free_account_url": "https://dataspace.copernicus.eu"
        }

    return {
        "status": "ready",
        "product_id": product_id,
        "download_url": base_download_url,
        "auth_header": "Bearer <TOKEN_ATTACHED>",
        "curl_command": f"curl -H 'Authorization: Bearer {token[:16]}...' '{base_download_url}' -o '{product_id}.zip'",
        "instructions": "Full Sentinel product zip package can be downloaded directly from Copernicus Data Space zipper service."
    }



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
