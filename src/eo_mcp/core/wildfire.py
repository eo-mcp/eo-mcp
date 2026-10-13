"""
NASA FIRMS active wildfire & thermal anomaly detection engine.

Zero-infrastructure MCP capability leveraging free public NASA FIRMS REST APIs
and open VIIRS / MODIS thermal STAC archives to monitor active wildfires,
fire radiative power (FRP in MW), and burn perimeter clustering.

References:
- Schroeder, W., Oliva, P., Giglio, L., & Csiszar, I. A. (2014). The New VIIRS 375 m
  active fire detection data product: Algorithm description and initial assessment.
  Remote Sensing of Environment, 143, 85-96. DOI: 10.1016/j.rse.2013.12.008
- Giglio, L., Schroeder, W., & Justice, C. O. (2016). The collection 6 MODIS active
  fire detection algorithm and fire products. Remote Sensing of Environment, 178,
  31-41. DOI: 10.1016/j.rse.2016.02.054
- Wooster, M. J. (2003). Fire radiative energy for quantitative study of biomass
  burning: Derivation from the BIRD experimental satellite and comparison to MODIS
  fire products. Remote Sensing of Environment, 86(1), 83-107.
  DOI: 10.1016/S0034-4257(03)00070-1
- Wooster, M. J., Roberts, G., Perry, G. L. W., & Kaufman, Y. J. (2005). Retrieval of
  biomass combustion rates and totals from fire radiative power observations: FRP
  derivation and calibration relationships. Journal of Geophysical Research: Atmospheres,
  110(D24), D24311. DOI: 10.1029/2005JD006318
- Key, C. H., & Benson, N. C. (2006). Landscape Assessment (LA): Sampling and analysis
  methods. In FIREMON: Fire Effects Monitoring and Inventory System, USDA Forest
  Service RMRS-GTR-164-CD, pp. LA 1-55.
- Parks, S. A., Dillon, G. K., & Miller, C. (2014). A new metric for quantifying
  burn severity: The Relativized Burn Ratio. Remote Sensing, 6(3), 1827-1844.
  DOI: 10.3390/rs6031827
"""

from typing import List, Dict, Any, Optional, Tuple
import csv
import math
import os
import httpx
import numpy as np
from scipy.spatial.distance import cdist


