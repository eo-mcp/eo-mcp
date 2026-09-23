"""Config-driven spectral index calculation and band math for Google Earth Engine.

Operates on standardized harmonized band names (Blue, Green, Red, NIR, SWIR1, SWIR2,
RedEdge1, etc.). Validates band availability per sensor era, computing only mathematically
feasible indices and cleanly reporting omitted indices when historical sensors lack requisite bands.
Supports custom user-defined band-math expressions.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Set, Tuple

# Required bands per spectral index
KNOWN_INDICES: Dict[str, List[str]] = {
    "NDVI": ["NIR", "Red"],
    "SAVI": ["NIR", "Red"],
    "EVI": ["NIR", "Red", "Blue"],
    "NDMI": ["NIR", "SWIR1"],
    "NBR": ["NIR", "SWIR2"],
    "NDWI": ["Green", "NIR"],
    "NDBI": ["SWIR1", "NIR"],
    "NDRE": ["NIR", "RedEdge1"],
    "CIre": ["NIR", "RedEdge1"],
    "GreenRed": ["Green", "Red"],
    "BlueGreenNIR": ["Blue", "Green", "NIR"],
}


def _ndvi(img: Any) -> Any:
    return img.normalizedDifference(["NIR", "Red"]).rename("NDVI")


def _savi(img: Any) -> Any:
    # Soil Adjusted Vegetation Index with L=0.5
    return img.expression(
        "((NIR - RED) / (NIR + RED + 0.5)) * 1.5",
        {"NIR": img.select("NIR"), "RED": img.select("Red")},
    ).rename("SAVI")


def _evi(img: Any) -> Any:
    # Enhanced Vegetation Index
    return img.expression(
        "2.5 * (NIR - RED) / (NIR + 6.0 * RED - 7.5 * BLUE + 1.0)",
        {"NIR": img.select("NIR"), "RED": img.select("Red"), "BLUE": img.select("Blue")},
    ).rename("EVI")


def _ndmi(img: Any) -> Any:
    # Normalized Difference Moisture Index
    return img.normalizedDifference(["NIR", "SWIR1"]).rename("NDMI")


def _nbr(img: Any) -> Any:
    # Normalized Burn Ratio
    return img.normalizedDifference(["NIR", "SWIR2"]).rename("NBR")


def _ndwi(img: Any) -> Any:
    # Normalized Difference Water Index (McFeeters)
    return img.normalizedDifference(["Green", "NIR"]).rename("NDWI")


def _ndbi(img: Any) -> Any:
    # Normalized Difference Built-Up Index
    return img.normalizedDifference(["SWIR1", "NIR"]).rename("NDBI")


def _ndre(img: Any) -> Any:
    # Normalized Difference Red Edge
    return img.normalizedDifference(["NIR", "RedEdge1"]).rename("NDRE")


def _cire(img: Any) -> Any:
    # Chlorophyll Index Red Edge
    return img.expression(
        "NIR / RE1 - 1",
        {"NIR": img.select("NIR"), "RE1": img.select("RedEdge1")},
    ).rename("CIre")


def _green_red(img: Any) -> Any:
    return img.expression(
        "GREEN / RED",
        {"GREEN": img.select("Green"), "RED": img.select("Red")},
    ).rename("GreenRed")


def _blue_green_nir(img: Any) -> Any:
    return img.expression(
        "(BLUE + GREEN) / NIR",
        {"BLUE": img.select("Blue"), "GREEN": img.select("Green"), "NIR": img.select("NIR")},
    ).rename("BlueGreenNIR")


INDEX_BUILDERS: Dict[str, Callable[[Any], Any]] = {
    "NDVI": _ndvi,
    "SAVI": _savi,
    "EVI": _evi,
    "NDMI": _ndmi,
    "NBR": _nbr,
    "NDWI": _ndwi,
    "NDBI": _ndbi,
    "NDRE": _ndre,
    "CIre": _cire,
    "GreenRed": _green_red,
    "BlueGreenNIR": _blue_green_nir,
}


def computable_indices(index_names: List[str], available_bands: List[str]) -> List[str]:
    """Identify which requested indices can be computed given the available bands.

    Args:
        index_names: Requested index keys (e.g. ['NDVI', 'NDRE', 'EVI']).
        available_bands: List of band names present on the target image.

    Returns:
        Filtered list of index keys whose requisite bands are all present.
    """
    band_set = set(available_bands)
    valid = []
    for name in index_names:
        norm_name = name.strip()
        # Case-insensitive match against KNOWN_INDICES
        matched_key = next((k for k in KNOWN_INDICES if k.lower() == norm_name.lower()), None)
        if matched_key and set(KNOWN_INDICES[matched_key]) <= band_set:
            valid.append(matched_key)
    return valid


def add_indices(
    image: Any,
    index_names: List[str],
    available_bands: List[str],
) -> Tuple[Any, List[str], List[str]]:
    """Add computable spectral index bands to an ee.Image.

    Args:
        image: ee.Image object carrying harmonized bands.
        index_names: List of requested spectral index names.
        available_bands: List of bands currently present on image.

    Returns:
        Tuple of (new_image, computed_index_names, skipped_index_names).
    """
    to_compute = computable_indices(index_names, available_bands)
    norm_requested = [i.strip() for i in index_names]
    skipped = [i for i in norm_requested if not any(k.lower() == i.lower() for k in to_compute)]

    result = image
    for idx_name in to_compute:
        builder = INDEX_BUILDERS[idx_name]
        index_band = builder(result)
        result = result.addBands(index_band)

    return result, to_compute, skipped


def evaluate_custom_expression(
    image: Any,
    expression: str,
    output_band_name: str = "custom_index",
) -> Any:
    """Evaluate an arbitrary band math expression on an ee.Image.

    Example expression: '(NIR - Red) / (NIR + Red)' or '(B8 - B4) / (B8 + B4)'.

    Args:
        image: ee.Image object.
        expression: Mathematical expression string.
        output_band_name: Name for the resulting single-band image.

    Returns:
        Single-band ee.Image.
    """
    band_names = image.bandNames().getInfo()
    band_map = {b: image.select(b) for b in band_names}
    return image.expression(expression, band_map).rename(output_band_name)
