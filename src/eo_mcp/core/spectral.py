"""Spectral band math and vegetation/water/burn index computation engine."""

from typing import Dict, Tuple
import numpy as np


def compute_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """
    Normalized Difference Vegetation Index: (NIR - Red) / (NIR + Red)
    Scale: -1.0 to 1.0 (Dense vegetation: 0.6 - 0.9)
    """
    nir = nir.astype(np.float32)
    red = red.astype(np.float32)
    denominator = nir + red
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = np.where(denominator != 0, (nir - red) / denominator, np.nan)
    return np.clip(ndvi, -1.0, 1.0)


def compute_ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """
    Normalized Difference Water Index (McFeeters): (Green - NIR) / (Green + NIR)
    Positive values represent open water bodies.
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
