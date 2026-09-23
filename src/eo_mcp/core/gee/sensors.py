"""Sensor registry, band harmonization, and QA cloud masking for GEE collections.

Spans 50+ years of satellite archives from Landsat 1 MSS (1972) to contemporary
Sentinel-2 SR Harmonized and Landsat 9 OLI. Harmonizes disparate band naming conventions
into a unified standard band namespace:
['Blue', 'Green', 'Red', 'NIR', 'SWIR1', 'SWIR2', 'RedEdge1', 'RedEdge2', 'RedEdge3', 'NIR_narrow']
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Earth Engine collection IDs keyed by internal sensor identifier
COLLECTIONS: Dict[str, str] = {
    "landsat_mss_l1": "LANDSAT/LM01/C02/T1",
    "landsat_mss_l2": "LANDSAT/LM02/C02/T1",
    "landsat_mss_l3": "LANDSAT/LM03/C02/T1",
    "landsat_mss_l4": "LANDSAT/LM04/C02/T1",
    "landsat_mss_l5": "LANDSAT/LM05/C02/T1",
    "landsat5_t1_sr": "LANDSAT/LT05/C02/T1_L2",
    "landsat7_t1_sr": "LANDSAT/LE07/C02/T1_L2",
    "landsat8_sr": "LANDSAT/LC08/C02/T1_L2",
    "landsat9_sr": "LANDSAT/LC09/C02/T1_L2",
    "sentinel2_sr": "COPERNICUS/S2_SR_HARMONIZED",
}

# Standardized core optical bands used across all harmonized composites
STANDARD_BANDS = ["Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2"]

# Landsat 5/7 TM/ETM+ (Collection 2 Level 2) mapping
LANDSAT57_BAND_MAP: Dict[str, str] = {
    "SR_B1": "Blue",
    "SR_B2": "Green",
    "SR_B3": "Red",
    "SR_B4": "NIR",
    "SR_B5": "SWIR1",
    "SR_B7": "SWIR2",
}

# Landsat 8/9 OLI (Collection 2 Level 2) mapping
LANDSAT89_BAND_MAP: Dict[str, str] = {
    "SR_B2": "Blue",
    "SR_B3": "Green",
    "SR_B4": "Red",
    "SR_B5": "NIR",
    "SR_B6": "SWIR1",
    "SR_B7": "SWIR2",
}

# Sentinel-2 SR Harmonized core optical bands
SENTINEL2_BAND_MAP: Dict[str, str] = {
    "B2": "Blue",
    "B3": "Green",
    "B4": "Red",
    "B8": "NIR",
    "B11": "SWIR1",
    "B12": "SWIR2",
}

# Sentinel-2 red-edge and narrow NIR bands
SENTINEL2_EXTRA_BANDS: Dict[str, str] = {
    "B5": "RedEdge1",
    "B6": "RedEdge2",
    "B7": "RedEdge3",
    "B8A": "NIR_narrow",
}

# Landsat MSS Collection 2 (B6 mapped to NIR for spectral index compatibility)
MSS_BAND_MAP: Dict[str, str] = {
    "B4": "Green",
    "B5": "Red",
    "B6": "NIR",
    "B7": "NIR2",
}


def get_sensors_for_year(year: int) -> List[str]:
    """Return era-appropriate sensor keys for a given calendar year, ordered by priority.

    Args:
        year: Target calendar year (1972 through present).

    Returns:
        List of sensor keys with primary sensor first and fallback sensors following.
    """
    if year <= 1978:
        return ["landsat_mss_l1", "landsat_mss_l2", "landsat_mss_l3"]
    if year <= 1982:
        return ["landsat_mss_l2", "landsat_mss_l3", "landsat_mss_l4"]
    if year <= 1984:
        return ["landsat_mss_l4", "landsat_mss_l5"]
    if year <= 1998:
        return ["landsat5_t1_sr"]
    if year <= 2012:
        return ["landsat5_t1_sr", "landsat7_t1_sr"]
    if year <= 2013:
        return ["landsat8_sr"]
    if year <= 2021:
        return ["sentinel2_sr", "landsat8_sr"]
    return ["sentinel2_sr", "landsat9_sr"]


def get_nominal_scale(sensor_key: str) -> int:
    """Return the nominal spatial resolution (pixel size in meters) for a sensor."""
    if sensor_key.startswith("landsat_mss_"):
        return 60
    if sensor_key.startswith("landsat"):
        return 30
    if sensor_key.startswith("sentinel2"):
        return 10
    return 30


def harmonized_bands_for(sensor_key: str) -> List[str]:
    """Return the list of harmonized band names produced by a given sensor."""
    if sensor_key in ("landsat5_t1_sr", "landsat7_t1_sr"):
        return list(LANDSAT57_BAND_MAP.values())
    if sensor_key in ("landsat8_sr", "landsat9_sr"):
        return list(LANDSAT89_BAND_MAP.values())
    if sensor_key == "sentinel2_sr":
        return list(SENTINEL2_BAND_MAP.values()) + list(SENTINEL2_EXTRA_BANDS.values())
    if sensor_key.startswith("landsat_mss_"):
        return list(MSS_BAND_MAP.values())
    raise ValueError(f"Unknown sensor key: {sensor_key}")


def mask_landsat_c2_sr(image: Any) -> Any:
    """Cloud and shadow masking for Landsat Collection 2 Level 2 (L5/7/8/9).

    Unpacks QA_PIXEL bit 3 (cloud) and bit 4 (cloud shadow).
    Applies Collection 2 Level 2 surface reflectance scaling (x * 0.0000275 - 0.2).
    """
    qa = image.select("QA_PIXEL")
    cloud_bit = 1 << 3
    shadow_bit = 1 << 4
    mask = qa.bitwiseAnd(cloud_bit).eq(0).And(qa.bitwiseAnd(shadow_bit).eq(0))
    optical = image.select("SR_B.*").multiply(0.0000275).add(-0.2)
    return image.addBands(optical, overwrite=True).updateMask(mask)


def mask_sentinel2_sr(image: Any) -> Any:
    """Cloud and shadow masking for Sentinel-2 SR Harmonized via SCL layer.

    Filters out SCL classes:
    - 3: Cloud shadow
    - 7: Unclassified
    - 8: Cloud medium probability
    - 9: Cloud high probability
    - 10: Thin cirrus
    Scales reflectance from integer DN to 0.0-1.0 range (divide by 10000).
    """
    scl = image.select("SCL")
    mask = (
        scl.neq(3)
        .And(scl.neq(7))
        .And(scl.neq(8))
        .And(scl.neq(9))
        .And(scl.neq(10))
    )
    core_bands = ["B2", "B3", "B4", "B8", "B11", "B12"]
    extra_bands = ["B5", "B6", "B7", "B8A"]
    optical = image.select(core_bands + extra_bands).divide(10000.0)
    return image.addBands(optical, overwrite=True).updateMask(mask)


def mask_mss_c2(image: Any) -> Any:
    """Cloud masking for Landsat MSS Collection 2 using QA_PIXEL bits 3 and 4."""
    qa = image.select("QA_PIXEL")
    mask = qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0))
    return image.updateMask(mask)


def convert_mss_toa(image: Any) -> Any:
    """Convert Landsat MSS raw DN to Top of Atmosphere (TOA) reflectance."""
    import ee
    return ee.Algorithms.Landsat.TOA(image)


def harmonize_landsat57(image: Any) -> Any:
    """Select and rename Landsat 5/7 TM/ETM+ bands to standard harmonized names."""
    return image.select(list(LANDSAT57_BAND_MAP.keys()), list(LANDSAT57_BAND_MAP.values()))


def harmonize_landsat89(image: Any) -> Any:
    """Select and rename Landsat 8/9 OLI bands to standard harmonized names."""
    return image.select(list(LANDSAT89_BAND_MAP.keys()), list(LANDSAT89_BAND_MAP.values()))


def harmonize_sentinel2(image: Any) -> Any:
    """Select and rename Sentinel-2 SR bands to standard harmonized names."""
    all_bands = {**SENTINEL2_BAND_MAP, **SENTINEL2_EXTRA_BANDS}
    return image.select(list(all_bands.keys()), list(all_bands.values()))


def harmonize_mss(image: Any) -> Any:
    """Select and rename Landsat MSS bands to standard harmonized names."""
    return image.select(list(MSS_BAND_MAP.keys()), list(MSS_BAND_MAP.values()))


def get_collection(sensor_key: str, aoi: Any, start_date: str, end_date: str) -> Any:
    """Build a filtered, cloud-masked, harmonized ee.ImageCollection for a single sensor.

    Args:
        sensor_key: Sensor key from COLLECTIONS (e.g. 'sentinel2_sr', 'landsat8_sr').
        aoi: ee.Geometry region of interest.
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).

    Returns:
        ee.ImageCollection with cloud masks applied and bands harmonized to standard names.
    """
    import ee

    if sensor_key not in COLLECTIONS:
        raise ValueError(f"Unknown sensor key: {sensor_key}. Supported: {list(COLLECTIONS.keys())}")

    collection_id = COLLECTIONS[sensor_key]
    col = ee.ImageCollection(collection_id).filterBounds(aoi).filterDate(start_date, end_date)

    if sensor_key in ("landsat5_t1_sr", "landsat7_t1_sr"):
        return col.map(mask_landsat_c2_sr).map(harmonize_landsat57)
    if sensor_key in ("landsat8_sr", "landsat9_sr"):
        return col.map(mask_landsat_c2_sr).map(harmonize_landsat89)
    if sensor_key == "sentinel2_sr":
        return col.map(mask_sentinel2_sr).map(harmonize_sentinel2)
    if sensor_key.startswith("landsat_mss_"):
        return col.map(mask_mss_c2).map(convert_mss_toa).map(harmonize_mss)

    raise ValueError(f"Unhandled sensor harmonization: {sensor_key}")
