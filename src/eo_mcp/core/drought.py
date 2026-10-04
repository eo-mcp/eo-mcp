"""
Reservoir drought dynamics & surface water depletion engine.

Zero-infrastructure MCP capability leveraging the EC Joint Research Centre (JRC)
Global Surface Water archive and multi-temporal optical imagery to track
reservoir shrinkage, permanent vs seasonal water loss, and drought severity.

References:
- Pekel, J.-F., Cottam, A., Gorelick, N., & Belward, A. S. (2016). High-resolution
  mapping of global surface water and its long-term changes. Nature, 540(7633),
  418-422. DOI: 10.1038/nature20584
"""

from typing import List, Dict, Any, Optional, Tuple
import math
import httpx
import numpy as np


def analyze_water_body_drought(
    bbox: List[float],
    historical_year: int = 2019,
    recent_year: int = 2024,
    cellsize_m: float = 30.0
) -> Dict[str, Any]:
    """
    Analyze reservoir surface water depletion between two observation epochs.

    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat] in WGS84.
        historical_year: Baseline year (e.g. 2019).
        recent_year: Modern year (e.g. 2024).
        cellsize_m: Spatial resolution in meters (30m standard for JRC/Landsat).

    Returns:
        Dictionary with historical vs modern water area (ha, km2), deficit percentage,
        seasonal transition breakdown, and drought severity class.

    References:
    - Pekel, J.-F., et al. (2016). Nature, 540(7633), 418-422.
      DOI: 10.1038/nature20584
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    result: Dict[str, Any] = {
        "bbox": bbox,
        "historical_year": historical_year,
        "recent_year": recent_year,
        "historical_water_area_ha": None,
        "recent_water_area_ha": None,
        "net_water_loss_ha": None,
        "water_area_change_percentage": None,
        "water_loss_percentage": None,
        "permanent_water_area_ha": None,
        "seasonal_water_area_ha": None,
        "water_present_area_ha": None,
        "dried_up_area_ha": None,
        "transition_breakdown_ha": {
            "permanent_water_ha": None,
            "desiccated_margin_ha": None,
            "newly_inundated_ha": None,
        },
        "drought_severity_class": "NOT_COMPARED",
        "dataset_source": "EC JRC Global Surface Water seasonality 2020 via Planetary Computer",
        "directive_alignment": "Water Framework Directive (WFD 2000/60/EC) & UN SDG 6.6",
        "policy_alignment": "Water Framework Directive (WFD 2000/60/EC) & UN SDG 6.6",
        "notice": (
            f"The public JRC mosaic used here is seasonality for 2020. "
            f"It does not compare {historical_year} with {recent_year}, so no water loss or drought class was calculated."
        ),
    }

    try:
        import rasterio
        from rasterio.windows import from_bounds
    except ImportError:
        result["notice"] = "rasterio is not available, so no JRC seasonality window was read. No drought values were invented."
        return result

    try:
        with httpx.Client(timeout=40.0) as client:
            resp = client.post(
                "https://planetarycomputer.microsoft.com/api/stac/v1/search",
                json={"collections": ["jrc-gsw"], "bbox": bbox, "limit": 8},
            )
            resp.raise_for_status()
            features = resp.json().get("features") or []
    except Exception as exc:
        result["notice"] = (
            f"JRC Global Surface Water search failed ({exc.__class__.__name__}). "
            "No drought values were invented."
        )
        return result

    if not features:
        result["notice"] = "No JRC Global Surface Water tile covers this box. No drought values were invented."
        return result

    month_counts = [0] * 13
    other_pixels = 0
    tiles = []
    pixel_ha = None
    try:
        with httpx.Client(timeout=40.0) as client:
            for feature in features:
                asset = (feature.get("assets") or {}).get("seasonality") or {}
                href = asset.get("href")
                if not href:
                    continue
                signed = client.get(
                    "https://planetarycomputer.microsoft.com/api/sas/v1/sign",
                    params={"href": href},
                )
                signed.raise_for_status()
                url = signed.json()["href"]
                with rasterio.Env(
                    GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                    CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
                    GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES",
                ):
                    with rasterio.open("/vsicurl/" + url) as src:
                        window = from_bounds(min_lon, min_lat, max_lon, max_lat, transform=src.transform)
                        if window.width > 4000 or window.height > 4000:
                            result["notice"] = (
                                "This box is larger than a 4000-pixel JRC window. "
                                "No seasonality was read and no drought values were invented."
                            )
                            return result
                        data = src.read(1, window=window)
                        if pixel_ha is None and data.size:
                            lat = (min_lat + max_lat) / 2.0
                            pixel_ha = (
                                abs(src.res[1]) * 111320.0
                                * abs(src.res[0]) * 111320.0
                                * math.cos(math.radians(lat))
                            ) / 10000.0
                flat = data.ravel()
                for value, count in zip(*np.unique(flat, return_counts=True)):
                    value = int(value)
                    count = int(count)
                    if 0 <= value <= 12:
                        month_counts[value] += count
                    else:
                        other_pixels += count
                tiles.append(feature.get("id"))
    except Exception as exc:
        result["notice"] = (
            f"JRC seasonality could not be read ({exc.__class__.__name__}). "
            "No drought values were invented."
        )
        return result

    if pixel_ha is None:
        result["notice"] = "JRC seasonality returned an empty window. No drought values were invented."
        return result

    def _ha(pixels: int) -> float:
        return round(pixels * pixel_ha, 2)

    seasonal_px = sum(month_counts[1:12])
    permanent_px = month_counts[12]
    present_px = seasonal_px + permanent_px
    result.update({
        "permanent_water_area_ha": _ha(permanent_px),
        "seasonal_water_area_ha": _ha(seasonal_px),
        "water_present_area_ha": _ha(present_px),
        "seasonality_year": 2020,
        "tiles": tiles,
        "pixel_area_ha": round(pixel_ha, 6),
        "month_pixel_counts": {str(i): month_counts[i] for i in range(13) if month_counts[i]},
        "transition_breakdown_ha": {
            "permanent_water_ha": _ha(permanent_px),
            "seasonal_water_ha": _ha(seasonal_px),
            "desiccated_margin_ha": None,
            "newly_inundated_ha": None,
        },
        "notice": (
            f"Read EC JRC seasonality for 2020 from {', '.join(tiles)}. "
            "Pixel values 1–12 are the number of months water was present; 12 means every month. "
            f"The requested {historical_year} to {recent_year} comparison was not calculated."
        ),
    })
    if other_pixels:
        result["unmapped_pixels"] = other_pixels
    return result


def drought_to_geojson(results: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize reservoir extent to GeoJSON Polygon FeatureCollection."""
    min_lon, min_lat, max_lon, max_lat = results["bbox"]

    ring = [
        [round(min_lon, 6), round(min_lat, 6)],
        [round(max_lon, 6), round(min_lat, 6)],
        [round(max_lon, 6), round(max_lat, 6)],
        [round(min_lon, 6), round(max_lat, 6)],
        [round(min_lon, 6), round(min_lat, 6)],
    ]

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [ring]},
                "properties": {
                    "feature_type": "ANALYSIS_WINDOW",
                    "seasonality_year": results.get("seasonality_year"),
                    "water_present_area_ha": results.get("water_present_area_ha"),
                    "permanent_water_area_ha": results.get("permanent_water_area_ha"),
                    "seasonal_water_area_ha": results.get("seasonal_water_area_ha"),
                    "historical_area_ha": results.get("historical_water_area_ha"),
                    "recent_area_ha": results.get("recent_water_area_ha"),
                    "net_water_loss_ha": results.get("net_water_loss_ha"),
                    "change_pct": results.get("water_area_change_percentage"),
                    "drought_status": results.get("drought_severity_class"),
                    "drought_severity_class": results.get("drought_severity_class"),
                    "notice": results.get("notice"),
                    "directive": results.get("directive_alignment"),
                },
            }
        ],
    }


def drought_to_csv(results: Dict[str, Any]) -> str:
    """Serialize reservoir drought results to tabular CSV."""
    lines = [
        "metric,value,unit",
        f"historical_year,{results.get('historical_year')},year",
        f"recent_year,{results.get('recent_year')},year",
        f"historical_area,{results.get('historical_water_area_ha')},hectares",
        f"historical_water_area_ha,{results.get('historical_water_area_ha')},hectares",
        f"recent_area,{results.get('recent_water_area_ha')},hectares",
        f"net_water_loss_ha,{results.get('net_water_loss_ha', 0.0)},hectares",
        f"change_percentage,{results.get('water_area_change_percentage')},percent",
        f"drought_severity,{results.get('drought_severity_class')},category",
        f"drought_severity_class,{results.get('drought_severity_class')},category"
    ]
    tb = results.get("transition_breakdown_ha", {})
    for k, v in tb.items():
        lines.append(f"{k},{v},hectares")
    return "\n".join(lines)
