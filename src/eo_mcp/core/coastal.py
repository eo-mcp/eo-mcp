"""Coastal dynamics, shoreline extraction, and multi-temporal erosion analysis engine.

Computes MNDWI waterlines from multi-temporal optical satellite bands (Sentinel-2 / Landsat)
and calculates perpendicular baseline transect End Point Rates (EPR in m/year) to assess
coastal shoreline retreat and erosion hazards aligned with the EU Climate Adaptation Strategy.
"""

from typing import Tuple, Dict, Any, List, Optional
import numpy as np
from scipy.ndimage import binary_erosion, binary_dilation


def compute_mndwi(green: np.ndarray, swir: np.ndarray) -> np.ndarray:
    """
    Calculate Modified Normalized Difference Water Index (MNDWI):
    MNDWI = (Green - SWIR) / (Green + SWIR)
    MNDWI suppresses built-up land noise and enhances water boundaries better than NDWI.
    """
    green_f = green.astype(np.float32)
    swir_f = swir.astype(np.float32)
    denom = green_f + swir_f
    denom = np.where(denom == 0, 1e-6, denom)
    mndwi = (green_f - swir_f) / denom
    return np.clip(mndwi, -1.0, 1.0)


def extract_water_mask_otsu(water_index: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Automated bimodal Otsu thresholding to segment water from land on a spectral index array.

    Returns:
        (binary_water_mask, optimal_threshold)
    """
    valid = water_index[~np.isnan(water_index)]
    if len(valid) == 0:
        return np.zeros_like(water_index, dtype=bool), 0.0

    # Scale to 0-255 for standard Otsu histogram
    scaled = np.clip((valid + 1.0) * 127.5, 0, 255).astype(np.uint8)
    hist, bin_edges = np.histogram(scaled, bins=256, range=(0, 256))
    total = len(scaled)

    current_max = 0.0
    threshold = 0
    sum_total = np.dot(np.arange(256), hist)
    sum_b = 0.0
    weight_b = 0

    for i in range(256):
        weight_b += hist[i]
        if weight_b == 0:
            continue
        weight_f = total - weight_b
        if weight_f == 0:
            break

        sum_b += i * hist[i]
        mean_b = sum_b / weight_b
        mean_f = (sum_total - sum_b) / weight_f

        # Between-class variance
        var_between = weight_b * weight_f * ((mean_b - mean_f) ** 2)
        if var_between > current_max:
            current_max = var_between
            threshold = i

    otsu_val = (threshold / 127.5) - 1.0
    # Water has positive MNDWI values, default threshold around 0.0
    refined_threshold = max(-0.15, min(0.15, float(otsu_val)))
    water_mask = (water_index > refined_threshold) & (~np.isnan(water_index))
    return water_mask, refined_threshold


def extract_shoreline_boundary(water_mask: np.ndarray) -> np.ndarray:
    """
    Extract the 1-pixel wide instantaneous waterline boundary separating open water from land.
    Uses morphological boundary detection (water XOR eroded_water) preserving raster borders.
    """
    eroded = binary_erosion(water_mask, border_value=True)
    shoreline_mask = water_mask ^ eroded
    return shoreline_mask


def compute_transect_erosion_rates(
    hist_water_mask: np.ndarray,
    recent_water_mask: np.ndarray,
    time_delta_years: float,
    pixel_size_m: float = 10.0,
    transect_sample_step: int = 5
) -> Dict[str, Any]:
    """
    Casts alongshore cross-sections to compute End Point Rate (EPR) and Net Shoreline Movement (NSM).
    Consistent with the USGS DSAS (Digital Shoreline Analysis System) coastal methodology.

    Convention:
        Negative NSM/EPR = Landward retreat (Coastal Erosion / Land Loss)
        Positive NSM/EPR = Seaward advance (Accretion / Land Gain)

    Args:
        hist_water_mask: 2D boolean array (True for water) at historical date.
        recent_water_mask: 2D boolean array at modern date.
        time_delta_years: Elapsed time in decimal years between the two acquisitions.
        pixel_size_m: Ground resolution in meters (e.g. 10m for Sentinel-2, 30m for Landsat).
        transect_sample_step: Interval in pixels between transects.

    Returns:
        Dictionary containing transect results, EPR rates, and hazard classifications.
    """
    n_rows, n_cols = hist_water_mask.shape
    transects = []
    
    # Cast horizontal transects across columns for each sampled row
    sample_rows = range(0, n_rows, max(1, transect_sample_step))

    for r in sample_rows:
        hist_water_line = hist_water_mask[r, :]
        recent_water_line = recent_water_mask[r, :]

        # Find water/land transition column
        hist_transitions = np.where(hist_water_line[:-1] != hist_water_line[1:])[0]
        recent_transitions = np.where(recent_water_line[:-1] != recent_water_line[1:])[0]

        if len(hist_transitions) > 0 and len(recent_transitions) > 0:
            hist_col = float(hist_transitions[0])
            recent_col = float(recent_transitions[0])

            # Shoreline displacement:
            # If recent_col > hist_col (water advanced right into land), shoreline retreated -> erosion (negative)
            delta_pixels = hist_col - recent_col
            nsm_meters = delta_pixels * pixel_size_m
            epr_m_per_year = nsm_meters / max(0.1, time_delta_years)

            if epr_m_per_year < -2.0:
                hazard = "CRITICAL_EROSION"
            elif epr_m_per_year < -0.5:
                hazard = "MODERATE_EROSION"
            elif epr_m_per_year <= 0.5:
                hazard = "STABLE"
            else:
                hazard = "ACCRETION"

            transects.append({
                "transect_id": f"TR-{len(transects)+1:03d}",
                "row_index": r,
                "historical_col": round(hist_col, 1),
                "recent_col": round(recent_col, 1),
                "net_shoreline_movement_m": round(nsm_meters, 2),
                "end_point_rate_m_per_year": round(epr_m_per_year, 2),
                "hazard_class": hazard
            })

    if not transects:
        return {
            "time_delta_years": round(time_delta_years, 2),
            "transects_evaluated": 0,
            "mean_erosion_rate_m_yr": 0.0,
            "max_erosion_rate_m_yr": 0.0,
            "eroding_percentage": 0.0,
            "overall_status": "NO_COASTAL_BOUNDARY_DETECTED",
            "transects": []
        }

    eprs = [t["end_point_rate_m_per_year"] for t in transects]
    eroding_count = sum(1 for e in eprs if e < -0.5)
    accreting_count = sum(1 for e in eprs if e > 0.5)
    stable_count = len(eprs) - eroding_count - accreting_count

    mean_epr = float(np.mean(eprs))
    max_erosion = float(np.min(eprs)) if np.min(eprs) < 0 else 0.0

    return {
        "time_delta_years": round(time_delta_years, 2),
        "transects_evaluated": len(transects),
        "mean_erosion_rate_m_yr": round(mean_epr, 2),
        "mean_end_point_rate_m_yr": round(mean_epr, 2),
        "max_erosion_rate_m_yr": round(max_erosion, 2),
        "eroding_transects_count": eroding_count,
        "accreting_transects_count": accreting_count,
        "stable_transects_count": stable_count,
        "eroding_percentage": round((eroding_count / len(transects)) * 100.0, 1),
        "overall_status": "EROSIONAL" if mean_epr < -0.5 else ("ACCRETIONAL" if mean_epr > 0.5 else "DYNAMICALLY_STABLE"),
        "transects": transects,
        "sample_transects": transects[:25]
    }


def transects_to_geojson(
    results: Dict[str, Any],
    bbox: Optional[List[float]] = None,
    raster_shape: Optional[Tuple[int, int]] = None
) -> Dict[str, Any]:
    """Serialize coastal transects to GeoJSON LineString FeatureCollection for GIS visualization."""
    features = []
    if bbox is None:
        bbox = results.get("bbox", [-2.85, 56.32, -2.75, 56.38])
    if raster_shape is None:
        raster_shape = results.get("raster_shape", (40, 50))

    min_lon, min_lat, max_lon, max_lat = bbox
    n_rows, n_cols = raster_shape

    transects_list = results.get("sample_transects", results.get("transects", []))
    for tr in transects_list:
        r = tr["row_index"]
        lat = max_lat - (r / max(1, n_rows - 1)) * (max_lat - min_lat)
        lon_hist = min_lon + (tr["historical_col"] / max(1, n_cols - 1)) * (max_lon - min_lon)
        lon_rec = min_lon + (tr["recent_col"] / max(1, n_cols - 1)) * (max_lon - min_lon)

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [round(lon_hist, 6), round(lat, 6)],
                    [round(lon_rec, 6), round(lat, 6)]
                ]
            },
            "properties": {
                "transect_id": tr["transect_id"],
                "row_index": r,
                "net_shoreline_movement_m": tr["net_shoreline_movement_m"],
                "end_point_rate_m_per_year": tr["end_point_rate_m_per_year"],
                "end_point_rate_m_yr": tr["end_point_rate_m_per_year"],
                "hazard_class": tr["hazard_class"],
                "policy_indicator": "EU Climate Adaptation Objective 2"
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }


def transects_to_csv(results: Dict[str, Any]) -> str:
    """Serialize transect rates to tabular CSV."""
    lines = ["transect_id,row_index,net_movement_m,epr_m_yr,end_point_rate_m_yr,hazard_class"]
    transects_list = results.get("sample_transects", results.get("transects", []))
    for tr in transects_list:
        lines.append(
            f"{tr['transect_id']},{tr['row_index']},{tr['net_shoreline_movement_m']},"
            f"{tr['end_point_rate_m_per_year']},{tr['end_point_rate_m_per_year']},{tr['hazard_class']}"
        )
    return "\n".join(lines)

