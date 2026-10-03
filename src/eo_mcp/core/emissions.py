"""
Sentinel-5P TROPOMI atmospheric emissions & OpenAQ air quality monitoring engine.

Zero-infrastructure MCP capability leveraging Copernicus Sentinel-5P STAC endpoints
(NO2, SO2, CO, Methane CH4) and the open OpenAQ public REST API to map
industrial plume emissions and urban air quality exceedances.

References:
- Veefkind, J. P., et al. (2012). TROPOMI on the ESA Sentinel-5 Precursor: A GMES
  mission for global observations of the atmospheric composition for climate, air
  quality and ozone layer applications. Remote Sensing of Environment, 120, 70-83.
  DOI: 10.1016/j.rse.2011.09.027
- van Geffen, J., et al. (2020). S5P TROPOMI NO2 slant column retrieval: Method,
  stability, uncertainties and comparisons with OMI. Atmospheric Measurement
  Techniques, 13(3), 1315-1335. DOI: 10.5194/amt-13-1315-2020
"""

from typing import List, Dict, Any, Optional, Tuple
import os
import httpx


# OpenAQ Public API endpoint (Free & zero API key required)
OPENAQ_LOCATIONS_URL = "https://api.openaq.org/v3/locations"


# Standard atmospheric thresholds for Sentinel-5P column density (in umol/m2)
AIR_QUALITY_THRESHOLDS = {
    "NO2": {
        "unit": "umol/m2",
        "clean_background": 40.0,
        "elevated": 85.0,
        "critical_plume": 150.0,
        "directive": "EU Ambient Air Quality Directive (2008/50/EC)"
    },
    "CH4": {
        "unit": "ppb",
        "clean_background": 1850.0,
        "elevated": 1920.0,
        "critical_plume": 2000.0,
        "directive": "EU Methane Regulation (2024/1787)"
    },
    "SO2": {
        "unit": "umol/m2",
        "clean_background": 15.0,
        "elevated": 50.0,
        "critical_plume": 120.0,
        "directive": "Industrial Emissions Directive (IED 2010/75/EU)"
    },
    "CO": {
        "unit": "mmol/m2",
        "clean_background": 30.0,
        "elevated": 45.0,
        "critical_plume": 70.0,
        "directive": "WHO Global Air Quality Guidelines"
    }
}


def query_sentinel5p_emissions(
    bbox: List[float],
    gas: str = "NO2",
    datetime_range: str = "2024-06-01/2024-06-30"
) -> Dict[str, Any]:
    """
    Extract tropospheric column densities from Sentinel-5P TROPOMI records.

    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat] in WGS84.
        gas: Target trace gas ('NO2', 'CH4', 'SO2', or 'CO').
        datetime_range: Acquisition date window.

    Returns:
        Dictionary with column density statistics, plume status, and spatial hotspots.

    References:
    - Veefkind et al. (2012). Remote Sensing of Environment, 120, 70-83.
      DOI: 10.1016/j.rse.2011.09.027
    - van Geffen et al. (2020). Atmospheric Measurement Techniques, 13(3), 1315-1335.
      DOI: 10.5194/amt-13-1315-2020
    """
    gas_key = gas.upper()
    meta = AIR_QUALITY_THRESHOLDS.get(gas_key, AIR_QUALITY_THRESHOLDS["NO2"])
    product = {"NO2": "no2", "CH4": "ch4", "SO2": "so2", "CO": "co"}.get(gas_key, "no2")

    if "/" in datetime_range and "T" not in datetime_range:
        start, end = datetime_range.split("/", 1)
        stac_datetime = f"{start}T00:00:00Z/{end}T23:59:59Z"
    else:
        stac_datetime = datetime_range

    base = {
        "gas": gas_key,
        "unit": meta["unit"],
        "bbox": bbox,
        "datetime_range": datetime_range,
        "mean_tropospheric_density": None,
        "mean_column_density": None,
        "max_tropospheric_density": None,
        "max_column_density": None,
        "thresholds": meta,
        "plume_status": "NOT_READ",
        "plume_detected": False,
        "plume_hotspots_count": 0,
        "hotspots": [],
        "satellite": "Sentinel-5P TROPOMI",
        "directive_alignment": meta["directive"],
        "compliance_directive": meta["directive"],
        "data_source": "planetarycomputer sentinel-5p-l2-netcdf",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                "https://planetarycomputer.microsoft.com/api/stac/v1/search",
                json={
                    "collections": ["sentinel-5p-l2-netcdf"],
                    "bbox": bbox,
                    "datetime": stac_datetime,
                    "limit": 1,
                    "query": {"s5p:product_name": {"eq": product}},
                    "sortby": [{"field": "datetime", "direction": "desc"}],
                },
            )
            resp.raise_for_status()
            features = resp.json().get("features") or []
    except Exception as exc:
        base["notice"] = (
            f"Sentinel-5P search failed ({exc.__class__.__name__}). "
            "No column density was computed."
        )
        return base

    if not features:
        base["notice"] = (
            f"No Sentinel-5P {product} scene in this box and window. "
            "No column density was computed."
        )
        return base

    feature = features[0]
    base["scene_id"] = feature.get("id")
    base["scene_datetime"] = (feature.get("properties") or {}).get("datetime")
    base["notice"] = (
        "A Sentinel-5P scene was found. The L2 granule was not read, "
        "so no column density, plume, or compliance result is reported."
    )
    return base


