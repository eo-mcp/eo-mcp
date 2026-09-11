"""Sentinel-1 Synthetic Aperture Radar (SAR) Backscatter & Flood Detection Engine."""

from typing import Dict, Any, Tuple
import numpy as np


def linear_to_db(linear_amplitude: np.ndarray) -> np.ndarray:
    """
    Convert SAR linear amplitude or intensity to decibels (dB):
    sigma0_dB = 10 * log10(intensity + epsilon)
    """
    linear = np.maximum(linear_amplitude.astype(np.float32), 1e-6)
    return 10.0 * np.log10(linear)


def detect_water_mask(
    sar_db: np.ndarray,
    threshold_db: float = -16.0
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Threshold SAR backscatter to identify specular water reflection (calm water).
    Calm open water reflects radar pulses specularly away from the sensor, appearing dark (typically < -16 dB).

    Returns:
        (water_mask_boolean, summary_stats)
    """
    water_mask = (sar_db < threshold_db) & (~np.isnan(sar_db))
    total_valid = np.sum(~np.isnan(sar_db))
    water_pixels = np.sum(water_mask)

    water_percent = (water_pixels / total_valid * 100.0) if total_valid > 0 else 0.0

    return water_mask, {
        "threshold_db": threshold_db,
        "water_pixel_count": int(water_pixels),
        "total_valid_pixels": int(total_valid),
        "water_coverage_percentage": round(float(water_percent), 2),
        "mean_backscatter_db": round(float(np.nanmean(sar_db)), 2)
    }
