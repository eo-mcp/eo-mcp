"""Geocoding and Spatial Coordinate Utilities."""

from typing import List, Optional, Dict, Any
import httpx


def geocode_place_name(place_name: str) -> Optional[Dict[str, Any]]:
    """
    Geocode a natural language place name into a standard WGS84 bounding box.
    Uses OpenStreetMap Nominatim with proper User-Agent compliance.

    Args:
        place_name: Name of city, region, or feature (e.g. "Valencia, Spain", "Lake Tahoe").

    Returns:
        Dict with "display_name", "bbox" [min_lon, min_lat, max_lon, max_lat], and "lat", "lon".
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": place_name,
        "format": "jsonv2",
        "limit": 1
    }
    headers = {
        "User-Agent": "eo-mcp/0.1.0 (Earth Observation Model Context Protocol; https://github.com/eo-mcp/eo-mcp)"
    }

    try:
        response = httpx.get(url, params=params, headers=headers, timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                first = data[0]
                # Nominatim boundingbox: [min_lat, max_lat, min_lon, max_lon]
                raw_box = [float(x) for x in first["boundingbox"]]
                # Convert to standard WGS84 [min_lon, min_lat, max_lon, max_lat]
                bbox = [raw_box[2], raw_box[0], raw_box[3], raw_box[1]]
                return {
                    "display_name": first.get("display_name"),
                    "lat": float(first["lat"]),
                    "lon": float(first["lon"]),
                    "bbox": bbox
                }
    except Exception:
        pass
    return None


def point_to_bbox(lat: float, lon: float, buffer_km: float = 5.0) -> List[float]:
    """
    Convert a center point (lat, lon) into a square bounding box buffered by buffer_km.
    Approximates 1 degree latitude ~ 111 km.
    """
    lat_delta = buffer_km / 111.0
    lon_delta = buffer_km / (111.0 * max(0.01, math.cos(math.radians(lat))))
    return [
        round(lon - lon_delta, 6),
        round(lat - lat_delta, 6),
        round(lon + lon_delta, 6),
        round(lat + lat_delta, 6)
    ]

import math
