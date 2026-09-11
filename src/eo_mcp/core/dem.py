"""Copernicus DEM GLO-30 Digital Elevation & Slope Terrain Engine."""

from typing import Tuple, Dict, Any
import numpy as np


def compute_slope_and_aspect(elevation_grid: np.ndarray, cellsize_m: float = 30.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate terrain slope (in degrees) and aspect (in degrees 0-360) from a 2D elevation raster.
    Uses standard Horn / Zevenbergen-Thorne finite difference algorithm.
    """
    if elevation_grid.ndim == 3:
        elevation_grid = elevation_grid[0]

    # Calculate gradients
    dy, dx = np.gradient(elevation_grid, cellsize_m)
    
    # Slope in radians and degrees
    slope_rad = np.arctan(np.sqrt(dx * dx + dy * dy))
    slope_deg = np.degrees(slope_rad)

    # Aspect in degrees (0 = North, 90 = East, 180 = South, 270 = West)
    aspect_rad = np.arctan2(-dx, dy)
    aspect_deg = np.degrees(aspect_rad)
    aspect_deg = np.where(aspect_deg < 0, 360.0 + aspect_deg, aspect_deg)

    return slope_deg, aspect_deg


def summarize_terrain(dem_array: np.ndarray, cellsize_m: float = 30.0) -> Dict[str, Any]:
    """Compute summary terrain statistics for an elevation array."""
    valid_elev = dem_array[~np.isnan(dem_array)]
    if len(valid_elev) == 0:
        return {
            "min_elevation_m": 0.0,
            "max_elevation_m": 0.0,
            "mean_elevation_m": 0.0,
            "mean_slope_degrees": 0.0,
            "max_slope_degrees": 0.0
        }

    slope_deg, _ = compute_slope_and_aspect(dem_array, cellsize_m)
    valid_slope = slope_deg[~np.isnan(slope_deg)]

    return {
        "min_elevation_m": float(np.min(valid_elev)),
        "max_elevation_m": float(np.max(valid_elev)),
        "mean_elevation_m": float(np.mean(valid_elev)),
        "mean_slope_degrees": float(np.mean(valid_slope)) if len(valid_slope) > 0 else 0.0,
        "max_slope_degrees": float(np.max(valid_slope)) if len(valid_slope) > 0 else 0.0
    }
