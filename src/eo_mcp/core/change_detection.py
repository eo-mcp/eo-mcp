"""Remote Sensing Change Detection (RS-CD) Core Computational Engine.

Implements foundational change detection algorithms curated from:
- Awesome Remote Sensing Change Detection (wenhwu/awesome-remote-sensing-change-detection)

Key Methodologies:
1. Difference & Ratio Algebra: Delta, Relative Difference, Normalized Difference.
2. Change Vector Analysis (CVA): Multi-spectral Euclidean magnitude & directional vectors.
3. SAR Log-Ratio: Speckle-reduced dual-epoch backscatter change (Sentinel-1 C-band).
4. Pixel-Wise T-Test (PWTT): Temporal baseline z-score testing for damage & conflict detection.
5. Adaptive Otsu Thresholding: Dynamic change/no-change segmentation.
6. Contiguous Patch Clustering: Spatial connected components, Minimum Mapping Unit (MMU) filtering,
   and GeoJSON polygonization.
7. Remote Sensing Image Change Captioning (RSICC) Telemetry: Natural language change descriptors.

References:
- Malila, W. A. (1980). Change Vector Analysis: An Approach for Detecting Forest Changes with Landsat.
  LARS Symposia, Purdue University, pp. 326-335.
- Bovolo, F., & Bruzzone, L. (2005). A detail-preserving scale-driven approach to unsupervised change
  detection in multitemporal SAR images. IEEE TGRS, 43(12), 2963-2972.
- Ballinger, O. (2025). Open access battle damage detection via Pixel-Wise T-Test on Sentinel-1 imagery.
  Remote Sensing of Environment, 318, 114578. DOI: 10.1016/j.rse.2025.114578
- Otsu, N. (1979). A threshold selection method from gray-level histograms. IEEE Transactions on
  Systems, Man, and Cybernetics, 9(1), 62-66. DOI: 10.1109/TSMC.1979.4310076
"""

from typing import Dict, List, Tuple, Optional, Any, Union
import numpy as np

try:
    from scipy import ndimage
    HAS_SCIPY = True
except (ImportError, OSError):
    ndimage = None
    HAS_SCIPY = False


def compute_difference_image(
    epoch1: np.ndarray,
    epoch2: np.ndarray,
    mode: str = "raw"
) -> np.ndarray:
    """
    Compute algebraic difference between two co-registered raster arrays.

    Args:
        epoch1: 2D float array of baseline observation (t1).
        epoch2: 2D float array of comparison observation (t2).
        mode: Difference mode:
            - 'raw': epoch2 - epoch1 (positive means increase, negative means decrease).
            - 'absolute': abs(epoch2 - epoch1).
            - 'relative': (epoch2 - epoch1) / (abs(epoch1) + 1e-6).
            - 'normalized': (epoch2 - epoch1) / (epoch2 + epoch1 + 1e-6).

    Returns:
        2D float32 difference array.
    """
    ep1 = epoch1.astype(np.float32)
    ep2 = epoch2.astype(np.float32)

    with np.errstate(divide="ignore", invalid="ignore"):
        if mode == "absolute":
            diff = np.abs(ep2 - ep1)
        elif mode == "relative":
            diff = (ep2 - ep1) / (np.abs(ep1) + 1e-6)
        elif mode == "normalized":
            denom = ep2 + ep1
            diff = np.where(denom != 0, (ep2 - ep1) / (denom + 1e-6), np.nan)
        else:  # raw
            diff = ep2 - ep1

    return diff.astype(np.float32)


