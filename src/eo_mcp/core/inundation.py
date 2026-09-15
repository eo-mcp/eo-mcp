"""
Sea-level rise, storm surge, and coastal flood inundation modeling engine.

Applies a hydrologically connected 8-connected flood-fill model to Copernicus DEM GLO-30 elevation
arrays, simulating IPCC AR6 sea-level rise scenarios and storm surge events conforming to
the EU Floods Directive (2007/60/EC Art. 6).

References:
- Poulter, B., & Halpin, P. N. (2008). Raster modelling of coastal flooding from
  sea-level rise. International Journal of Geographical Information Science, 22(2),
  167-182. DOI: 10.1080/13658810701371858
- Gesch, D. B. (2009). Analysis of lidar elevation data for improved identification
  and delineation of lands vulnerable to sea-level rise. Journal of Coastal Research,
  SI(53), 49-58. DOI: 10.2112/si53-006.1
- Gesch, D. B. (2018). Best practices for elevation-based assessments of sea-level
  rise and coastal flooding exposure. Frontiers in Earth Science, 6, 230.
  DOI: 10.3389/feart.2018.00230
- Fox-Kemper, B., et al. (2021). Ocean, cryosphere and sea level change. In Climate
  Change 2021: The Physical Science Basis (IPCC AR6 WGI), pp. 1211-1362.
  Cambridge University Press. DOI: 10.1017/9781009157896.011
"""

from typing import Dict, Any, Optional, Tuple, List
import numpy as np
from scipy.ndimage import label


# Standard IPCC AR6 Sea-Level Rise Projections (Global Mean Sea Level by 2100 relative to 1995-2014; Fox-Kemper et al., 2021)
IPCC_AR6_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "SSP1-2.6": {
        "title": "Low Emissions (Sustainability)",
        "slr_median_m": 0.44,
        "slr_range_m": [0.32, 0.61],
        "description": "Consistent with Paris Agreement 1.5°C-2.0°C warming."
    },
    "SSP2-4.5": {
        "title": "Intermediate Emissions (Middle of the Road)",
        "slr_median_m": 0.56,
        "slr_range_m": [0.44, 0.76],
        "description": "Current policy trajectory without dramatic mitigation."
    },
    "SSP5-8.5": {
        "title": "High Emissions (Fossil-Fueled Development)",
        "slr_median_m": 0.77,
        "slr_range_m": [0.63, 1.01],
        "description": "Worst-case unconstrained emissions scenario."
    }
}


