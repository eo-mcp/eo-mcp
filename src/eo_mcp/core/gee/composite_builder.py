"""Multi-sensor temporal composite builder with fallback ladder and spatial tiling.

Combines the robust 50-year sensor fallback ladder from geeflow with the
multi-method compositing (median, mosaic, greenest-pixel quality mosaic, most recent)
and pre-flight tiling checks from gee-mcp.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from eo_mcp.core.gee.sensors import (
    get_nominal_scale,
    get_sensors_for_year,
    get_collection,
    harmonized_bands_for,
)

logger = logging.getLogger(__name__)


def build_date_range(year: int, start_month: int, end_month: int, offset_yr: int = 0) -> Tuple[str, str]:
    """Compute ISO date strings for a season window, supporting cross-year windows.

    For example, months 11 to 2 in 2022 spans 2022-11-01 to 2023-02-28.

    Args:
        year: Base calendar year.
        start_month: Start month (1-12).
        end_month: End month (1-12).
        offset_yr: Optional year offset for window expansion fallbacks.

    Returns:
        Tuple of (start_date, end_date) in YYYY-MM-DD format.
    """
    import calendar

    sy = year + offset_yr
    if start_month <= end_month:
        ey = sy
    else:
        ey = sy + 1

    last_day = calendar.monthrange(ey, end_month)[1]
    start_str = f"{sy:04d}-{start_month:02d}-01"
    end_str = f"{ey:04d}-{end_month:02d}-{last_day:02d}"
    return start_str, end_str


def check_and_split_region(region: Any, max_pixels: float = 1e8) -> List[Any]:
    """Pre-flight check for region geometry size.

    If a bounding box is excessively large, subdivides into a 2x2 spatial tile grid
    to avoid Google Earth Engine computation memory limits.

    Args:
        region: ee.Geometry defining the AOI.
        max_pixels: Threshold above which to tile.

    Returns:
        List of ee.Geometry tiles (single element if within limits).
    """
    import ee

    bounds = region.bounds().getInfo()["coordinates"][0]
    lons = [p[0] for p in bounds]
    lats = [p[1] for p in bounds]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    lon_span = abs(max_lon - min_lon)
    lat_span = abs(max_lat - min_lat)

    # If region spans more than 2 degrees in either dimension, split into 4 quadrant tiles
    if lon_span > 2.0 or lat_span > 2.0:
        mid_lon = (min_lon + max_lon) / 2.0
        mid_lat = (min_lat + max_lat) / 2.0
        quadrants = [
            ee.Geometry.BBox(min_lon, min_lat, mid_lon, mid_lat),
            ee.Geometry.BBox(mid_lon, min_lat, max_lon, mid_lat),
            ee.Geometry.BBox(min_lon, mid_lat, mid_lon, max_lat),
            ee.Geometry.BBox(mid_lon, mid_lat, max_lon, max_lat),
        ]
        return [q.intersection(region) for q in quadrants]

    return [region]


def build_harmonized_collection_with_fallback(
    year: int,
    aoi: Any,
    start_month: int = 1,
    end_month: int = 12,
    min_scenes: int = 3,
    max_cloud_cover: Optional[float] = None,
    log_func: Optional[Callable[[str], None]] = None,
) -> Tuple[Any, str, int, List[str]]:
    """Build a cloud-masked, harmonized ImageCollection executing the fallback ladder.

    Fallback Ladder:
    1. Primary sensor over the season window.
    2. If scene count < min_scenes: merge backup sensor (e.g. Sentinel-2 + Landsat 8/9).
    3. If still < min_scenes: expand window to +/- 1 year.

    Args:
        year: Target calendar year.
        aoi: ee.Geometry area of interest.
        start_month: Start month (1-12).
        end_month: End month (1-12).
        min_scenes: Minimum desired scene count before triggering fallback.
        max_cloud_cover: Optional metadata filter threshold on cloud percentage.
        log_func: Optional logging callback.

    Returns:
        Tuple of (ee.ImageCollection, primary_sensor_key, total_scene_count, log_lines).
    """
    log_lines: List[str] = []

    def _log(msg: str):
        log_lines.append(msg)
        if log_func:
            log_func(msg)
        logger.debug(msg)

    sensors = get_sensors_for_year(year)
    primary = sensors[0]
    start_date, end_date = build_date_range(year, start_month, end_month)

    _log(f"Initiating composite collection for {year} (window: {start_date} to {end_date})")
    _log(f"Primary sensor: {primary}")

    col = get_collection(primary, aoi, start_date, end_date)
    count = col.size().getInfo()
    _log(f"Found {count} scenes from primary sensor '{primary}'")

    # Ladder step 2: Merge backup sensor if count < min_scenes
    if count < min_scenes and len(sensors) > 1:
        backup = sensors[1]
        _log(f"Scene count ({count}) < min_scenes ({min_scenes}). Merging backup sensor: {backup}")
        backup_col = get_collection(backup, aoi, start_date, end_date)
        col = col.merge(backup_col)
        count = col.size().getInfo()
        _log(f"Scene count after merging backup: {count}")

    # Ladder step 3: Expand search window by +/- 1 year if still under min_scenes
    if count < min_scenes and year > 1972:
        _log(f"Scene count ({count}) still < min_scenes ({min_scenes}). Expanding window by +/- 1 year.")
        for offset in (-1, 1):
            exp_start, exp_end = build_date_range(year, start_month, end_month, offset_yr=offset)
            exp_col = get_collection(primary, aoi, exp_start, exp_end)
            col = col.merge(exp_col)
        count = col.size().getInfo()
        _log(f"Scene count after +/- 1 year expansion: {count}")

    return col, primary, count, log_lines


def reduce_collection(
    collection: Any,
    method: str = "median",
    bands: Optional[List[str]] = None,
) -> Any:
    """Reduce an ee.ImageCollection to a single composite ee.Image.

    Supported methods:
    - 'median': Median value composite (default, robust against cloud outliers).
    - 'mean': Mean value composite.
    - 'mosaic': Latest scene on top (sort by system:time_start ascending).
    - 'greenest': Quality mosaic prioritizing maximum NDVI (qualityMosaic('NDVI')).
    - 'most_recent': Single latest acquisition in the collection.

    Args:
        collection: ee.ImageCollection with harmonized bands.
        method: Compositing algorithm.
        bands: Optional subset of bands to select.

    Returns:
        ee.Image representing the reduced composite.
    """
    import ee

    norm_method = method.strip().lower()

    if norm_method == "median":
        composite = collection.median()
    elif norm_method == "mean":
        composite = collection.mean()
    elif norm_method == "mosaic":
        composite = collection.sort("system:time_start", False).mosaic()
    elif norm_method == "most_recent":
        composite = collection.sort("system:time_start", False).first()
    elif norm_method == "greenest":
        # Compute NDVI band on each scene and take maximum NDVI quality mosaic
        def _add_ndvi(img):
            ndvi = img.normalizedDifference(["NIR", "Red"]).rename("NDVI_QM")
            return img.addBands(ndvi)

        composite = collection.map(_add_ndvi).qualityMosaic("NDVI_QM")
        # Remove the auxiliary quality band
        all_names = composite.bandNames().getInfo()
        clean_names = [n for n in all_names if n != "NDVI_QM"]
        composite = composite.select(clean_names)
    else:
        raise ValueError(
            f"Unknown composite method: '{method}'. Supported: 'median', 'mean', 'mosaic', 'greenest', 'most_recent'"
        )

    if bands:
        composite = composite.select(bands)

    return composite


def build_harmonized_composite(
    year: int,
    aoi: Any,
    start_month: int = 1,
    end_month: int = 12,
    method: str = "median",
    min_scenes: int = 3,
    max_cloud_cover: Optional[float] = None,
    bands: Optional[List[str]] = None,
) -> Tuple[Any, str, List[str], int, str]:
    """High-level builder returning a fully harmonized, cloud-masked, clipped composite.

    Args:
        year: Target year (1972 through present).
        aoi: ee.Geometry defining the region of interest.
        start_month: Start month (1-12).
        end_month: End month (1-12).
        method: Compositing method ('median', 'mean', 'mosaic', 'greenest', 'most_recent').
        min_scenes: Minimum scenes before initiating sensor/temporal fallback.
        max_cloud_cover: Optional scene-level cloud filter.
        bands: Optional list of bands to retain (defaults to all harmonized bands).

    Returns:
        Tuple of:
        (composite_image, primary_sensor, band_names, nominal_scale_m, trace_log)
    """
    col, primary_sensor, count, logs = build_harmonized_collection_with_fallback(
        year=year,
        aoi=aoi,
        start_month=start_month,
        end_month=end_month,
        min_scenes=min_scenes,
        max_cloud_cover=max_cloud_cover,
    )

    if count == 0:
        raise RuntimeError(
            f"No satellite scenes found over region for year {year} (window {start_month:02d}-{end_month:02d}) "
            "even after backup sensor and temporal window expansion. Try widening the date range."
        )

    available_bands = bands or harmonized_bands_for(primary_sensor)
    composite = reduce_collection(col, method=method, bands=available_bands).clip(aoi)
    scale = get_nominal_scale(primary_sensor)
    trace = "\n".join(logs)

    return composite, primary_sensor, available_bands, scale, trace