def compute_change_vector_analysis(
    bands_ep1: Dict[str, np.ndarray],
    bands_ep2: Dict[str, np.ndarray]
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Change Vector Analysis (CVA) across multi-spectral band stacks.

    Calculates total Euclidean spectral displacement (magnitude) and directional
    angle in spectral feature space.

    Args:
        bands_ep1: Dict mapping band names (e.g. 'B', 'G', 'R', 'N', 'S1') to 2D arrays at t1.
        bands_ep2: Dict mapping identical band names to 2D arrays at t2.

    Returns:
        (magnitude_array, direction_degrees, summary_metadata)

    References:
        Malila, W. A. (1980). Change Vector Analysis. LARS Symposia.
    """
    common_bands = sorted(list(set(bands_ep1.keys()) & set(bands_ep2.keys())))
    if not common_bands:
        raise ValueError("No common spectral bands provided between epoch 1 and epoch 2.")

    # Align shapes
    first_b = common_bands[0]
    shape = bands_ep1[first_b].shape

    sum_sq_diff = np.zeros(shape, dtype=np.float32)
    for b in common_bands:
        arr1 = bands_ep1[b].astype(np.float32)
        arr2 = bands_ep2[b].astype(np.float32)
        diff = arr2 - arr1
        sum_sq_diff += np.square(diff)

    magnitude = np.sqrt(sum_sq_diff)

    # Compute directional angle (using first two bands if available, e.g. R and N)
    if len(common_bands) >= 2:
        b1, b2 = common_bands[0], common_bands[1]
        d1 = bands_ep2[b1].astype(np.float32) - bands_ep1[b1].astype(np.float32)
        d2 = bands_ep2[b2].astype(np.float32) - bands_ep1[b2].astype(np.float32)
        direction_rad = np.arctan2(d2, d1)
        direction_deg = np.degrees(direction_rad) % 360.0
    else:
        direction_deg = np.zeros(shape, dtype=np.float32)

    valid_mag = magnitude[~np.isnan(magnitude)]
    meta = {
        "bands_analyzed": common_bands,
        "mean_magnitude": float(np.mean(valid_mag)) if len(valid_mag) > 0 else 0.0,
        "max_magnitude": float(np.max(valid_mag)) if len(valid_mag) > 0 else 0.0,
        "std_magnitude": float(np.std(valid_mag)) if len(valid_mag) > 0 else 0.0,
    }

    return magnitude, direction_deg, meta


def compute_sar_log_ratio(
    sar_ep1_db: np.ndarray,
    sar_ep2_db: np.ndarray
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Compute SAR backscatter difference and log-ratio between two C-band acquisitions.

    In decibel space: Delta sigma0_dB = sigma0_dB(t2) - sigma0_dB(t1).
    Negative backscatter drops indicate specular water inundation or structural destruction.
    Positive backscatter surges indicate new structures, roughness, or high soil moisture.

    Args:
        sar_ep1_db: 2D array of SAR backscatter at t1 (in dB).
        sar_ep2_db: 2D array of SAR backscatter at t2 (in dB).

    Returns:
        (delta_db_array, summary_stats)
    """
    ep1 = sar_ep1_db.astype(np.float32)
    ep2 = sar_ep2_db.astype(np.float32)

    delta_db = ep2 - ep1

    valid = delta_db[~np.isnan(delta_db)]
    stats = {
        "mean_delta_db": float(np.mean(valid)) if len(valid) > 0 else 0.0,
        "min_delta_db": float(np.min(valid)) if len(valid) > 0 else 0.0,
        "max_delta_db": float(np.max(valid)) if len(valid) > 0 else 0.0,
        "std_delta_db": float(np.std(valid)) if len(valid) > 0 else 0.0,
        "severe_drop_percent": float(np.sum(valid < -3.0) / len(valid) * 100.0) if len(valid) > 0 else 0.0,
        "severe_surge_percent": float(np.sum(valid > 3.0) / len(valid) * 100.0) if len(valid) > 0 else 0.0,
    }

    return delta_db, stats


def compute_pixelwise_t_test(
    baseline_stack: List[np.ndarray],
    post_event: np.ndarray,
    z_threshold: float = 2.5
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Pixel-Wise T-Test (PWTT) / Z-Score anomaly detection against a baseline time-series stack.

    Evaluates whether post-event backscatter or reflectance deviates significantly
    from pre-event baseline normal distributions:
    z = (post_event - mu_baseline) / (std_baseline + epsilon)

    Args:
        baseline_stack: List of 2D arrays representing pre-event baseline acquisitions (n >= 2).
        post_event: 2D array representing post-event observation.
        z_threshold: Z-score threshold for anomaly flag (default 2.5).

    Returns:
        (z_score_array, anomaly_mask, summary_stats)

    References:
        Ballinger, O. (2025). Remote Sensing of Environment, 318, 114578.
    """
    if len(baseline_stack) < 2:
        raise ValueError("Pixel-Wise T-Test requires at least 2 pre-event baseline observations.")

    stack = np.stack([arr.astype(np.float32) for arr in baseline_stack], axis=0)
    mu = np.nanmean(stack, axis=0)
    sigma = np.nanstd(stack, axis=0)

    post = post_event.astype(np.float32)
    epsilon = 1e-4

    with np.errstate(divide="ignore", invalid="ignore"):
        z_score = (post - mu) / (sigma + epsilon)

    anomaly_mask = np.abs(z_score) >= z_threshold

    valid_z = z_score[~np.isnan(z_score)]
    stats = {
        "z_threshold": z_threshold,
        "baseline_scenes_count": len(baseline_stack),
        "mean_z_score": float(np.nanmean(valid_z)) if len(valid_z) > 0 else 0.0,
        "anomalous_pixel_count": int(np.sum(anomaly_mask)),
        "anomaly_percentage": float(np.sum(anomaly_mask) / valid_z.size * 100.0) if valid_z.size > 0 else 0.0
    }

    return z_score, anomaly_mask, stats


def otsu_threshold(diff_image: np.ndarray, num_bins: int = 256) -> float:
    """
    Compute optimal binarization threshold via Otsu's maximum inter-class variance method.

    Args:
        diff_image: 2D float or uint array (difference magnitude).
        num_bins: Histogram bins (default 256).

    Returns:
        Optimal threshold float value.

    References:
        Otsu, N. (1979). IEEE TSMC, 9(1), 62-66.
    """
    valid = diff_image[~np.isnan(diff_image)]
    if len(valid) == 0:
        return 0.0

    min_val, max_val = float(np.min(valid)), float(np.max(valid))
    if min_val == max_val:
        return min_val

    hist, bin_edges = np.histogram(valid, bins=num_bins, range=(min_val, max_val))
    hist = hist.astype(np.float32)
    total = hist.sum()
    if total == 0:
        return (min_val + max_val) / 2.0

    w_b = np.cumsum(hist)
    w_f = total - w_b
    valid_mask = (w_b > 0) & (w_f > 0)

    sum_total = float(np.dot(np.arange(num_bins), hist))
    sum_b = np.cumsum(np.arange(num_bins) * hist)

    with np.errstate(divide="ignore", invalid="ignore"):
        m_b = sum_b / np.maximum(w_b, 1e-6)
        m_f = (sum_total - sum_b) / np.maximum(w_f, 1e-6)
        var_between = w_b * w_f * ((m_b - m_f) ** 2)
        var_between[~valid_mask] = 0.0

    max_var = float(np.max(var_between))
    if max_var <= 0:
        return float((min_val + max_val) / 2.0)

    # Pick midpoint of the maximum between-class variance plateau
    best_bins = np.where(np.isclose(var_between, max_var, rtol=1e-5, atol=1e-5))[0]
    mid_idx = float((best_bins[0] + best_bins[-1]) / 2.0)

    bin_width = (max_val - min_val) / num_bins
    threshold = min_val + (mid_idx + 0.5) * bin_width
    return float(threshold)


def extract_contiguous_change_patches(
    change_mask: np.ndarray,
    pixel_size_m: float = 10.0,
    min_patch_ha: float = 0.5,
    bbox_wgs84: Optional[Tuple[float, float, float, float]] = None,
    hazard_label: str = "change_anomaly"
) -> List[Dict[str, Any]]:
    """
    Extract, cluster, filter, and vectorize contiguous change anomaly patches.

    Applies connected component labeling, filters out noise below the Minimum
    Mapping Unit (min_patch_ha), and projects pixel centroids to WGS84 coordinates.

    Args:
        change_mask: 2D boolean array where True indicates change anomaly.
        pixel_size_m: Spatial resolution in meters (e.g. 10.0 for Sentinel-2, 30.0 for Landsat).
        min_patch_ha: Minimum Mapping Unit (MMU) in hectares.
        bbox_wgs84: Optional (min_lon, min_lat, max_lon, max_lat) for georeferencing.
        hazard_label: Classification tag for identified patches.

    Returns:
        List of patch dictionaries sorted descending by surface area.
    """
    mask = change_mask.astype(bool)
    rows, cols = mask.shape
    pixel_area_ha = (pixel_size_m * pixel_size_m) / 10000.0

    patches: List[Dict[str, Any]] = []

    if HAS_SCIPY:
        labeled, num_features = ndimage.label(mask)
    else:
        # Resilient pure-Python fallback for environments without C-extensions
        labeled = np.zeros_like(mask, dtype=np.int32)
        current_label = 1
        for r in range(rows):
            for c in range(cols):
                if mask[r, c] and labeled[r, c] == 0:
                    # Simple flood fill
                    queue = [(r, c)]
                    labeled[r, c] = current_label
                    while queue:
                        cr, cc = queue.pop()
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = cr + dr, cc + dc
                            if 0 <= nr < rows and 0 <= nc < cols:
                                if mask[nr, nc] and labeled[nr, nc] == 0:
                                    labeled[nr, nc] = current_label
                                    queue.append((nr, nc))
                    current_label += 1
        num_features = current_label - 1

    if num_features == 0:
        return []

    # Calculate geographic transformation factors if bbox provided
    min_lon, min_lat, max_lon, max_lat = bbox_wgs84 if bbox_wgs84 else (-180.0, -90.0, 180.0, 90.0)

    for feat_id in range(1, num_features + 1):
        component_coords = np.argwhere(labeled == feat_id)
        pixel_count = int(len(component_coords))
        area_ha = round(float(pixel_count * pixel_area_ha), 3)

        if area_ha < min_patch_ha:
            continue

        mean_row = float(np.mean(component_coords[:, 0]))
        mean_col = float(np.mean(component_coords[:, 1]))

        # Project pixel row/col to approximate WGS84 lon/lat
        frac_x = mean_col / max(cols, 1)
        frac_y = 1.0 - (mean_row / max(rows, 1))
        centroid_lon = round(min_lon + frac_x * (max_lon - min_lon), 6)
        centroid_lat = round(min_lat + frac_y * (max_lat - min_lat), 6)

        min_r, min_c = component_coords.min(axis=0)
        max_r, max_c = component_coords.max(axis=0)

        patch_bbox = [
            round(min_lon + (min_c / cols) * (max_lon - min_lon), 6),
            round(min_lat + (1.0 - max_r / rows) * (max_lat - min_lat), 6),
            round(min_lon + (max_c / cols) * (max_lon - min_lon), 6),
            round(min_lat + (1.0 - min_r / rows) * (max_lat - min_lat), 6)
        ]

        patches.append({
            "patch_id": int(feat_id),
            "area_ha": area_ha,
            "pixel_count": pixel_count,
            "centroid_lon": centroid_lon,
            "centroid_lat": centroid_lat,
            "bbox_wgs84": patch_bbox,
            "hazard_label": hazard_label
        })

    patches.sort(key=lambda p: p["area_ha"], reverse=True)
    return patches


def patches_to_geojson(
    patches: List[Dict[str, Any]],
    dataset_name: str = "Planetary Change Patches"
) -> Dict[str, Any]:
    """
    Format extracted change patches into a standard GeoJSON FeatureCollection.

    Args:
        patches: List of patch dictionaries from extract_contiguous_change_patches.
        dataset_name: Descriptive layer title.

    Returns:
        GeoJSON FeatureCollection dictionary.
    """
    features = []
    for p in patches:
        min_x, min_y, max_x, max_y = p["bbox_wgs84"]
        polygon_coords = [[
            [min_x, min_y],
            [max_x, min_y],
            [max_x, max_y],
            [min_x, max_y],
            [min_x, min_y]
        ]]

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": polygon_coords
            },
            "properties": {
                "patch_id": p["patch_id"],
                "area_ha": p["area_ha"],
                "pixel_count": p["pixel_count"],
                "centroid_lon": p["centroid_lon"],
                "centroid_lat": p["centroid_lat"],
                "hazard_label": p["hazard_label"]
            }
        })

    return {
        "type": "FeatureCollection",
        "name": dataset_name,
        "features": features
    }


def generate_rsicc_caption(
    location_name: str,
    epoch1_str: str,
    epoch2_str: str,
    loss_ha: float,
    gain_ha: float,
    net_ha: float,
    total_area_ha: float,
    dominant_type: str = "canopy_cover",
    top_patches: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Generate Remote Sensing Image Change Captioning (RSICC) telemetry.

    Constructs a grounded, assertive narrative explaining multi-temporal
    transformations, spatial concentrations, and net shifts.

    Args:
        location_name: Region or coordinates description.
        epoch1_str: Date string for baseline observation.
        epoch2_str: Date string for comparison observation.
        loss_ha: Surface area of negative change/loss in hectares.
        gain_ha: Surface area of positive change/gain in hectares.
        net_ha: Net surface change (gain_ha - loss_ha).
        total_area_ha: Total surveyed area in hectares.
        dominant_type: Subject descriptor ('canopy_cover', 'water_body', 'built_up', 'burn_scar').
        top_patches: Top contiguous change patches with areas and centroids.

    Returns:
        Structured RSICC natural language caption.
    """
    loss_pct = round((loss_ha / total_area_ha * 100.0), 2) if total_area_ha > 0 else 0.0
    gain_pct = round((gain_ha / total_area_ha * 100.0), 2) if total_area_ha > 0 else 0.0
    net_direction = "expansion" if net_ha > 0 else "reduction"

    lines = [
        f"Multi-temporal remote sensing analysis for {location_name} between {epoch1_str} and {epoch2_str}:",
        f"Total surveyed area spans {round(total_area_ha, 1)} hectares.",
        f"Observed negative shift in {dominant_type} covers {round(loss_ha, 1)} ha ({loss_pct}% of surveyed area).",
        f"Observed positive expansion covers {round(gain_ha, 1)} ha ({gain_pct}% of surveyed area).",
        f"Net trajectory indicates an overall {net_direction} of {abs(round(net_ha, 1))} ha."
    ]

    if top_patches and len(top_patches) > 0:
        top1 = top_patches[0]
        lines.append(
            f"Primary anomaly hotspot is concentrated at coordinates [{top1['centroid_lat']}, {top1['centroid_lon']}] "
            f"encompassing {top1['area_ha']} contiguous hectares."
        )

    return " ".join(lines)
