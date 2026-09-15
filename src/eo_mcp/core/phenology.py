"""
Vegetation Phenology and Agricultural Crop Dynamics Engine.

Models multi-temporal vegetation trajectories (NDVI/EVI time-series) to extract
key agro-climatic phenological milestones: Start of Season (SOS), Peak of Season (POS),
End of Season (EOS), Length of Season (LOS), and crop vigor anomalies.

References:
- Reed, B. C., Brown, J. F., VanderZee, D., Loveland, T. R., Merchant, J. W., &
  Ohlen, D. O. (1994). Measuring phenological variability from satellite imagery.
  Journal of Vegetation Science, 5(5), 703-714. DOI: 10.2307/3235884
- Zhang, X., et al. (2003). Monitoring vegetation phenology using MODIS. Remote
  Sensing of Environment, 84(3), 471-475. DOI: 10.1016/S0034-4257(02)00135-9
- Jönsson, P., & Eklundh, L. (2004). TIMESAT—A program for analyzing time-series
  of satellite sensor data. Computers & Geosciences, 30(8), 833-845.
  DOI: 10.1016/j.cageo.2004.05.006
"""

from typing import Dict, Any, List, Optional
import numpy as np


def analyze_crop_phenology_trajectory(
    observations: List[Dict[str, Any]],
    year: int = 2024,
    reference_peak_ndvi: float = 0.75
) -> Dict[str, Any]:
    """
    Extract phenological metrics from an ordered sequence of multi-temporal observations.

    Args:
        observations: List of dicts with 'date' (YYYY-MM-DD) and 'ndvi' (float).
        year: Year under evaluation.
        reference_peak_ndvi: Regional benchmark peak NDVI for healthy crop baseline.

    Returns:
        Phenological milestones, seasonal metrics, and crop vigor anomaly.

    References:
    - Reed, B. C., et al. (1994). Journal of Vegetation Science, 5(5), 703-714.
      DOI: 10.2307/3235884
    - Zhang, X., et al. (2003). Remote Sensing of Environment, 84(3), 471-475.
      DOI: 10.1016/S0034-4257(02)00135-9
    - Jönsson, P., & Eklundh, L. (2004). Computers & Geosciences, 30(8), 833-845.
      DOI: 10.1016/j.cageo.2004.05.006
    """
    if not observations:
        return {"error": "No temporal observations provided."}

    # Sort observations chronologically
    sorted_obs = sorted(observations, key=lambda x: x.get("date", ""))
    dates = [o.get("date", "") for o in sorted_obs]
    ndvis = np.array([float(o.get("ndvi", 0.0)) for o in sorted_obs], dtype=np.float32)

    min_ndvi = float(np.min(ndvis))
    max_ndvi = float(np.max(ndvis))
    amplitude = max_ndvi - min_ndvi

    # Peak of Season (POS)
    pos_idx = int(np.argmax(ndvis))
    pos_date = dates[pos_idx]
    peak_ndvi = max_ndvi

    # Threshold for SOS and EOS: 20% of seasonal amplitude
    threshold = min_ndvi + (0.20 * amplitude)

    # Start of Season (SOS): first date before POS where NDVI crosses threshold
    sos_date = dates[0]
    for i in range(pos_idx):
        if ndvis[i] >= threshold:
            sos_date = dates[i]
            break

    # End of Season (EOS): first date after POS where NDVI drops below threshold
    eos_date = dates[-1]
    for i in range(pos_idx, len(ndvis)):
        if ndvis[i] <= threshold:
            eos_date = dates[i]
            break

    # Crop vigor anomaly vs reference benchmark
    vigor_anomaly_pct = round(((peak_ndvi - reference_peak_ndvi) / max(0.1, reference_peak_ndvi)) * 100.0, 2)
    
    # Seasonal integrated NDVI (proxy for total biomass)
    seasonal_integral = round(float(np.sum(ndvis)), 3)

    if vigor_anomaly_pct >= 10.0:
        health_status = "ABOVE_AVERAGE_VIGOR"
    elif vigor_anomaly_pct >= -10.0:
        health_status = "NORMAL_HEALTHY"
    elif vigor_anomaly_pct >= -25.0:
        health_status = "MODERATE_STRESS_OR_DROUGHT"
    else:
        health_status = "SEVERE_CROP_DEFICIT"

    return {
        "year": year,
        "observations_count": len(sorted_obs),
        "phenology_milestones": {
            "start_of_season_sos": sos_date,
            "peak_of_season_pos": pos_date,
            "end_of_season_eos": eos_date,
            "peak_ndvi": round(peak_ndvi, 3),
            "baseline_ndvi": round(min_ndvi, 3),
            "seasonal_amplitude": round(amplitude, 3),
            "integrated_biomass_proxy": seasonal_integral
        },
        "crop_health_assessment": {
            "reference_benchmark_ndvi": reference_peak_ndvi,
            "vigor_anomaly_percentage": vigor_anomaly_pct,
            "status": health_status
        },
        "temporal_series": sorted_obs
    }


def phenology_to_geojson(results: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize phenology results to GeoJSON FeatureCollection."""
    bbox = results.get("bbox", [-4.5, 37.5, -4.0, 38.0])
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

    miles = results.get("phenology_milestones", {})
    health = results.get("crop_health_assessment", {})

    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": polygon_coords
        },
        "properties": {
            "feature_type": "CROP_PHENOLOGY_MONITORING",
            "year": results.get("year"),
            "sos_date": miles.get("start_of_season_sos"),
            "pos_date": miles.get("peak_of_season_pos"),
            "eos_date": miles.get("end_of_season_eos"),
            "peak_ndvi": miles.get("peak_ndvi"),
            "vigor_anomaly_pct": health.get("vigor_anomaly_percentage"),
            "crop_status": health.get("status")
        }
    }

    return {
        "type": "FeatureCollection",
        "features": [feature]
    }


def phenology_to_csv(results: Dict[str, Any]) -> str:
    """Serialize phenology series to tabular CSV."""
    lines = ["date,ndvi"]
    series = results.get("temporal_series", [])
    for s in series:
        lines.append(f"{s.get('date')},{s.get('ndvi')}")
    return "\n".join(lines)
