"""Vector Zonal Statistics, Geometry Coupling & Temporal Compositing Engine.

Inspired by and adapted from:
- Python from Space (kscottz/PythonFromSpace): Vector-raster geometry coupling,
  OpenStreetMap Overpass querying, and multi-polygon zonal temporal monitoring.
- GEE-MCP Agentic Architecture (FDL Earth System Lab / Raul Ramos):
  Zonal statistics, temporal compositing, and raster masking primitives.

Provides:
1. OpenStreetMap Overpass API real-world geometry resolver (parks, farms, protected zones).
2. Multi-polygon zonal statistics extraction with property enrichment.
3. Bitemporal zonal change assessment (delta, percent shift, hazard state).
4. Temporal compositing across image stacks (cloud-free median, mean, min, max, percentiles).
5. Raster masking (cloud masking, water masking, threshold masking).
"""

import json
from typing import Dict, List, Tuple, Optional, Any, Union
import numpy as np
import httpx

try:
    import rasterio.features
    from rasterio.transform import from_bounds
    HAS_RASTERIO_FEATURES = True
except (ImportError, OSError):
    HAS_RASTERIO_FEATURES = False

try:
    from shapely.geometry import shape, mapping, Polygon, MultiPolygon
    HAS_SHAPELY = True
except (ImportError, OSError):
    HAS_SHAPELY = False


OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"


def query_osm_geometries(
    bbox_wgs84: Tuple[float, float, float, float],
    osm_tag: str = "leisure=park",
    timeout_s: float = 20.0
) -> Dict[str, Any]:
    """
    Query OpenStreetMap Overpass API for real-world polygon geometries within a bounding box.

    Args:
        bbox_wgs84: (min_lon, min_lat, max_lon, max_lat) in EPSG:4326.
        osm_tag: Filter tag string (e.g. 'leisure=park', 'landuse=farmland', 'natural=wood').
        timeout_s: Request timeout in seconds.

    Returns:
        GeoJSON FeatureCollection dictionary.
    """
    min_lon, min_lat, max_lon, max_lat = bbox_wgs84

    # Overpass bbox format is (south, west, north, east) -> (min_lat, min_lon, max_lat, max_lon)
    if "=" in osm_tag:
        k, v = osm_tag.split("=", 1)
        tag_filter = f'["{k.strip()}"="{v.strip()}"]'
    else:
        tag_filter = f'["{osm_tag.strip()}"]'

    query = f"""
    [out:json][timeout:{int(timeout_s)}];
    (
      way{tag_filter}({min_lat},{min_lon},{max_lat},{max_lon});
      relation{tag_filter}({min_lat},{min_lon},{max_lat},{max_lon});
    );
    out body;
    >;
    out skel qt;
    """

    features = []
    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(OVERPASS_API_URL, data={"data": query})
            if resp.status_code == 200:
                data = resp.json()
                elements = data.get("elements", [])

                # Map nodes by id for coordinate reconstruction
                nodes = {el["id"]: (el["lon"], el["lat"]) for el in elements if el.get("type") == "node"}

                # Process ways into polygons
                for el in elements:
                    if el.get("type") == "way" and "nodes" in el:
                        way_nodes = el["nodes"]
                        if len(way_nodes) >= 3 and way_nodes[0] == way_nodes[-1]:
                            coords = [nodes[nid] for nid in way_nodes if nid in nodes]
                            if len(coords) >= 4:
                                tags = el.get("tags", {})
                                name = tags.get("name", f"Feature {el['id']}")
                                features.append({
                                    "type": "Feature",
                                    "geometry": {
                                        "type": "Polygon",
                                        "coordinates": [coords]
                                    },
                                    "properties": {
                                        "osm_id": el["id"],
                                        "name": name,
                                        "tags": tags
                                    }
                                })
    except Exception:
        # Graceful return of empty collection if Overpass API is temporarily throttled or offline
        pass

    return {
        "type": "FeatureCollection",
        "name": f"OSM {osm_tag}",
        "features": features
    }


