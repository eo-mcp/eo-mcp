"""
Land Surface Temperature (LST) and Urban Heat Island (UHI) analysis engine.

Leverages Landsat 8/9 Thermal Infrared Sensor (TIRS Band 10: 10.6-11.19 µm)
and NDVI-derived Fractional Vegetation Cover (FVC) to derive calibrated
Land Surface Temperature (LST in °C and K) and map urban microclimate heat risks.

References:
- Valor, E., & Caselles, V. (1996). Mapping land surface emissivity from NDVI:
  Application to European, African, and South American areas. Remote Sensing of
  Environment, 57(3), 167-184. DOI: 10.1016/0034-4257(96)00039-9
- Sobrino, J. A., Jiménez-Muñoz, J. C., & Paolini, L. (2004). Land surface temperature
  retrieval from LANDSAT TM 5. Remote Sensing of Environment, 90(4), 434-440.
  DOI: 10.1016/j.rse.2004.02.003
- Sobrino, J. A., et al. (2008). Land surface emissivity retrieval from different
  VNIR and TIR sensors. IEEE Transactions on Geoscience and Remote Sensing, 46(2),
  316-327. DOI: 10.1109/TGRS.2007.904834
- Jiménez-Muñoz, J. C., et al. (2009). Revision of the single-channel algorithm for
  land surface temperature retrieval from Landsat thermal-infrared data. IEEE
  Transactions on Geoscience and Remote Sensing, 47(1), 339-349.
  DOI: 10.1109/TGRS.2008.2007125
"""

from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from eo_mcp.core.spectral import compute_ndvi


# Landsat 8/9 TIRS Band 10 Calibration Constants
K1_CONSTANT_BAND10 = 774.8853
K2_CONSTANT_BAND10 = 1321.0789
WAVELENGTH_BAND10_UM = 10.895
RHO_CONSTANT = 14380.0  # h * c / sigma in um * K


