"""Configuration, public STAC endpoints, and environment settings for eo-mcp."""

import os
from typing import Dict, List

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
