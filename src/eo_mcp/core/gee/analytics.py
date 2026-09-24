"""Planetary spatial analytics, zonal statistics, raster masking, and polygon sampling.

Implements server-side GEE analytics:
1. Multi-reducer zonal statistics (mean, median, min, max, stdDev, sum, count)
2. Ancillary raster masking (Copernicus DEM elevation/slope, ESA WorldCover)
3. Geodesic threshold area quantification (km2 and m2) using ee.Image.pixelArea()
4. Homogeneous training polygon sampling from categorical land cover products
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple


def build_combined_reducer(reducer_names: List[str]) -> Any:
    """Combine multiple standard GEE reducers into a single multi-reducer.

    Args:
        reducer_names: List of reducer identifiers ('mean', 'median', 'min', 'max', 'stdDev', 'sum', 'count').

    Returns:
        Combined ee.Reducer.
    """
    import ee

    reducer_constructors = {
        "mean": ee.Reducer.mean,
        "median": ee.Reducer.median,
        "min": ee.Reducer.min,
        "max": ee.Reducer.max,
        "stddev": ee.Reducer.stdDev,
        "std_dev": ee.Reducer.stdDev,
        "sum": ee.Reducer.sum,
        "count": ee.Reducer.count,
    }

    clean_names = [r.strip().lower() for r in reducer_names if r.strip()]
    if not clean_names:
        clean_names = ["mean"]

    first_key = clean_names[0]
    if first_key not in reducer_constructors:
        raise ValueError(f"Unknown reducer: '{first_key}'. Supported: {list(reducer_constructors.keys())}")

    combined = reducer_constructors[first_key]()
    for r_name in clean_names[1:]:
        if r_name in reducer_constructors:
            combined = combined.combine(reducer_constructors[r_name](), sharedInputs=True)
        else:
            raise ValueError(f"Unknown reducer: '{r_name}'. Supported: {list(reducer_constructors.keys())}")

    return combined


def compute_zonal_statistics(
    image: Any,
    region: Any,
    scale: int = 30,
    reducers: Optional[List[str]] = None,
    bands: Optional[List[str]] = None,
    max_pixels: float = 1e9,
) -> Dict[str, Any]:
    """Compute summary statistics for specified bands over a region of interest.

    Args:
        image: ee.Image to evaluate.
        region: ee.Geometry defining the AOI.
        scale: Spatial reduction scale in meters.
        reducers: List of reducers to compute (default: ['mean', 'min', 'max', 'stdDev']).
        bands: Optional subset of bands to evaluate.
        max_pixels: Maximum allowed pixels in reduction.

    Returns:
        Dictionary containing stats, reducers, and region area in m2 and km2.
    """
    target = image.select(bands) if bands else image
    reducer_list = reducers or ["mean", "min", "max", "stddev"]
    combined_reducer = build_combined_reducer(reducer_list)

    raw_stats = target.reduceRegion(
        reducer=combined_reducer,
        geometry=region,
        scale=scale,
        maxPixels=max_pixels,
        bestEffort=True,
    ).getInfo()

    region_area_m2 = region.area(maxError=1).getInfo() or 0.0

    return {
        "reducers": reducer_list,
        "scale_m": scale,
        "region_area_m2": round(region_area_m2, 2),
        "region_area_km2": round(region_area_m2 / 1e6, 4),
        "statistics": raw_stats,
    }


def apply_ancillary_mask(
    target_image: Any,
    mask_dataset_id: str,
    mask_band: str,
    mask_min: Optional[float] = None,
    mask_max: Optional[float] = None,
) -> Any:
    """Apply an ancillary raster value-range mask to an existing image.

    Common applications:
    - Masking by elevation/slope: mask_dataset_id='COPERNICUS/DEM/GLO30', mask_band='DEM'
    - Masking by land cover class: mask_dataset_id='ESA/WorldCover/v200', mask_band='Map'

    Args:
        target_image: ee.Image to mask.
        mask_dataset_id: GEE Image or ImageCollection dataset ID.
        mask_band: Band name in the mask dataset.
        mask_min: Optional minimum value threshold (inclusive).
        mask_max: Optional maximum value threshold (inclusive).

    Returns:
        Masked ee.Image.
    """
    import ee

    try:
        mask_source = ee.Image(mask_dataset_id).select(mask_band)
    except Exception:
        mask_source = ee.ImageCollection(mask_dataset_id).select(mask_band).first()

    binary_mask = ee.Image(1)
    if mask_min is not None:
        binary_mask = binary_mask.And(mask_source.gte(mask_min))
    if mask_max is not None:
        binary_mask = binary_mask.And(mask_source.lte(mask_max))

    return target_image.updateMask(binary_mask)


def compute_threshold_area(
    image: Any,
    band_name: str,
    operator: str,
    threshold: float,
    region: Any,
    scale: int = 30,
) -> Dict[str, Any]:
    """Compute the geodesic area of pixels meeting a threshold condition.

    Args:
        image: ee.Image to analyze.
        band_name: Name of the target band or spectral index (e.g. 'NDVI', 'NDWI').
        operator: Comparison operator ('gte', 'gt', 'lte', 'lt', 'eq').
        threshold: Numeric threshold value.
        region: ee.Geometry defining the AOI.
        scale: Spatial reduction scale in meters.

    Returns:
        Dictionary reporting matching area in km2 and m2, total area, and percentage fraction.
    """
    import ee

    target_band = image.select(band_name)
    norm_op = operator.strip().lower()

    op_map = {
        "gte": target_band.gte,
        ">=": target_band.gte,
        "gt": target_band.gt,
        ">": target_band.gt,
        "lte": target_band.lte,
        "<=": target_band.lte,
        "lt": target_band.lt,
        "<": target_band.lt,
        "eq": target_band.eq,
        "==": target_band.eq,
    }

    if norm_op not in op_map:
        raise ValueError(f"Unknown operator: '{operator}'. Supported: 'gte', 'gt', 'lte', 'lt', 'eq'")

    binary = op_map[norm_op](threshold)

    # Compute geodesic area using ee.Image.pixelArea()
    pixel_area_img = ee.Image.pixelArea().updateMask(binary)
    stats = pixel_area_img.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=region,
        scale=scale,
        maxPixels=1e9,
        bestEffort=True,
    ).getInfo()

    matched_area_m2 = stats.get("area") or 0.0
    total_area_m2 = region.area(maxError=1).getInfo() or 0.0

    matched_km2 = matched_area_m2 / 1e6
    total_km2 = total_area_m2 / 1e6
    fraction_pct = (matched_area_m2 / total_area_m2 * 100.0) if total_area_m2 > 0 else 0.0

    return {
        "band": band_name,
        "operator": norm_op,
        "threshold": threshold,
        "matched_area_km2": round(matched_km2, 4),
        "matched_area_m2": round(matched_area_m2, 2),
        "total_region_km2": round(total_km2, 4),
        "fraction_percentage": round(fraction_pct, 2),
    }


def sample_reference_polygons(
    dataset_id: str,
    band: str,
    class_values: List[int],
    region: Any,
    class_labels: Optional[List[str]] = None,
    points_per_class: int = 6,
    polygon_size_m: float = 180.0,
) -> Dict[str, Any]:
    """Sample homogeneous reference polygons from a categorical dataset for ML training.

    Default source is ESA WorldCover (10m).
    Samples isolated homogeneous clusters and extracts square bounding polygons per class.

    Args:
        dataset_id: GEE dataset ID (e.g. 'ESA/WorldCover/v200').
        band: Categorical band name (e.g. 'Map').
        class_values: Source pixel values to sample (e.g. [10, 40, 50, 80]).
        region: ee.Geometry defining the sampling region.
        class_labels: Human-readable names for classes.
        points_per_class: Target polygon count per class.
        polygon_size_m: Side length in meters of each generated polygon.

    Returns:
        GeoJSON FeatureCollection dictionary.
    """
    import ee

    try:
        source_img = ee.Image(dataset_id).select(band)
    except Exception:
        source_img = ee.ImageCollection(dataset_id).select(band).first()

    features: List[Dict[str, Any]] = []
    labels = class_labels or [f"Class_{val}" for val in class_values]
    half_side = polygon_size_m / 2.0

    for idx, val in enumerate(class_values):
        label = labels[idx] if idx < len(labels) else f"Class_{val}"
        class_mask = source_img.eq(val)
        masked_img = source_img.updateMask(class_mask)

        # Stratified sampling of points inside the class mask
        samples = masked_img.stratifiedSample(
            numPoints=points_per_class,
            classBand=band,
            region=region,
            scale=30,
            geometries=True,
        ).getInfo()

        for pt_feat in samples.get("features", []):
            coords = pt_feat["geometry"]["coordinates"]
            pt = ee.Geometry.Point(coords)
            # Create square buffer
            poly = pt.buffer(half_side).bounds()
            poly_geojson = poly.getInfo()
            features.append({
                "type": "Feature",
                "geometry": poly_geojson,
                "properties": {
                    "class_code": idx,
                    "source_value": val,
                    "label": label,
                    "source_dataset": dataset_id,
                },
            })

    return {
        "type": "FeatureCollection",
        "features": features,
        "total_polygons": len(features),
        "classes_sampled": labels,
    }
