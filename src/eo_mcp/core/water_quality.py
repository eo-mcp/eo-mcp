"""
Coastal Water Quality, Eutrophication & Marine Pollution Assessment Engine.

Computes Normalized Difference Chlorophyll Index (NDCI) for harmful algal bloom (HAB)
and chlorophyll-a concentration tracking, Normalized Difference Turbidity Index (NDTI)
for sediment runoff and water clarity, Suspended Particulate Matter (SPM / TSS) proxies,
and Sea Surface Temperature (SST) thermal plume anomaly detection conforming to the
EU Water Framework Directive (2000/60/EC) and Marine Strategy Framework Directive (2008/56/EC).

References:
- Mishra, S., & Mishra, D. R. (2012). Normalized difference chlorophyll index: A novel model
  for remote estimation of chlorophyll-a in turbid productive waters. Remote Sensing of Environment,
  117, 394-406. DOI: 10.1016/j.rse.2011.10.016
- Lacaux, J. P., Tourre, Y. M., Vignolles, C., Ndione, J. A., & Lafaye, M. (2007). Classification
  of ponds using high-spatial resolution SPOT 5 satellite imagery in the Ferlo (Senegal) to predict
  the risk of Rift Valley fever. Remote Sensing of Environment, 106(1), 66-74.
  DOI: 10.1016/j.rse.2006.07.012
- Nechad, B., Dogliotti, A. I., Ruddick, K. G., & Doxaran, D. (2010). Calibration and validation
  of a generic single-band algorithm for mapping total suspended matter in turbid waters.
  Remote Sensing of Environment, 114(4), 854-866. DOI: 10.1016/j.rse.2009.11.022
- European Commission (2000). Directive 2000/60/EC of the European Parliament and of the Council
  establishing a framework for Community action in the field of water policy (Water Framework Directive).
"""

from typing import Tuple, Dict, Any, List, Optional
import numpy as np
from scipy.ndimage import label


def compute_ndci(red_edge: np.ndarray, red: np.ndarray) -> np.ndarray:
    """
    Calculate Normalized Difference Chlorophyll Index (NDCI):
    NDCI = (RedEdge - Red) / (RedEdge + Red)
    For Sentinel-2 MSI: RedEdge = Band 5 (~705 nm), Red = Band 4 (~665 nm).

    References:
    - Mishra, S., & Mishra, D. R. (2012). Remote Sensing of Environment, 117, 394-406.
      DOI: 10.1016/j.rse.2011.10.016
    """
    re_f = red_edge.astype(np.float32)
    r_f = red.astype(np.float32)
    denom = re_f + r_f
    denom = np.where(denom == 0, 1e-6, denom)
    ndci = (re_f - r_f) / denom
    return np.clip(ndci, -1.0, 1.0)