def compute_zonal_statistics(
    raster: np.ndarray,
    bbox_wgs84: Tuple[float, float, float, float],
    geojson_features: Dict[str, Any],
    pixel_size_m: float = 10.0
) -> Dict[str, Any]:
    """
    Extract zonal summary statistics across arbitrary polygon geometries.

    Args:
        raster: 2D float32 raster array.
        bbox_wgs84: (min_lon, min_lat, max_lon, max_lat) of the raster.
        geojson_features: GeoJSON FeatureCollection dictionary.
        pixel_size_m: Spatial resolution in meters.

    Returns:
        Enriched GeoJSON FeatureCollection with zonal properties.
    """
    rows, cols = raster.shape
    min_lon, min_lat, max_lon, max_lat = bbox_wgs84
    pixel_area_ha = (pixel_size_m * pixel_size_m) / 10000.0

    features = geojson_features.get("features", [])
    output_features = []

    if HAS_RASTERIO_FEATURES:
        transform = from_bounds(min_lon, min_lat, max_lon, max_lat, cols, rows)
    else:
        transform = None

    for feat in features:
        geom = feat.get("geometry")
        props = dict(feat.get("properties", {}))

        if not geom or geom.get("type") not in ("Polygon", "MultiPolygon"):
            continue

        if HAS_RASTERIO_FEATURES and transform is not None:
            # High-precision vector rasterization
            try:
                poly_mask = rasterio.features.rasterize(
                    [(geom, 1)],
                    out_shape=(rows, cols),
                    transform=transform,
                    fill=0,
                    dtype=np.uint8
                ).astype(bool)
            except Exception:
                poly_mask = None
        else:
            poly_mask = None

        if poly_mask is None:
            # Resilient bounding box fallback
            coords = []
            if geom.get("type") == "Polygon":
                coords = geom.get("coordinates", [[]])[0]
            elif geom.get("type") == "MultiPolygon":
                coords = geom.get("coordinates", [[[]]])[0][0]

            if not coords:
                continue

            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]

            c_min = int(max(0, (min(lons) - min_lon) / max(max_lon - min_lon, 1e-6) * cols))
            c_max = int(min(cols, (max(lons) - min_lon) / max(max_lon - min_lon, 1e-6) * cols))
            r_min = int(max(0, (1.0 - (max(lats) - min_lat) / max(max_lat - min_lat, 1e-6)) * rows))
            r_max = int(min(rows, (1.0 - (min(lats) - min_lat) / max(max_lat - min_lat, 1e-6)) * rows))

            poly_mask = np.zeros((rows, cols), dtype=bool)
            poly_mask[r_min:max(r_max, r_min + 1), c_min:max(c_max, c_min + 1)] = True

        pixels = raster[poly_mask]
        valid_pixels = pixels[~np.isnan(pixels)]

        count = int(len(valid_pixels))
        if count == 0:
            props.update({
                "pixel_count": 0,
                "area_ha": 0.0,
                "mean": 0.0,
                "median": 0.0,
                "std": 0.0,
                "min": 0.0,
                "max": 0.0
            })
        else:
            props.update({
                "pixel_count": count,
                "area_ha": round(float(count * pixel_area_ha), 3),
                "mean": round(float(np.mean(valid_pixels)), 4),
                "median": round(float(np.median(valid_pixels)), 4),
                "std": round(float(np.std(valid_pixels)), 4),
                "min": round(float(np.min(valid_pixels)), 4),
                "max": round(float(np.max(valid_pixels)), 4)
            })

        output_features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": props
        })

    return {
        "type": "FeatureCollection",
        "name": geojson_features.get("name", "Zonal Statistics"),
        "features": output_features
    }


