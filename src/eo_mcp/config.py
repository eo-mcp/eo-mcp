"""Configuration, public STAC endpoints, and environment settings for eo-mcp."""

import os
from typing import Dict, List, Any, Optional


# Public Zero-Config STAC Endpoints
EARTH_SEARCH_STAC_URL = "https://earth-search.aws.element84.com/v1"
CDSE_STAC_URL = "https://catalogue.dataspace.copernicus.eu/stac"
PLANETARY_COMPUTER_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
NASA_CMR_STAC_URL = "https://cmr.earthdata.nasa.gov/stac"

# Optional Government Credentials for full archives
CDSE_USERNAME = os.getenv("CDSE_USERNAME", "")
CDSE_PASSWORD = os.getenv("CDSE_PASSWORD", "")
EARTHDATA_TOKEN = os.getenv("EARTHDATA_TOKEN", "")

# Standard collection mappings
COLLECTIONS_META: Dict[str, Dict[str, any]] = {
    "sentinel-2-l2a": {
        "title": "Sentinel-2 Level-2A (Surface Reflectance)",
        "source": "AWS Earth Search (Element 84)",
        "resolution_m": 10,
        "bands": {
            "blue": "blue",
            "green": "green",
            "red": "red",
            "nir": "nir",
            "nir08": "nir08",
            "swir16": "swir16",
            "swir22": "swir22",
            "scl": "scl"
        },
        "free_access": True
    },
    "landsat-c2-l2": {
        "title": "Landsat Collection 2 Level-2",
        "source": "AWS Earth Search (Element 84)",
        "resolution_m": 30,
        "bands": {
            "blue": "blue",
            "green": "green",
            "red": "red",
            "nir": "nir08",
            "swir16": "swir16",
            "swir22": "swir22"
        },
        "free_access": True
    },
    "cop-dem-glo-30": {
        "title": "Copernicus DEM GLO-30 (Global Elevation)",
        "source": "AWS Earth Search (Element 84)",
        "resolution_m": 30,
        "bands": {
            "elevation": "data"
        },
        "free_access": True
    },
    "sentinel-1-grd": {
        "title": "Sentinel-1 GRD (Synthetic Aperture Radar)",
        "source": "Copernicus CDSE / Planetary Computer",
        "resolution_m": 10,
        "bands": {
            "vv": "vv",
            "vh": "vh"
        },
        "free_access": True
    }
}


def update_credential(provider: str, **kwargs) -> Dict[str, Any]:
    """Dynamically set credentials in memory and environment."""
    p_clean = provider.lower().strip()
    if p_clean in ["cdse", "copernicus"]:
        username = kwargs.get("username")
        password = kwargs.get("password")
        if username:
            os.environ["CDSE_USERNAME"] = str(username).strip()
        if password:
            os.environ["CDSE_PASSWORD"] = str(password).strip()
        is_conf = bool(os.getenv("CDSE_USERNAME") and os.getenv("CDSE_PASSWORD"))
        return {
            "provider": "cdse",
            "status": "configured" if is_conf else "partial",
            "username": os.getenv("CDSE_USERNAME", ""),
            "message": "CDSE credentials saved in environment. Full-granule downloads and authenticated OData APIs active." if is_conf else "Provide both username and password for CDSE."
        }
    elif p_clean in ["earthdata", "nasa"]:
        token = kwargs.get("token") or kwargs.get("api_key") or kwargs.get("token_or_key") or ""
        if token:
            os.environ["EARTHDATA_TOKEN"] = str(token).strip()
        is_conf = bool(os.getenv("EARTHDATA_TOKEN"))
        return {
            "provider": "earthdata",
            "status": "configured" if is_conf else "cleared",
            "message": "NASA Earthdata token active." if is_conf else "No token provided."
        }
    elif p_clean in ["planetary_computer", "microsoft", "pc"]:
        key = kwargs.get("api_key") or kwargs.get("token") or kwargs.get("token_or_key") or ""
        if key:
            os.environ["PC_SDK_SUBSCRIPTION_KEY"] = str(key).strip()
        is_conf = bool(os.getenv("PC_SDK_SUBSCRIPTION_KEY"))
        return {
            "provider": "planetary_computer",
            "status": "configured" if is_conf else "cleared",
            "message": "Microsoft Planetary Computer subscription key active." if is_conf else "No key provided."
        }
    elif p_clean in ["firms", "nasa_firms"]:
        key = kwargs.get("api_key") or kwargs.get("token") or kwargs.get("token_or_key") or ""
        if key:
            os.environ["MAP_KEY"] = str(key).strip()
        is_conf = bool(os.getenv("MAP_KEY"))
        return {
            "provider": "firms",
            "status": "configured" if is_conf else "cleared",
            "message": "NASA FIRMS MAP_KEY active for high-volume fire feeds." if is_conf else "No key provided."
        }
    return {
        "error": f"Unknown provider '{provider}'. Supported: 'cdse', 'earthdata', 'planetary_computer', 'firms'."
    }


def get_credentials_status_summary() -> Dict[str, Any]:
    """Summarize configured credentials and unlocked services."""
    cdse_u = os.getenv("CDSE_USERNAME", "")
    cdse_p = os.getenv("CDSE_PASSWORD", "")
    ed_t = os.getenv("EARTHDATA_TOKEN", "")
    pc_k = os.getenv("PC_SDK_SUBSCRIPTION_KEY", "")
    firms_k = os.getenv("MAP_KEY", "")

    # Mask username for privacy
    masked_u = ""
    if cdse_u:
        if "@" in cdse_u:
            parts = cdse_u.split("@")
            masked_u = f"{parts[0][:2]}***@{parts[1]}"
        else:
            masked_u = f"{cdse_u[:2]}***"

    return {
        "zero_config_public_mode_active": True,
        "providers": {
            "cdse": {
                "configured": bool(cdse_u and cdse_p),
                "identity": masked_u if masked_u else None,
                "capabilities": [
                    "Direct official Copernicus product zip downloads",
                    "Official Copernicus OData API access",
                    "Dedicated CDSE STAC quotas"
                ] if (cdse_u and cdse_p) else [
                    "Zero-config public STAC active",
                    "Optional: supply credentials via configure_credentials(provider='cdse', username=..., password=...) for direct full-granule downloads"
                ]
            },
            "earthdata": {
                "configured": bool(ed_t),
                "capabilities": ["Direct NASA DAAC authenticated downloads active"] if ed_t else ["Zero-config public CMR STAC active"]
            },
            "planetary_computer": {
                "configured": bool(pc_k),
                "capabilities": ["High-rate Planetary Computer SAS tokens active"] if pc_k else ["Zero-config public Planetary Computer STAC active"]
            },
            "nasa_firms": {
                "configured": bool(firms_k),
                "capabilities": ["High-volume FIRMS active fire queries with custom MAP_KEY"] if firms_k else ["Zero-config public area feeds active"]
            }
        }
    }