def classify_ndci_trophic_state(ndci: np.ndarray, water_mask: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Classify NDCI into standard aquatic trophic states & HAB risk levels:
    0: Oligotrophic (NDCI < -0.10) - Clear, low nutrient waters
    1: Mesotrophic (-0.10 <= NDCI < 0.10) - Moderate biological productivity
    2: Eutrophic (0.10 <= NDCI < 0.20) - High nutrient, elevated algal biomass
    3: Hypertrophic / HAB Risk (NDCI >= 0.20) - Extreme chlorophyll, harmful algal bloom warning

    Returns:
        (classified_array, percentage_breakdown)
    """
    mask = water_mask if water_mask is not None else ~np.isnan(ndci)
    valid_pixels = np.count_nonzero(mask)

    classified = np.full(ndci.shape, -1, dtype=np.int8)
    if valid_pixels == 0:
        return classified, {"oligotrophic_pct": 0.0, "mesotrophic_pct": 0.0, "eutrophic_pct": 0.0, "hypertrophic_hab_pct": 0.0}

    c0 = mask & (ndci < -0.10)
    c1 = mask & (ndci >= -0.10) & (ndci < 0.10)
    c2 = mask & (ndci >= 0.10) & (ndci < 0.20)
    c3 = mask & (ndci >= 0.20)

    classified[c0] = 0
    classified[c1] = 1
    classified[c2] = 2
    classified[c3] = 3

    breakdown = {
        "oligotrophic_pct": round(float(np.count_nonzero(c0) / valid_pixels * 100.0), 2),
        "mesotrophic_pct": round(float(np.count_nonzero(c1) / valid_pixels * 100.0), 2),
        "eutrophic_pct": round(float(np.count_nonzero(c2) / valid_pixels * 100.0), 2),
        "hypertrophic_hab_pct": round(float(np.count_nonzero(c3) / valid_pixels * 100.0), 2),
    }
    return classified, breakdown


def compute_ndti(red: np.ndarray, green: np.ndarray) -> np.ndarray:
    """
    Calculate Normalized Difference Turbidity Index (NDTI):
    NDTI = (Red - Green) / (Red + Green)
    For Sentinel-2 MSI: Red = Band 4 (~665 nm), Green = Band 3 (~560 nm).

    References:
    - Lacaux, J. P., et al. (2007). Remote Sensing of Environment, 106(1), 66-74.
      DOI: 10.1016/j.rse.2006.07.012
    """
    r_f = red.astype(np.float32)
    g_f = green.astype(np.float32)
    denom = r_f + g_f
    denom = np.where(denom == 0, 1e-6, denom)
    ndti = (r_f - g_f) / denom
    return np.clip(ndti, -1.0, 1.0)


def classify_ndti_turbidity(ndti: np.ndarray, water_mask: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Classify NDTI into aquatic turbidity & sedimentation regimes:
    0: Clear Water (NDTI < -0.05)
    1: Low Turbidity (-0.05 <= NDTI < 0.05)
    2: Moderate Turbidity (0.05 <= NDTI < 0.20)
    3: High Turbidity / Sediment Plume (NDTI >= 0.20)

    Returns:
        (classified_array, percentage_breakdown)
    """
    mask = water_mask if water_mask is not None else ~np.isnan(ndti)
    valid_pixels = np.count_nonzero(mask)

    classified = np.full(ndti.shape, -1, dtype=np.int8)
    if valid_pixels == 0:
        return classified, {"clear_pct": 0.0, "low_turbidity_pct": 0.0, "moderate_turbidity_pct": 0.0, "high_turbidity_pct": 0.0}

    c0 = mask & (ndti < -0.05)
    c1 = mask & (ndti >= -0.05) & (ndti < 0.05)
    c2 = mask & (ndti >= 0.05) & (ndti < 0.20)
    c3 = mask & (ndti >= 0.20)

    classified[c0] = 0
    classified[c1] = 1
    classified[c2] = 2
    classified[c3] = 3

    breakdown = {
        "clear_pct": round(float(np.count_nonzero(c0) / valid_pixels * 100.0), 2),
        "low_turbidity_pct": round(float(np.count_nonzero(c1) / valid_pixels * 100.0), 2),
        "moderate_turbidity_pct": round(float(np.count_nonzero(c2) / valid_pixels * 100.0), 2),
        "high_turbidity_pct": round(float(np.count_nonzero(c3) / valid_pixels * 100.0), 2),
    }
    return classified, breakdown


def estimate_spm_nechad(red_reflectance: np.ndarray, a: float = 362.1, c: float = 0.174) -> np.ndarray:
    """
    Estimate Suspended Particulate Matter (SPM / TSS in mg/L) using the Nechad single-band model.
    SPM = A * rho_red / (1 - rho_red / C)
    Where for Sentinel-2 Band 4 (Red): A = 362.1 mg/L, C = 0.174.

    References:
    - Nechad, B., et al. (2010). Remote Sensing of Environment, 114(4), 854-866.
      DOI: 10.1016/j.rse.2009.11.022
    """
    rho = np.clip(red_reflectance.astype(np.float32), 0.0, 0.9 * c)
    spm = (a * rho) / (1.0 - (rho / c))
    return np.maximum(spm, 0.0)


def detect_thermal_plume_anomalies(
    sst: np.ndarray,
    water_mask: Optional[np.ndarray] = None,
    delta_t_threshold_celsius: float = 1.5,
    cellsize_m: float = 30.0
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Detect thermal plume anomalies (e.g. power plant cooling effluent, industrial runoff)
    relative to the local ambient water temperature background.

    Args:
        sst: Sea Surface Temperature in Celsius (°C).
        water_mask: Optional boolean mask of water pixels.
        delta_t_threshold_celsius: Temperature anomaly threshold (°C above ambient). Default 1.5°C.
        cellsize_m: Spatial resolution in meters.

    Returns:
        (binary_anomaly_mask, thermal_metrics)
    """
    mask = water_mask if water_mask is not None else ~np.isnan(sst)
    valid_sst = sst[mask]

    if len(valid_sst) == 0:
        return np.zeros_like(sst, dtype=bool), {
            "ambient_sst_celsius": None,
            "max_sst_celsius": None,
            "max_delta_t_celsius": 0.0,
            "thermal_plume_detected": False,
            "plume_area_km2": 0.0,
            "plume_hotspots_count": 0
        }

    ambient_temp = float(np.median(valid_sst))
    delta_t = np.where(mask, sst - ambient_temp, 0.0)
    anomaly_mask = mask & (delta_t >= delta_t_threshold_celsius)

    labeled_plumes, num_hotspots = label(anomaly_mask)
    plume_pixel_count = int(np.count_nonzero(anomaly_mask))
    plume_area_km2 = round(plume_pixel_count * (cellsize_m ** 2) / 1e6, 4)

    max_delta_t = round(float(np.max(delta_t[mask])) if len(delta_t[mask]) > 0 else 0.0, 2)
    max_sst = round(float(np.max(valid_sst)), 2)

    metrics = {
        "ambient_sst_celsius": round(ambient_temp, 2),
        "max_sst_celsius": max_sst,
        "max_delta_t_celsius": max_delta_t,
        "thermal_plume_detected": bool(num_hotspots > 0 and plume_pixel_count >= 3),
        "plume_area_km2": plume_area_km2,
        "plume_hotspots_count": int(num_hotspots)
    }
    return anomaly_mask, metrics


def analyze_coastal_water_quality(
    green: np.ndarray,
    red: np.ndarray,
    red_edge: np.ndarray,
    sst: Optional[np.ndarray] = None,
    water_mask: Optional[np.ndarray] = None,
    cellsize_m: float = 10.0,
    bbox: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Comprehensive multi-parameter coastal water quality analysis engine.
    Integrates NDCI (chlorophyll-a), NDTI (turbidity), SPM (sediment load), and thermal plume anomalies.

    Args:
        green: Sentinel-2 Band 3 (Green, ~560 nm).
        red: Sentinel-2 Band 4 (Red, ~665 nm).
        red_edge: Sentinel-2 Band 5 (Red Edge 1, ~705 nm).
        sst: Optional Sea Surface Temperature array in Celsius.
        water_mask: Optional boolean water mask. If None, derived from valid finite values.
        cellsize_m: Spatial resolution in meters (default 10m for Sentinel-2).
        bbox: Optional [min_lon, min_lat, max_lon, max_lat] coordinates.

    Returns:
        Structured dictionary containing water quality metrics, trophic states, and hazard flags.
    """
    if water_mask is None:
        water_mask = np.isfinite(green) & np.isfinite(red) & np.isfinite(red_edge)

    valid_count = int(np.count_nonzero(water_mask))
    water_area_km2 = round(valid_count * (cellsize_m ** 2) / 1e6, 4)

    # 1. Chlorophyll-a / NDCI
    ndci = compute_ndci(red_edge, red)
    ndci_valid = ndci[water_mask]
    classified_trophic, trophic_breakdown = classify_ndci_trophic_state(ndci, water_mask)

    mean_ndci = round(float(np.mean(ndci_valid)), 4) if len(ndci_valid) > 0 else 0.0
    max_ndci = round(float(np.max(ndci_valid)), 4) if len(ndci_valid) > 0 else 0.0
    std_ndci = round(float(np.std(ndci_valid)), 4) if len(ndci_valid) > 0 else 0.0

    # Determine Harmful Algal Bloom (HAB) Alert Level
    hab_pct = trophic_breakdown["hypertrophic_hab_pct"]
    eutrophic_pct = trophic_breakdown["eutrophic_pct"]
    if hab_pct > 15.0 or (hab_pct > 5.0 and max_ndci > 0.35):
        hab_alert_level = "CRITICAL"
    elif hab_pct > 5.0 or eutrophic_pct > 30.0:
        hab_alert_level = "ELEVATED"
    elif eutrophic_pct > 10.0:
        hab_alert_level = "MODERATE"
    else:
        hab_alert_level = "LOW"

    # 2. Turbidity / NDTI
    ndti = compute_ndti(red, green)
    ndti_valid = ndti[water_mask]
    classified_turbidity, turbidity_breakdown = classify_ndti_turbidity(ndti, water_mask)

    mean_ndti = round(float(np.mean(ndti_valid)), 4) if len(ndti_valid) > 0 else 0.0
    max_ndti = round(float(np.max(ndti_valid)), 4) if len(ndti_valid) > 0 else 0.0

    # 3. Suspended Particulate Matter (SPM) Proxy
    spm = estimate_spm_nechad(red)
    spm_valid = spm[water_mask]
    mean_spm = round(float(np.mean(spm_valid)), 2) if len(spm_valid) > 0 else 0.0
    max_spm = round(float(np.max(spm_valid)), 2) if len(spm_valid) > 0 else 0.0

    # 4. Thermal Plume Anomaly Detection
    thermal_metrics = {
        "thermal_plume_detected": False,
        "max_delta_t_celsius": 0.0,
        "plume_area_km2": 0.0,
        "plume_hotspots_count": 0
    }
    if sst is not None:
        _, thermal_metrics = detect_thermal_plume_anomalies(sst, water_mask, cellsize_m=cellsize_m)

    # Compile integrated result
    result = {
        "summary": {
            "water_surface_area_km2": water_area_km2,
            "valid_water_pixels": valid_count,
            "hab_alert_level": hab_alert_level,
            "primary_trophic_state": max(trophic_breakdown, key=trophic_breakdown.get).replace("_pct", "").upper(),
            "primary_turbidity_class": max(turbidity_breakdown, key=turbidity_breakdown.get).replace("_pct", "").upper()
        },
        "chlorophyll_ndci": {
            "mean": mean_ndci,
            "max": max_ndci,
            "std": std_ndci,
            "trophic_classification": trophic_breakdown,
            "hab_risk_percentage": hab_pct
        },
        "turbidity_ndti": {
            "mean": mean_ndti,
            "max": max_ndti,
            "classification": turbidity_breakdown
        },
        "suspended_solids_spm": {
            "mean_mg_l": mean_spm,
            "max_mg_l": max_spm,
            "algorithm": "Nechad single-band red reflectance (2010)"
        },
        "thermal_plume": thermal_metrics,
        "bbox": bbox
    }
    return result


def water_quality_to_geojson(results: Dict[str, Any], bbox: Optional[List[float]] = None) -> Dict[str, Any]:
    """
    Serialize water quality results to an RFC 7946 compliant GeoJSON FeatureCollection.
    """
    effective_bbox = bbox or results.get("bbox") or [0.0, 0.0, 0.0, 0.0]
    min_lon, min_lat, max_lon, max_lat = effective_bbox
    center_lon = (min_lon + max_lon) / 2.0
    center_lat = (min_lat + max_lat) / 2.0

    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [min_lon, min_lat],
                    [max_lon, min_lat],
                    [max_lon, max_lat],
                    [min_lon, max_lat],
                    [min_lon, min_lat]
                ]]
            },
            "properties": {
                "feature_type": "water_quality_aoi_summary",
                "water_area_km2": results["summary"]["water_surface_area_km2"],
                "hab_alert_level": results["summary"]["hab_alert_level"],
                "mean_ndci": results["chlorophyll_ndci"]["mean"],
                "max_ndci": results["chlorophyll_ndci"]["max"],
                "hab_risk_pct": results["chlorophyll_ndci"]["hab_risk_percentage"],
                "mean_ndti": results["turbidity_ndti"]["mean"],
                "mean_spm_mg_l": results["suspended_solids_spm"]["mean_mg_l"],
                "thermal_plume_detected": results["thermal_plume"]["thermal_plume_detected"],
                "max_delta_t_celsius": results["thermal_plume"]["max_delta_t_celsius"]
            }
        },
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [center_lon, center_lat]
            },
            "properties": {
                "feature_type": "water_quality_centroid_marker",
                "hab_alert": results["summary"]["hab_alert_level"],
                "trophic_state": results["summary"]["primary_trophic_state"],
                "turbidity_class": results["summary"]["primary_turbidity_class"]
            }
        }
    ]

    return {
        "type": "FeatureCollection",
        "features": features
    }