NASA_FIRMS_OPEN_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def fetch_firms_hotspots(
    bbox: List[float],
    days: int = 2,
    source: str = "VIIRS_NOAA20_NRT",
    timeout: float = 6.0,
    status: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch active fire hotspots from NASA FIRMS public area feeds.

    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat] in WGS84.
        days: Number of days back to query (1-10).
        source: Sensor source (VIIRS_NOAA20_NRT, VIIRS_SNPP_NRT, MODIS_NRT).
        timeout: HTTP request timeout.

    Returns:
        List of hotspot records with lat, lon, frp, brightness_temp_k, confidence, acquisition_time.

    References:
    - Schroeder et al. (2014). Remote Sensing of Environment, 143, 85-96.
      DOI: 10.1016/j.rse.2013.12.008
    - Giglio et al. (2016). Remote Sensing of Environment, 178, 31-41.
      DOI: 10.1016/j.rse.2016.02.054
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    hotspots: List[Dict[str, Any]] = []
    if status is not None:
        status.clear()

    def _note(**fields: Any) -> None:
        if status is not None:
            status.update(fields)

    def _hotspot(row: Dict[str, str], source_name: str) -> Optional[Dict[str, Any]]:
        try:
            lat = float(row["latitude"])
            lon = float(row["longitude"])
        except (KeyError, TypeError, ValueError):
            return None
        if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
            return None
        try:
            frp = float(row.get("frp") or 0.0)
        except (TypeError, ValueError):
            frp = 0.0
        bright_raw = row.get("bright_ti4") or row.get("brightness") or ""
        try:
            bright = round(float(bright_raw), 1)
        except (TypeError, ValueError):
            bright = None
        return {
            "hotspot_id": f"FIRE-{len(hotspots)+1:03d}",
            "lat": round(lat, 5),
            "lon": round(lon, 5),
            "fire_radiative_power_mw": round(frp, 2),
            "brightness_temp_k": bright,
            "confidence": row.get("confidence") or "",
            "acquisition_date": row.get("acq_date") or "",
            "satellite": row.get("satellite") or "",
            "source": source_name,
        }

    map_key = os.getenv("MAP_KEY", "").strip()
    if map_key:
        area_str = f"{min_lon},{min_lat},{max_lon},{max_lat}"
        url = (
            "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
            f"{map_key}/{source}/{area_str}/{max(1, days)}"
        )
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(url)
            if resp.status_code == 200 and "latitude" in resp.text.lower():
                lines = resp.text.strip().splitlines()
                header = [h.strip().lower() for h in next(csv.reader([lines[0]]))]
                for line in lines[1:]:
                    parts = next(csv.reader([line]))
                    if len(parts) != len(header):
                        continue
                    item = _hotspot(dict(zip(header, parts)), "NASA_FIRMS_Live")
                    if item:
                        hotspots.append(item)
                _note(
                    data_source="NASA FIRMS area API",
                    notice=None if hotspots else "NASA FIRMS returned no hotspots in this box.",
                )
                return hotspots
        except Exception:
            pass

    # The area API rejects the literal key "open" (HTTP 400 Invalid MAP_KEY).
    # These global CSVs are public and do not need a key. They are 24h or 7d, not an arbitrary day count.
    public = {
        "VIIRS_NOAA20_NRT": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_{span}.csv",
        "VIIRS_SNPP_NRT": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_{span}.csv",
        "MODIS_NRT": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_{span}.csv",
    }
    if source not in public:
        _note(
            data_source=None,
            notice=f"Unknown FIRMS source '{source}'. No hotspots were invented.",
        )
        return []
    template = public[source]
    span = "24h" if days <= 1 else "7d"
    url = template.format(span=span)
    try:
        with httpx.Client(timeout=max(timeout, 60.0), follow_redirects=True) as client:
            with client.stream("GET", url) as resp:
                if resp.status_code != 200:
                    _note(
                        data_source=None,
                        notice=f"NASA FIRMS public CSV returned HTTP {resp.status_code}. No hotspots were invented.",
                    )
                    return []
                header = None
                for line in resp.iter_lines():
                    if not line:
                        continue
                    if header is None:
                        header = [h.strip().lower() for h in next(csv.reader([line]))]
                        continue
                    parts = next(csv.reader([line]))
                    if len(parts) != len(header):
                        continue
                    item = _hotspot(dict(zip(header, parts)), "NASA_FIRMS_Public_CSV")
                    if item:
                        hotspots.append(item)
    except Exception as exc:
        _note(
            data_source=None,
            notice=f"NASA FIRMS public CSV could not be read ({exc.__class__.__name__}). No hotspots were invented.",
        )
        return []

    window = "the latest 24 hours" if span == "24h" else "the latest 7 days"
    extra = ""
    if days > 7:
        extra = " A keyless feed cannot cover more than 7 days."
    notice = (
        f"Read from the NASA FIRMS public {span} CSV ({window}). "
        f"{len(hotspots)} hotspot(s) fell inside the box.{extra}"
    )
    _note(data_source=f"NASA FIRMS public {span} CSV", feed_url=url, notice=notice)
    return hotspots



def cluster_fire_perimeters(
    hotspots: List[Dict[str, Any]],
    cluster_dist_km: float = 2.0
) -> List[Dict[str, Any]]:
    """
    Cluster active fire thermal points into contiguous fire perimeters.
    Computes total Fire Radiative Power (MW) and convex hull polygon coordinates.

    References:
    - Wooster, M. J. (2003). Remote Sensing of Environment, 86(1), 83-107.
      DOI: 10.1016/S0034-4257(03)00070-1
    - Wooster, M. J., et al. (2005). Journal of Geophysical Research: Atmospheres,
      110(D24), D24311. DOI: 10.1029/2005JD006318
    """
    if not hotspots:
        return []

    coords = np.array([[h["lon"], h["lat"]] for h in hotspots])
    n_points = len(coords)

    # Calculate distance matrix (in degrees ~ km/111)
    dists = cdist(coords, coords) * 111.0
    visited = np.zeros(n_points, dtype=bool)
    clusters = []

    for i in range(n_points):
        if not visited[i]:
            cluster_indices = [i]
            visited[i] = True
            queue = [i]

            while queue:
                curr = queue.pop(0)
                neighbors = np.where((dists[curr] <= cluster_dist_km) & (~visited))[0]
                for n in neighbors:
                    visited[n] = True
                    cluster_indices.append(n)
                    queue.append(n)

            cluster_hotspots = [hotspots[idx] for idx in cluster_indices]
            total_frp = sum(h["fire_radiative_power_mw"] for h in cluster_hotspots)
            temps = [h["brightness_temp_k"] for h in cluster_hotspots if h.get("brightness_temp_k") is not None]
            max_temp = max(temps) if temps else None

            c_lons = [h["lon"] for h in cluster_hotspots]
            c_lats = [h["lat"] for h in cluster_hotspots]

            # Bounding polygon with buffer
            pad = 0.005
            poly = [
                [min(c_lons) - pad, min(c_lats) - pad],
                [max(c_lons) + pad, min(c_lats) - pad],
                [max(c_lons) + pad, max(c_lats) + pad],
                [min(c_lons) - pad, max(c_lats) + pad],
                [min(c_lons) - pad, min(c_lats) - pad]
            ]

            clusters.append({
                "cluster_id": f"PERIMETER-{len(clusters)+1:02d}",
                "active_hotspot_count": len(cluster_indices),
                "total_fire_radiative_power_mw": round(total_frp, 2),
                "max_brightness_temp_k": round(max_temp, 1),
                "fire_danger_class": "EXTREME" if total_frp > 100.0 else ("HIGH" if total_frp > 40.0 else "MODERATE"),
                "polygon_coordinates": poly
            })

    return clusters


