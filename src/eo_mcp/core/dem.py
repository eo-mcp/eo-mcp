"""
Copernicus DEM GLO-30 Digital Elevation & Slope Terrain Engine.

References:
- Horn, B. K. P. (1981). Hill shading and the reflectance map. Proceedings of the IEEE,
  69(1), 14-47. DOI: 10.1109/PROC.1981.11918
- Zevenbergen, L. W., & Thorne, C. R. (1987). Quantitative analysis of land surface
  topography. Earth Surface Processes and Landforms, 12(1), 47-56.
  DOI: 10.1002/esp.3290120107
- Guth, P. L., & Geoffroy, T. M. (2021). LiDAR point cloud and ICESat-2 evaluation of
  1 second global digital elevation models: Copernicus wins. Transactions in GIS,
  25(5), 2245-2261. DOI: 10.1111/tgis.12825
- European Space Agency. (2020). Copernicus Complex Digital Elevation Model (COP-DEM)
  Validation Report. Issue 4.0, Airbus Defence and Space & ESA.
"""

from typing import Tuple, Dict, Any
import numpy as np


def compute_slope_and_aspect(elevation_grid: np.ndarray, cellsize_m: float = 30.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate terrain slope (in degrees) and aspect (in degrees 0-360) from a 2D elevation raster.
    Uses central finite difference gradient estimation (Horn, 1981; Zevenbergen & Thorne, 1987).

    References:
    - Horn, B. K. P. (1981). Proceedings of the IEEE, 69(1), 14-47.
      DOI: 10.1109/PROC.1981.11918
    - Zevenbergen, L. W., & Thorne, C. R. (1987). Earth Surface Processes and Landforms,
      12(1), 47-56. DOI: 10.1002/esp.3290120107
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


def compute_terrain_ruggedness_index(elevation_grid: np.ndarray) -> np.ndarray:
    """
    Calculate Terrain Ruggedness Index (TRI) according to Riley et al. (1999).
    TRI = sqrt(sum((z_ij - z_00)^2)) over the 8-cell Moore neighborhood.

    Reference:
    - Riley, S. J., DeGloria, S. D., & Elliot, R. (1999). Index that quantifies topographic
      heterogeneity. Intermountain Journal of Sciences, 5(1-4), 23-27.
    """
    if elevation_grid.ndim == 3:
        elevation_grid = elevation_grid[0]

    h, w = elevation_grid.shape
    tri = np.zeros_like(elevation_grid, dtype=np.float32)

    # Pad elevation grid to handle boundary conditions
    padded = np.pad(elevation_grid, 1, mode="edge")

    # Accumulate squared differences across 8 neighbors
    diff_sq_sum = np.zeros((h, w), dtype=np.float64)
    for dy in [-1, 0, 1]:
        for dx in [-1, 0, 1]:
            if dy == 0 and dx == 0:
                continue
            neighbor = padded[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w]
            diff = neighbor - elevation_grid
            diff_sq_sum += diff * diff

    tri = np.sqrt(diff_sq_sum).astype(np.float32)
    return tri


def compute_topographic_wetness_index(
    elevation_grid: np.ndarray, cellsize_m: float = 30.0
) -> np.ndarray:
    """
    Calculate Topographic Wetness Index (TWI) based on Beven & Kirkby (1979).
    TWI = ln(a / tan(beta))
    where a is the specific catchment area and beta is the slope angle in radians.

    Reference:
    - Beven, K. J., & Kirkby, M. J. (1979). A physically based, variable contributing area
      model of basin hydrology. Hydrological Sciences Bulletin, 24(1), 43-69.
    """
    if elevation_grid.ndim == 3:
        elevation_grid = elevation_grid[0]

    slope_deg, _ = compute_slope_and_aspect(elevation_grid, cellsize_m)
    slope_rad = np.radians(np.maximum(slope_deg, 0.05))  # prevent division by zero

    # Approximate specific catchment area via inverse gradient accumulation proxy
    # In standard hydrology, catchment area accumulates along flow paths.
    # Here we estimate local upslope contributing area using inverted elevation convergence.
    dy, dx = np.gradient(elevation_grid, cellsize_m)
    convergence = np.maximum(1.0, cellsize_m * (1.0 + np.abs(dx) + np.abs(dy)))
    
    tan_beta = np.tan(slope_rad)
    tan_beta = np.maximum(tan_beta, 1e-4)

    twi = np.log(convergence / tan_beta).astype(np.float32)
    return twi


def summarize_terrain(dem_array: np.ndarray, cellsize_m: float = 30.0) -> Dict[str, Any]:
    """Compute summary terrain statistics for an elevation array including slope, TWI, and TRI."""
    valid_elev = dem_array[~np.isnan(dem_array)]
    if len(valid_elev) == 0:
        return {
            "min_elevation_m": 0.0,
            "max_elevation_m": 0.0,
            "mean_elevation_m": 0.0,
            "mean_slope_degrees": 0.0,
            "max_slope_degrees": 0.0,
            "mean_twi": 0.0,
            "mean_tri_m": 0.0
        }

    slope_deg, _ = compute_slope_and_aspect(dem_array, cellsize_m)
    valid_slope = slope_deg[~np.isnan(slope_deg)]
    
    twi_arr = compute_topographic_wetness_index(dem_array, cellsize_m)
    valid_twi = twi_arr[~np.isnan(twi_arr)]

    tri_arr = compute_terrain_ruggedness_index(dem_array)
    valid_tri = tri_arr[~np.isnan(tri_arr)]

    return {
        "min_elevation_m": float(np.min(valid_elev)),
        "max_elevation_m": float(np.max(valid_elev)),
        "mean_elevation_m": float(np.mean(valid_elev)),
        "mean_slope_degrees": float(np.mean(valid_slope)) if len(valid_slope) > 0 else 0.0,
        "max_slope_degrees": float(np.max(valid_slope)) if len(valid_slope) > 0 else 0.0,
        "mean_twi": float(np.mean(valid_twi)) if len(valid_twi) > 0 else 0.0,
        "mean_tri_m": float(np.mean(valid_tri)) if len(valid_tri) > 0 else 0.0
    }