def water_quality_to_csv(results: Dict[str, Any]) -> str:
    """
    Format water quality results as a standard tabular CSV string.
    """
    lines = [
        "parameter,value,unit,interpretation",
        f"water_area_km2,{results['summary']['water_surface_area_km2']},km2,Analyzed water surface",
        f"hab_alert_level,{results['summary']['hab_alert_level']},severity,Harmful algal bloom status",
        f"mean_ndci,{results['chlorophyll_ndci']['mean']},index,Mean Normalized Difference Chlorophyll Index",
        f"max_ndci,{results['chlorophyll_ndci']['max']},index,Peak Chlorophyll Index",
        f"hab_risk_pct,{results['chlorophyll_ndci']['hab_risk_percentage']},%,Area exceeding HAB threshold",
        f"oligotrophic_pct,{results['chlorophyll_ndci']['trophic_classification']['oligotrophic_pct']},%,Low biological productivity",
        f"mesotrophic_pct,{results['chlorophyll_ndci']['trophic_classification']['mesotrophic_pct']},%,Moderate productivity",
        f"eutrophic_pct,{results['chlorophyll_ndci']['trophic_classification']['eutrophic_pct']},%,Elevated nutrient loading",
        f"hypertrophic_hab_pct,{results['chlorophyll_ndci']['trophic_classification']['hypertrophic_hab_pct']},%,Severe algal proliferation",
        f"mean_ndti,{results['turbidity_ndti']['mean']},index,Mean Normalized Difference Turbidity Index",
        f"mean_spm_mg_l,{results['suspended_solids_spm']['mean_mg_l']},mg/L,Mean Suspended Particulate Matter",
        f"max_spm_mg_l,{results['suspended_solids_spm']['max_mg_l']},mg/L,Peak Suspended Particulate Matter",
        f"thermal_plume_detected,{results['thermal_plume']['thermal_plume_detected']},bool,Coastal thermal discharge presence",
        f"max_delta_t_celsius,{results['thermal_plume']['max_delta_t_celsius']},deg_C,Maximum thermal elevation above ambient",
        f"plume_area_km2,{results['thermal_plume']['plume_area_km2']},km2,Surface thermal plume area"
    ]
    return "\n".join(lines)
