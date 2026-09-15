"""
Spectral band math and vegetation/water/burn index computation engine.

References:
- Rouse, J. W., Haas, R. H., Schell, J. A., & Deering, D. W. (1974). Monitoring
  vegetation systems in the Great Plains with ERTS. Third Earth Resources Technology
  Satellite-1 Symposium, NASA SP-351, 1, 309-317. NASA Accession No. N74-30724.
- Tucker, C. J. (1979). Red and photographic infrared linear combinations for
  monitoring vegetation. Remote Sensing of Environment, 8(2), 127-150.
  DOI: 10.1016/0034-4257(79)90013-0
- McFeeters, S. K. (1996). The use of the Normalized Difference Water Index (NDWI)
  in the delineation of open water features. International Journal of Remote Sensing,
  17(7), 1425-1432. DOI: 10.1080/01431169608948714
- Gao, B.-C. (1996). NDWI—A normalized difference water index for remote sensing of
  vegetation liquid water from space. Remote Sensing of Environment, 58(3), 257-266.
  DOI: 10.1016/S0034-4257(96)00067-3
- Key, C. H., & Benson, N. C. (2006). Landscape Assessment (LA): Sampling and analysis
  methods. In FIREMON: Fire Effects Monitoring and Inventory System, USDA Forest
  Service RMRS-GTR-164-CD, pp. LA 1-55.
- Huete, A., Didan, K., Miura, T., Rodriguez, E. P., Gao, X., & Ferreira, L. G. (2002).
  Overview of the radiometric and biophysical performance of the MODIS vegetation
  indices. Remote Sensing of Environment, 83(1–2), 195-213.
  DOI: 10.1016/S0034-4257(02)00096-2
"""

from typing import Dict, Tuple
import numpy as np


def compute_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """
    Normalized Difference Vegetation Index: (NIR - Red) / (NIR + Red)
    Scale: -1.0 to 1.0 (Dense vegetation: 0.6 - 0.9)

    References:
    - Rouse et al. (1974), NASA SP-351, 1, 309-317.
    - Tucker, C. J. (1979). Remote Sensing of Environment, 8(2), 127-150.
      DOI: 10.1016/0034-4257(79)90013-0
    """
    nir = nir.astype(np.float32)
    red = red.astype(np.float32)
    denominator = nir + red
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = np.where(denominator != 0, (nir - red) / denominator, np.nan)
    return np.clip(ndvi, -1.0, 1.0)


def compute_ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """
    Normalized Difference Water Index: (Green - NIR) / (Green + NIR)
    Positive values represent open water bodies.

    References:
    - McFeeters, S. K. (1996). International Journal of Remote Sensing, 17(7), 1425-1432.
      DOI: 10.1080/01431169608948714
    - Gao, B.-C. (1996). Remote Sensing of Environment, 58(3), 257-266.
      DOI: 10.1016/S0034-4257(96)00067-3
    """
    green = green.astype(np.float32)
    nir = nir.astype(np.float32)
    denominator = green + nir
    with np.errstate(divide="ignore", invalid="ignore"):
        ndwi = np.where(denominator != 0, (green - nir) / denominator, np.nan)
    return np.clip(ndwi, -1.0, 1.0)


def compute_nbr(nir: np.ndarray, swir2: np.ndarray) -> np.ndarray:
    """
    Normalized Burn Ratio: (NIR - SWIR2) / (NIR + SWIR2)
    Used to highlight burned areas and estimate wildfire severity.

    References:
    - Key, C. H., & Benson, N. C. (2006). USDA Forest Service RMRS-GTR-164-CD, pp. LA 1-55.
    """
    nir = nir.astype(np.float32)
    swir2 = swir2.astype(np.float32)
    denominator = nir + swir2
    with np.errstate(divide="ignore", invalid="ignore"):
        nbr = np.where(denominator != 0, (nir - swir2) / denominator, np.nan)
    return np.clip(nbr, -1.0, 1.0)


def compute_evi(nir: np.ndarray, red: np.ndarray, blue: np.ndarray, g: float = 2.5, c1: float = 6.0, c2: float = 7.5, l: float = 1.0) -> np.ndarray:
    """
    Enhanced Vegetation Index: G * ((NIR - Red) / (NIR + C1*Red - C2*Blue + L))
    Atmospherically corrected vegetation index optimized for high biomass canopy.

    References:
    - Huete, A., et al. (2002). Remote Sensing of Environment, 83(1-2), 195-213.
      DOI: 10.1016/S0034-4257(02)00096-2
    """
    nir = nir.astype(np.float32)
    red = red.astype(np.float32)
    blue = blue.astype(np.float32)
    denominator = nir + (c1 * red) - (c2 * blue) + l
    with np.errstate(divide="ignore", invalid="ignore"):
        evi = np.where(denominator != 0, g * ((nir - red) / denominator), np.nan)
    return np.clip(evi, -1.0, 1.0)


def calculate_array_stats(arr: np.ndarray) -> Dict[str, float]:
    """Calculate non-NaN summary statistics for an index array."""
    valid = arr[~np.isnan(arr)]
    if len(valid) == 0:
        return {"mean": 0.0, "min": 0.0, "max": 0.0, "std": 0.0, "count": 0}
    return {
        "mean": float(np.mean(valid)),
        "min": float(np.min(valid)),
        "max": float(np.max(valid)),
        "std": float(np.std(valid)),
        "count": int(len(valid))
    }