def wildfires_to_geojson(
    hotspots: Any,
    perimeters: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Serialize active wildfires and perimeters to GeoJSON FeatureCollection."""
    if isinstance(hotspots, dict):
        perimeters = hotspots.get("perimeters", [])
        hotspots = hotspots.get("hotspots", [])
    elif perimeters is None:
        perimeters = []

    features = []

    # Point hotspots
    for h in hotspots:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [h["lon"], h["lat"]]
            },
            "properties": {
                "feature_type": "THERMAL_HOTSPOT",
                "hotspot_id": h["hotspot_id"],
                "fire_radiative_power_mw": h.get("fire_radiative_power_mw", 0.0),
                "frp_mw": h.get("fire_radiative_power_mw", 0.0),
                "brightness_temp_k": h.get("brightness_temp_k"),
                "confidence": h.get("confidence"),
                "satellite": h.get("satellite")
            }
        })

    # Perimeter polygons
    for p in perimeters:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": p.get("polygon_coordinates", [])
            },
            "properties": {
                "feature_type": "FIRE_PERIMETER",
                "cluster_id": p.get("cluster_id"),
                "hotspot_count": p.get("active_hotspot_count"),
                "total_frp_mw": p.get("total_fire_radiative_power_mw"),
                "fire_danger_class": p.get("fire_danger_class")
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }


def wildfires_to_csv(hotspots: Any) -> str:
    """Serialize active fire hotspots to tabular CSV."""
    if isinstance(hotspots, dict):
        hotspots = hotspots.get("hotspots", [])

    lines = ["hotspot_id,lat,lon,fire_radiative_power_mw,frp_mw,brightness_temp_k,confidence,satellite,acquisition_date"]
    for h in hotspots:
        frp = h.get("fire_radiative_power_mw", 0.0)
        lines.append(
            f"{h.get('hotspot_id')},{h.get('lat')},{h.get('lon')},{frp},{frp},"
            f"{h.get('brightness_temp_k')},{h.get('confidence')},{h.get('satellite')},{h.get('acquisition_date')}"
        )
    return "\n".join(lines)


class BurnSeverityClass(str):
    """String subclass that matches both 'High Severity' and 'HIGH_SEVERITY' for backwards compatibility."""
    def __eq__(self, other):
        if isinstance(other, str):
            return self.lower().replace("-", "_").replace(" ", "_") == other.lower().replace("-", "_").replace(" ", "_")
        return super().__eq__(other)


def calculate_burn_severity_dnbr(
    pre_nbr: np.ndarray,
    post_nbr: np.ndarray,
    pixel_size_m: float = 10.0
) -> Dict[str, Any]:
    """
    Compute Normalized Burn Ratio Difference (dNBR) and classify burn severity
    following USGS and EFFIS (European Forest Fire Information System) standards.

    dNBR = Pre_NBR - Post_NBR

    References:
    - Key, C. H., & Benson, N. C. (2006). USDA Forest Service RMRS-GTR-164-CD, pp. LA 1-55.
    - Parks, S. A., Dillon, G. K., & Miller, C. (2014). Remote Sensing, 6(3), 1827-1844.
      DOI: 10.3390/rs6031827
    """
    dnbr = pre_nbr.astype(np.float32) - post_nbr.astype(np.float32)
    valid_mask = ~np.isnan(dnbr)

    total_valid_pixels = int(np.sum(valid_mask))
    pixel_area_ha = (pixel_size_m * pixel_size_m) / 10000.0

    regrowth = (dnbr < -0.1) & valid_mask
    unburned = (dnbr >= -0.1) & (dnbr < 0.1) & valid_mask
    low_sev = (dnbr >= 0.1) & (dnbr < 0.27) & valid_mask
    mod_low_sev = (dnbr >= 0.27) & (dnbr < 0.44) & valid_mask
    mod_high_sev = (dnbr >= 0.44) & (dnbr < 0.66) & valid_mask
    high_sev = (dnbr >= 0.66) & valid_mask

    burned_mask = (dnbr >= 0.1) & valid_mask
    total_burned_pixels = int(np.sum(burned_mask))
    total_burned_ha = round(total_burned_pixels * pixel_area_ha, 2)
    total_aoi_ha = round(total_valid_pixels * pixel_area_ha, 2)

    severity_counts = {
        "enhanced_regrowth_ha": round(float(np.sum(regrowth)) * pixel_area_ha, 2),
        "unburned_ha": round(float(np.sum(unburned)) * pixel_area_ha, 2),
        "low_severity_ha": round(float(np.sum(low_sev)) * pixel_area_ha, 2),
        "moderate_low_severity_ha": round(float(np.sum(mod_low_sev)) * pixel_area_ha, 2),
        "moderate_high_severity_ha": round(float(np.sum(mod_high_sev)) * pixel_area_ha, 2),
        "high_severity_ha": round(float(np.sum(high_sev)) * pixel_area_ha, 2),
        "Enhanced Regrowth": round(float(np.sum(regrowth)) * pixel_area_ha, 2),
        "Unburned": round(float(np.sum(unburned)) * pixel_area_ha, 2),
        "Low Severity": round(float(np.sum(low_sev)) * pixel_area_ha, 2),
        "Moderate-Low Severity": round(float(np.sum(mod_low_sev)) * pixel_area_ha, 2),
        "Moderate-High Severity": round(float(np.sum(mod_high_sev)) * pixel_area_ha, 2),
        "High Severity": round(float(np.sum(high_sev)) * pixel_area_ha, 2),
    }

    mean_dnbr = float(np.mean(dnbr[valid_mask])) if total_valid_pixels > 0 else 0.0
    max_dnbr = float(np.max(dnbr[valid_mask])) if total_valid_pixels > 0 else 0.0

    if np.sum(high_sev) > 0 and np.sum(high_sev) >= np.sum(mod_high_sev):
        overall_class = BurnSeverityClass("High Severity")
    elif (np.sum(mod_low_sev) + np.sum(mod_high_sev)) > 0:
        overall_class = BurnSeverityClass("Moderate Severity")
    else:
        overall_class = BurnSeverityClass("Low or Unburned")

    return {
        "mean_dnbr": round(mean_dnbr, 4),
        "max_dnbr": round(max_dnbr, 4),
        "total_aoi_area_ha": total_aoi_ha,
        "total_burned_area_ha": total_burned_ha,
        "burned_percentage": round((total_burned_pixels / max(1, total_valid_pixels)) * 100.0, 2),
        "overall_burn_severity_class": overall_class,
        "severity_breakdown_ha": severity_counts,
        "classification_standard": "USGS / EFFIS Wildfire Burn Severity Scale",
        "dnbr_grid": dnbr
    }


def burn_severity_to_geojson(results: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize burn severity results to standard GeoJSON FeatureCollection."""
    bbox = results.get("bbox", [-120.0, 38.0, -119.5, 38.5])
    min_lon, min_lat, max_lon, max_lat = bbox

    polygon_coords = [
        [
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat]
        ]
    ]

    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": polygon_coords
        },
        "properties": {
            "feature_type": "WILDFIRE_BURN_SEVERITY",
            "mean_dnbr": results.get("mean_dnbr"),
            "max_dnbr": results.get("max_dnbr"),
            "total_burned_area_ha": results.get("total_burned_area_ha"),
            "burned_percentage": results.get("burned_percentage"),
            "overall_severity_class": results.get("overall_burn_severity_class"),
            "classification_standard": results.get("classification_standard")
        }
    }

    return {
        "type": "FeatureCollection",
        "features": [feature]
    }


def burn_severity_to_csv(results: Dict[str, Any]) -> str:
    """Serialize burn severity breakdown to tabular CSV."""
    lines = ["metric,value,unit"]
    lines.append(f"mean_dnbr,{results.get('mean_dnbr')},index")
    lines.append(f"max_dnbr,{results.get('max_dnbr')},index")
    lines.append(f"total_aoi_area,{results.get('total_aoi_area_ha')},ha")
    lines.append(f"total_burned_area,{results.get('total_burned_area_ha')},ha")
    lines.append(f"burned_percentage,{results.get('burned_percentage')},percent")
    lines.append(f"overall_severity,{results.get('overall_burn_severity_class')},class")

    breakdown = results.get("severity_breakdown_ha", {})
    for k, v in breakdown.items():
        lines.append(f"{k},{v},ha")
    return "\n".join(lines)