def fetch_openaq_ground_truth(
    bbox: List[float],
    parameter: str = "no2",
    timeout: float = 6.0
) -> List[Dict[str, Any]]:
    """
    Fetch in-situ air quality monitoring ground stations from the OpenAQ public API.

    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat] in WGS84.
        parameter: Target chemical parameter (no2, pm25, pm10, so2, co, o3).
        timeout: HTTP request timeout.

    Returns:
        List of ground monitoring stations with coordinates and reported values.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    stations = []

    try:
        params = {
            "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "parameter": parameter.lower(),
            "limit": 10
        }
        api_key = os.getenv("OPENAQ_API_KEY", "").strip()
        if not api_key:
            return []
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(
                OPENAQ_LOCATIONS_URL,
                params=params,
                headers={"X-API-Key": api_key},
            )
            if resp.status_code == 200:
                data = resp.json()
                for res in data.get("results", []):
                    coords = res.get("coordinates", {})
                    lat = coords.get("latitude")
                    lon = coords.get("longitude")
                    name = res.get("name") or str(res.get("id"))
                    if lat and lon:
                        stations.append({
                            "station_id": name,
                            "station_name": name,
                            "lat": round(lat, 5),
                            "lon": round(lon, 5),
                            "city": res.get("city", "Regional Network"),
                            "country": res.get("country", "EU"),
                            "source": "OpenAQ_Public_Station"
                        })
    except Exception:
        pass

    return stations


def emissions_to_geojson(
    emissions: Dict[str, Any],
    ground_stations: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Serialize emissions hotspots and ground stations to GeoJSON FeatureCollection."""
    if ground_stations is None:
        ground_stations = emissions.get("openaq_ground_stations", [])

    features = []

    # Satellite plume hotspots
    for h in emissions.get("hotspots", []):
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [h["lon"], h["lat"]]
            },
            "properties": {
                "feature_type": "SATELLITE_EMISSIONS_HOTSPOT",
                "hotspot_id": h["hotspot_id"],
                "gas": emissions.get("gas"),
                "column_density": h["column_density"],
                "unit": h["unit"],
                "exceedance": h["exceedance_level"]
            }
        })

    # Ground monitoring stations
    for s in ground_stations:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [s["lon"], s["lat"]]
            },
            "properties": {
                "feature_type": "GROUND_MONITORING_STATION",
                "station_id": s["station_id"],
                "station_name": s.get("station_name", s["station_id"]),
                "city": s.get("city"),
                "reported_value": s.get("reported_value_ug_m3")
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }


def emissions_to_csv(emissions: Dict[str, Any]) -> str:
    """Serialize emissions hotspots to tabular CSV."""
    lines = ["hotspot_id,gas,feature_type,lat,lon,column_density,unit,exceedance_level"]
    gas = emissions.get("gas", "NO2")
    for h in emissions.get("hotspots", []):
        lines.append(
            f"{h['hotspot_id']},{gas},SATELLITE_EMISSIONS_HOTSPOT,{h['lat']},{h['lon']},{h['column_density']},{h['unit']},{h['exceedance_level']}"
        )
    return "\n".join(lines)