def simulate_connected_inundation(
    dem_array: np.ndarray,
    water_level_rise_m: float = 1.0,
    storm_surge_m: float = 0.0,
    cellsize_m: float = 30.0,
    sea_level_datum_m: float = 0.0
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Simulate coastal inundation using an 8-connected flood-fill algorithm.
    Ensures hydrologic connectivity so inland isolated depressions below sea level
    without physical connection to the ocean are NOT falsely classified as flooded.

    Args:
        dem_array: 2D elevation grid in meters (e.g. from Copernicus DEM GLO-30).
        water_level_rise_m: Projected sea level rise in meters.
        storm_surge_m: Additional storm surge water elevation in meters.
        cellsize_m: Pixel spatial resolution in meters (30m for Copernicus DEM).
        sea_level_datum_m: Baseline sea level datum in meters. Default is 0.0.

    Returns:
        (binary_inundation_mask, depth_array_meters, summary_metrics)

    References:
    - Poulter, B., & Halpin, P. N. (2008). International Journal of Geographical
      Information Science, 22(2), 167-182. DOI: 10.1080/13658810701371858
    - Gesch, D. B. (2009). Journal of Coastal Research, SI(53), 49-58.
      DOI: 10.2112/si53-006.1
    - Gesch, D. B. (2018). Frontiers in Earth Science, 6, 230.
      DOI: 10.3389/feart.2018.00230
    - Fox-Kemper, B., et al. (2021). IPCC AR6 WGI, Chapter 9.
      DOI: 10.1017/9781009157896.011
    """
    if dem_array.ndim == 3:
        dem_array = dem_array[0]

    valid_mask = ~np.isnan(dem_array)
    total_valid = np.sum(valid_mask)
    if total_valid == 0:
        return np.zeros_like(dem_array, dtype=bool), np.zeros_like(dem_array, dtype=np.float32), {}

    total_water_level = sea_level_datum_m + water_level_rise_m + storm_surge_m

    # Baseline land pixels (cells above initial sea level)
    baseline_land = (dem_array > sea_level_datum_m) & valid_mask
    total_land_pixels = int(np.sum(baseline_land))

    # All candidate submerged pixels (elevation <= target water level)
    candidate_submerged = (dem_array <= total_water_level) & valid_mask

    # Identify ocean seed cells along the border of the raster where elevation <= sea_level_datum_m
    n_rows, n_cols = dem_array.shape
    border_mask = np.zeros_like(dem_array, dtype=bool)
    border_mask[0, :] = True
    border_mask[-1, :] = True
    border_mask[:, 0] = True
    border_mask[:, -1] = True

    ocean_seeds = border_mask & (dem_array <= sea_level_datum_m) & valid_mask

    # If no border seed found, take lowest elevation cells as ocean entry
    if not np.any(ocean_seeds):
        min_elev = np.nanmin(dem_array)
        ocean_seeds = (dem_array <= min_elev) & valid_mask

    # Label connected candidate regions using 8-connectivity
    structure = np.ones((3, 3), dtype=int)
    labeled_regions, num_regions = label(candidate_submerged, structure=structure)

    # Find labels that touch any ocean seed cell
    ocean_labels = np.unique(labeled_regions[ocean_seeds])
    ocean_labels = ocean_labels[ocean_labels > 0]

    # Connected inundated mask is only the components connected to ocean seeds
    connected_inundated = np.isin(labeled_regions, ocean_labels)

    # Newly flooded land (was above sea level datum initially, but now submerged)
    newly_flooded_land = connected_inundated & baseline_land
    flooded_land_pixels = int(np.sum(newly_flooded_land))

    # Depth grid: water level minus ground elevation for inundated cells
    depth_grid = np.zeros_like(dem_array, dtype=np.float32)
    depth_grid[connected_inundated] = np.maximum(
        0.0,
        total_water_level - dem_array[connected_inundated]
    )

    # Pixel area in m2, hectares, km2
    pixel_area_m2 = cellsize_m * cellsize_m
    flooded_area_ha = (flooded_land_pixels * pixel_area_m2) / 10000.0
    flooded_area_km2 = (flooded_land_pixels * pixel_area_m2) / 1000000.0
    total_land_ha = (total_land_pixels * pixel_area_m2) / 10000.0

    flooded_pct = (flooded_land_pixels / total_land_pixels * 100.0) if total_land_pixels > 0 else 0.0

    # Depth statistics
    flooded_depths = depth_grid[newly_flooded_land]
    mean_depth = float(np.mean(flooded_depths)) if len(flooded_depths) > 0 else 0.0
    max_depth = float(np.max(flooded_depths)) if len(flooded_depths) > 0 else 0.0

    # Flood hazard zoning
    shallow_pixels = int(np.sum((flooded_depths > 0.0) & (flooded_depths <= 0.5)))
    moderate_pixels = int(np.sum((flooded_depths > 0.5) & (flooded_depths <= 1.5)))
    severe_pixels = int(np.sum(flooded_depths > 1.5))

    metrics = {
        "water_level_rise_m": round(water_level_rise_m, 2),
        "storm_surge_m": round(storm_surge_m, 2),
        "total_water_elevation_m": round(total_water_level, 2),
        "total_land_area_ha": round(total_land_ha, 2),
        "inundated_land_area_ha": round(flooded_area_ha, 2),
        "inundated_area_ha": round(flooded_area_ha, 2),
        "submerged_land_area_ha": round(flooded_area_ha, 2),
        "inundated_land_area_km2": round(flooded_area_km2, 4),
        "land_inundation_percentage": round(flooded_pct, 2),
        "mean_inundation_depth_m": round(mean_depth, 2),
        "max_inundation_depth_m": round(max_depth, 2),
        "hazard_breakdown_ha": {
            "shallow_under_0_5m_ha": round((shallow_pixels * pixel_area_m2) / 10000.0, 2),
            "moderate_0_5m_to_1_5m_ha": round((moderate_pixels * pixel_area_m2) / 10000.0, 2),
            "severe_over_1_5m_ha": round((severe_pixels * pixel_area_m2) / 10000.0, 2)
        }
    }

    return newly_flooded_land, depth_grid, metrics


def inundation_to_geojson(
    flooded_mask: Any,
    depth_grid: Optional[np.ndarray] = None,
    bbox: Optional[List[float]] = None
) -> Dict[str, Any]:
    """Serialize connected inundation extents to GeoJSON FeatureCollection."""
    features = []

    if isinstance(flooded_mask, dict):
        # Passed metrics dictionary
        metrics = flooded_mask
        bbox = metrics.get("bbox", [22.8, 38.6, 23.2, 38.9])
        min_lon, min_lat, max_lon, max_lat = bbox
        poly = [
            [round(min_lon, 6), round(min_lat, 6)],
            [round(max_lon, 6), round(min_lat, 6)],
            [round(max_lon, 6), round(max_lat, 6)],
            [round(min_lon, 6), round(max_lat, 6)],
            [round(min_lon, 6), round(min_lat, 6)]
        ]
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [poly]
            },
            "properties": {
                "feature_type": "INUNDATION_ZONE",
                "water_level_rise_m": metrics.get("water_level_rise_m"),
                "inundated_area_ha": metrics.get("inundated_land_area_ha"),
                "submerged_land_area_ha": metrics.get("inundated_land_area_ha"),
                "land_inundation_percentage": metrics.get("land_inundation_percentage"),
                "mean_depth_m": metrics.get("mean_inundation_depth_m"),
                "directive": "EU Floods Directive (2007/60/EC Art. 6)"
            }
        })
        return {
            "type": "FeatureCollection",
            "features": features
        }

    # Otherwise, numpy arrays passed
    if bbox is None:
        bbox = [22.8, 38.6, 23.2, 38.9]
    min_lon, min_lat, max_lon, max_lat = bbox
    n_rows, n_cols = flooded_mask.shape

    step_r = max(1, n_rows // 15)
    step_c = max(1, n_cols // 15)

    for r in range(0, n_rows, step_r):
        for c in range(0, n_cols, step_c):
            if flooded_mask[r, c]:
                lat = max_lat - (r / max(1, n_rows - 1)) * (max_lat - min_lat)
                lon = min_lon + (c / max(1, n_cols - 1)) * (max_lon - min_lon)
                depth = float(depth_grid[r, c]) if depth_grid is not None else 0.5

                if depth > 1.5:
                    zone = "CRITICAL_INUNDATION"
                elif depth > 0.5:
                    zone = "MODERATE_INUNDATION"
                else:
                    zone = "SHALLOW_INUNDATION"

                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [round(lon, 6), round(lat, 6)]
                    },
                    "properties": {
                        "water_depth_m": round(depth, 2),
                        "hazard_zone": zone,
                        "directive": "EU Floods Directive Art. 6"
                    }
                })

    return {
        "type": "FeatureCollection",
        "features": features
    }


def inundation_to_csv(metrics: Dict[str, Any]) -> str:
    """Serialize sea level rise inundation metrics to tabular CSV format."""
    lines = [
        "metric,value,unit",
        f"water_level_rise_m,{metrics.get('water_level_rise_m', 0.0)},meters",
        f"water_level_rise,{metrics.get('water_level_rise_m', 0.0)},meters",
        f"storm_surge_m,{metrics.get('storm_surge_m', 0.0)},meters",
        f"total_water_elevation_m,{metrics.get('total_water_elevation_m', 0.0)},meters",
        f"total_land_area_ha,{metrics.get('total_land_area_ha', 0.0)},hectares",
        f"inundated_land_area_ha,{metrics.get('inundated_land_area_ha', 0.0)},hectares",
        f"inundated_area_ha,{metrics.get('inundated_land_area_ha', 0.0)},hectares",
        f"land_inundation_percentage,{metrics.get('land_inundation_percentage', 0.0)},percent",
        f"mean_inundation_depth_m,{metrics.get('mean_inundation_depth_m', 0.0)},meters",
        f"max_inundation_depth_m,{metrics.get('max_inundation_depth_m', 0.0)},meters"
    ]
    hazard = metrics.get("hazard_breakdown_ha", {})
    for k, v in hazard.items():
        lines.append(f"{k},{v},hectares")
    return "\n".join(lines)