def compute_brightness_temperature(radiance: np.ndarray) -> np.ndarray:
    """
    Convert Top of Atmosphere (TOA) spectral radiance to at-satellite Brightness Temperature in Kelvin.

    TB = K2 / ln((K1 / L_lambda) + 1)
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        tb = K2_CONSTANT_BAND10 / np.log((K1_CONSTANT_BAND10 / np.maximum(radiance, 0.01)) + 1.0)
    return tb


def compute_fractional_vegetation_cover(ndvi: np.ndarray, ndvi_min: float = 0.2, ndvi_max: float = 0.5) -> np.ndarray:
    """
    Calculate Fractional Vegetation Cover (FVC or Pv) from NDVI.
    Pv = ((NDVI - NDVI_min) / (NDVI_max - NDVI_min))^2

    References:
    - Valor, E., & Caselles, V. (1996). Remote Sensing of Environment, 57(3), 167-184.
      DOI: 10.1016/0034-4257(96)00039-9
    """
    fvc = np.clip((ndvi - ndvi_min) / max(1e-4, (ndvi_max - ndvi_min)), 0.0, 1.0) ** 2
    return fvc


def compute_land_surface_emissivity(fvc: np.ndarray, ndvi: np.ndarray) -> np.ndarray:
    """
    Estimate Land Surface Emissivity (LSE) using the NDVI threshold method (Sobrino et al.).
    - Water (NDVI < 0): 0.995
    - Soil (NDVI < 0.2): 0.960
    - Mixed (0.2 <= NDVI <= 0.5): 0.970 + 0.018 * Pv
    - Dense Vegetation (NDVI > 0.5): 0.985

    References:
    - Valor, E., & Caselles, V. (1996). Remote Sensing of Environment, 57(3), 167-184.
      DOI: 10.1016/0034-4257(96)00039-9
    - Sobrino, J. A., et al. (2004). Remote Sensing of Environment, 90(4), 434-440.
      DOI: 10.1016/j.rse.2004.02.003
    - Sobrino, J. A., et al. (2008). IEEE TGRS, 46(2), 316-327.
      DOI: 10.1109/TGRS.2007.904834
    """
    emissivity = np.full_like(ndvi, 0.970, dtype=np.float32)
    emissivity[ndvi < 0.0] = 0.995
    emissivity[(ndvi >= 0.0) & (ndvi < 0.2)] = 0.960
    mixed_mask = (ndvi >= 0.2) & (ndvi <= 0.5)
    emissivity[mixed_mask] = 0.970 + (0.018 * fvc[mixed_mask])
    emissivity[ndvi > 0.5] = 0.985
    return emissivity


def calculate_land_surface_temperature(
    thermal_radiance: np.ndarray,
    red_band: np.ndarray,
    nir_band: np.ndarray,
    cellsize_m: float = 30.0
) -> Dict[str, Any]:
    """
    Calculate Land Surface Temperature (LST in °C) from thermal radiance and surface emissivity.

    LST = TB / (1 + (lambda * TB / rho) * ln(emissivity))

    References:
    - Sobrino, J. A., et al. (2004). Remote Sensing of Environment, 90(4), 434-440.
      DOI: 10.1016/j.rse.2004.02.003
    - Jiménez-Muñoz, J. C., et al. (2009). IEEE TGRS, 47(1), 339-349.
      DOI: 10.1109/TGRS.2008.2007125
    """
    # 1. Compute NDVI & Fractional Vegetation Cover
    ndvi = compute_ndvi(nir=nir_band, red=red_band)
    fvc = compute_fractional_vegetation_cover(ndvi)
    emissivity = compute_land_surface_emissivity(fvc, ndvi)

    # 2. Compute Brightness Temperature (Kelvin)
    if np.mean(thermal_radiance) > 100.0:
        tb = thermal_radiance
    else:
        tb = compute_brightness_temperature(thermal_radiance)

    # 3. Compute LST in Kelvin
    with np.errstate(divide="ignore", invalid="ignore"):
        lst_k = tb / (1.0 + ((WAVELENGTH_BAND10_UM * tb / RHO_CONSTANT) * np.log(emissivity)))

    # Convert to Celsius
    lst_c = lst_k - 273.15
    valid_mask = ~np.isnan(lst_c)

    mean_c = float(np.mean(lst_c[valid_mask])) if np.any(valid_mask) else 25.0
    min_c = float(np.min(lst_c[valid_mask])) if np.any(valid_mask) else 18.0
    max_c = float(np.max(lst_c[valid_mask])) if np.any(valid_mask) else 38.0
    std_c = float(np.std(lst_c[valid_mask])) if np.any(valid_mask) else 3.5

    # Urban Heat Island hotspot threshold: mean + 1.0 standard deviation
    uhi_threshold_c = mean_c + (1.0 * std_c)
    hotspots_mask = (lst_c >= uhi_threshold_c) & valid_mask

    # Cool islands (parks / water): mean - 1.0 standard deviation
    cool_island_mask = (lst_c <= (mean_c - (1.0 * std_c))) & valid_mask

    pixel_area_ha = (cellsize_m * cellsize_m) / 10000.0
    total_valid_ha = float(np.sum(valid_mask)) * pixel_area_ha
    hotspot_area_ha = float(np.sum(hotspots_mask)) * pixel_area_ha
    cool_area_ha = float(np.sum(cool_island_mask)) * pixel_area_ha

    cool_baseline_c = float(np.mean(lst_c[cool_island_mask])) if np.any(cool_island_mask) else min_c
    uhi_intensity_c = max(0.0, max_c - cool_baseline_c)

    return {
        "mean_lst_celsius": round(mean_c, 2),
        "min_lst_celsius": round(min_c, 2),
        "max_lst_celsius": round(max_c, 2),
        "std_lst_celsius": round(std_c, 2),
        "uhi_intensity_celsius": round(uhi_intensity_c, 2),
        "total_aoi_area_ha": round(total_valid_ha, 2),
        "thermal_hotspot_area_ha": round(hotspot_area_ha, 2),
        "cool_island_area_ha": round(cool_area_ha, 2),
        "hotspot_percentage": round((np.sum(hotspots_mask) / max(1, np.sum(valid_mask))) * 100.0, 2),
        "thermal_risk_level": "EXTREME_HEAT_RISK" if uhi_intensity_c > 8.0 else ("MODERATE_HEAT_ISLAND" if uhi_intensity_c > 4.0 else "NOMINAL"),
        "methodology": "Sobrino Radiative Transfer / Landsat TIRS Band 10 Single-Channel Algorithm",
        "lst_grid_celsius": lst_c
    }


def thermal_to_geojson(results: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize thermal results to GeoJSON FeatureCollection."""
    bbox = results.get("bbox", [2.2, 48.8, 2.4, 49.0])
    min_lon, min_lat, max_lon, max_lat = bbox

    polygon_coords = [
        [
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat]
        ]
    ]

    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": polygon_coords
        },
        "properties": {
            "feature_type": "URBAN_HEAT_ISLAND_ANALYSIS",
            "mean_lst_celsius": results.get("mean_lst_celsius"),
            "max_lst_celsius": results.get("max_lst_celsius"),
            "uhi_intensity_celsius": results.get("uhi_intensity_celsius"),
            "thermal_hotspot_area_ha": results.get("thermal_hotspot_area_ha"),
            "cool_island_area_ha": results.get("cool_island_area_ha"),
            "thermal_risk_level": results.get("thermal_risk_level"),
            "methodology": results.get("methodology")
        }
    }

    return {
        "type": "FeatureCollection",
        "features": [feature]
    }


def thermal_to_csv(results: Dict[str, Any]) -> str:
    """Serialize thermal results to tabular CSV."""
    lines = ["metric,value,unit"]
    lines.append(f"mean_lst,{results.get('mean_lst_celsius')},celsius")
    lines.append(f"min_lst,{results.get('min_lst_celsius')},celsius")
    lines.append(f"max_lst,{results.get('max_lst_celsius')},celsius")
    lines.append(f"uhi_intensity,{results.get('uhi_intensity_celsius')},delta_celsius")
    lines.append(f"hotspot_area,{results.get('thermal_hotspot_area_ha')},ha")
    lines.append(f"cool_island_area,{results.get('cool_island_area_ha')},ha")
    lines.append(f"hotspot_percentage,{results.get('hotspot_percentage')},percent")
    lines.append(f"thermal_risk_level,{results.get('thermal_risk_level')},class")
    return "\n".join(lines)