def compute_bitemporal_zonal_change(
    raster_ep1: np.ndarray,
    raster_ep2: np.ndarray,
    bbox_wgs84: Tuple[float, float, float, float],
    geojson_features: Dict[str, Any],
    pixel_size_m: float = 10.0,
    change_threshold: float = 0.15
) -> Dict[str, Any]:
    """
    Compute dual-epoch zonal change across vector polygons.

    Quantifies delta shift, percentage shift, and categorizes status
    (degraded, stable, improved) within each polygon.

    Args:
        raster_ep1: Baseline raster at epoch 1.
        raster_ep2: Comparison raster at epoch 2.
        bbox_wgs84: Bounding box of the rasters.
        geojson_features: GeoJSON polygon features.
        pixel_size_m: Pixel spatial resolution in meters.
        change_threshold: Threshold magnitude defining significant change.

    Returns:
        Enriched GeoJSON FeatureCollection with bitemporal change telemetry.
    """
    zonal_ep1 = compute_zonal_statistics(raster_ep1, bbox_wgs84, geojson_features, pixel_size_m)
    zonal_ep2 = compute_zonal_statistics(raster_ep2, bbox_wgs84, geojson_features, pixel_size_m)

    diff_raster = raster_ep2 - raster_ep1
    zonal_diff = compute_zonal_statistics(diff_raster, bbox_wgs84, geojson_features, pixel_size_m)

    enriched_features = []
    for f1, f2, fd in zip(zonal_ep1["features"], zonal_ep2["features"], zonal_diff["features"]):
        p1 = f1["properties"]
        p2 = f2["properties"]
        pd = fd["properties"]

        mean1 = p1.get("mean", 0.0)
        mean2 = p2.get("mean", 0.0)
        delta = round(mean2 - mean1, 4)
        pct_change = round((delta / (abs(mean1) + 1e-6)) * 100.0, 2)

        if delta <= -change_threshold:
            status = "degraded"
        elif delta >= change_threshold:
            status = "improved"
        else:
            status = "stable"

        combined_props = {
            **p2,
            "epoch1_mean": mean1,
            "epoch2_mean": mean2,
            "delta_mean": delta,
            "percent_change": pct_change,
            "status": status,
            "change_intensity": abs(delta)
        }

        enriched_features.append({
            "type": "Feature",
            "geometry": f2["geometry"],
            "properties": combined_props
        })

    # Sort descending by change intensity
    enriched_features.sort(key=lambda f: f["properties"].get("change_intensity", 0.0), reverse=True)

    return {
        "type": "FeatureCollection",
        "name": "Bitemporal Zonal Change",
        "features": enriched_features
    }


def compute_temporal_composite(
    image_stack: List[np.ndarray],
    method: str = "median"
) -> np.ndarray:
    """
    Compute a multi-temporal raster composite across a temporal image stack.

    Handles cloud contamination and transient anomalies by computing statistical
    reduction along the temporal dimension.

    Args:
        image_stack: List of co-registered 2D float arrays.
        method: Statistical reduction method:
            - 'median': Cloud-free median composite (standard for Sentinel/Landsat).
            - 'mean': Temporal arithmetic mean.
            - 'min': Temporal minimum (e.g. baseline low-vegetation or water extent).
            - 'max': Temporal maximum (e.g. peak greenness / max NDVI).
            - 'percentile_25': 25th percentile (suppresses bright cloud reflection).
            - 'percentile_75': 75th percentile.

    Returns:
        2D float32 composite raster array.
    """
    if not image_stack:
        raise ValueError("Image stack cannot be empty for temporal compositing.")

    stack = np.stack([arr.astype(np.float32) for arr in image_stack], axis=0)

    with np.errstate(divide="ignore", invalid="ignore"):
        if method == "mean":
            composite = np.nanmean(stack, axis=0)
        elif method == "max":
            composite = np.nanmax(stack, axis=0)
        elif method == "min":
            composite = np.nanmin(stack, axis=0)
        elif method == "percentile_25":
            composite = np.nanpercentile(stack, 25.0, axis=0)
        elif method == "percentile_75":
            composite = np.nanpercentile(stack, 75.0, axis=0)
        else:  # median
            composite = np.nanmedian(stack, axis=0)

    return composite.astype(np.float32)


def apply_raster_mask(
    raster: np.ndarray,
    mask: np.ndarray,
    invert: bool = False,
    fill_value: float = np.nan
) -> np.ndarray:
    """
    Apply a boolean or threshold mask to a raster array.

    Args:
        raster: 2D input array.
        mask: 2D boolean array (True indicates pixels to mask out).
        invert: If True, keep pixels where mask is True and mask out False.
        fill_value: Value to set for masked pixels (default np.nan).

    Returns:
        Masked 2D array.
    """
    out = raster.astype(np.float32).copy()
    m = ~mask.astype(bool) if invert else mask.astype(bool)
    out[m] = fill_value
    return out
