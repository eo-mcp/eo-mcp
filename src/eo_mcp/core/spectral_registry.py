"""Awesome Spectral Indices (ASI) Registry & Dynamic Formula Engine for eo-mcp.

Provides access to 200+ curated peer-reviewed spectral indices across:
- Vegetation (NDVI, EVI, SAVI, MSAVI, NDRE, GNDVI, MCARI, MTVI2, etc.)
- Water & Inundation (NDWI, MNDWI, AWEInsh, AWEIsh, WI, WRI, etc.)
- Burn & Wildfire (NBR, NBR2, BAI, MIRBI, CSI, GEMI, etc.)
- Urban & Built-Up (NDBI, UI, IBI, EBBI, BAEI, NDISI, NBAI, etc.)
- Soil & Geology (BSI, NDSI, NDSoI, Clay Minerals, Ferrous Iron, etc.)
- Snow & Ice (NDSI, S3, SWI)

References:
- Montero, D., et al. (2023). A standardized catalogue of spectral indices
  to advance the use of Earth Observation data. Scientific Data, 10(1), 197.
  DOI: 10.1038/s41597-023-02096-0
"""

import ast
import json
import os
from typing import Dict, List, Optional, Any, Union
import numpy as np

# Path to bundled spectral indices definitions
_RESOURCE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")
_INDICES_JSON_PATH = os.path.join(_RESOURCE_DIR, "spectral_indices.json")
_BANDS_JSON_PATH = os.path.join(_RESOURCE_DIR, "bands.json")

# Standard platform band translation table
# Maps generic ASI band tokens (N, R, G, B, S1, S2, RE1, etc.) to common STAC asset keys
PLATFORM_BAND_MAPPINGS: Dict[str, Dict[str, List[str]]] = {
    "sentinel-2": {
        "A": ["B01", "coastal", "aerosols"],
        "B": ["B02", "blue"],
        "G": ["B03", "green"],
        "R": ["B04", "red"],
        "RE1": ["B05", "rededge1"],
        "RE2": ["B06", "rededge2"],
        "RE3": ["B07", "rededge3"],
        "N": ["B08", "nir"],
        "N2": ["B8A", "nir09", "narrow_nir"],
        "WV": ["B09", "water_vapour"],
        "S1": ["B11", "swir16", "swir1"],
        "S2": ["B12", "swir22", "swir2"],
    },
    "landsat-8": {
        "A": ["coastal", "B1"],
        "B": ["blue", "B2"],
        "G": ["green", "B3"],
        "R": ["red", "B4"],
        "N": ["nir08", "nir", "B5"],
        "S1": ["swir16", "swir1", "B6"],
        "S2": ["swir22", "swir2", "B7"],
        "T1": ["lwir11", "thermal", "B10"],
        "T2": ["lwir12", "B11"],
    },
    "landsat-9": {
        "A": ["coastal", "B1"],
        "B": ["blue", "B2"],
        "G": ["green", "B3"],
        "R": ["red", "B4"],
        "N": ["nir08", "nir", "B5"],
        "S1": ["swir16", "swir1", "B6"],
        "S2": ["swir22", "swir2", "B7"],
        "T1": ["lwir11", "thermal", "B10"],
        "T2": ["lwir12", "B11"],
    },
    "planetscope": {
        "A": ["coastal_blue", "B1"],
        "B": ["blue", "B2"],
        "G": ["green", "B3"],
        "R": ["red", "B4"],
        "RE1": ["rededge", "B5"],
        "N": ["nir", "B6"],
    }
}

# Standard default parameters for indices with empirical constants
DEFAULT_CONSTANTS: Dict[str, float] = {
    "L": 1.0,         # Soil adjustment factor (SAVI, MSAVI)
    "C1": 6.0,        # Atmosphere resistance factor 1 (EVI)
    "C2": 7.5,        # Atmosphere resistance factor 2 (EVI)
    "g": 2.5,         # Gain factor (EVI)
    "gamma": 1.0,     # Weighting factor
    "alpha": 0.1,     # Empirical constant
    "sla": 1.0,       # Soil line slope
    "slb": 0.0,       # Soil line intercept
    "sigma": 0.5,     # Kernel width parameter
}


class SafeFormulaEvaluator(ast.NodeVisitor):
    """Safely evaluates an AST mathematical expression over NumPy arrays and scalar constants."""

    ALLOWED_FUNCS = {
        "sqrt": np.sqrt,
        "exp": np.exp,
        "log": np.log,
        "abs": np.abs,
        "maximum": np.maximum,
        "minimum": np.minimum,
        "clip": np.clip,
    }

    def __init__(self, variables: Dict[str, Any]):
        self.variables = variables

    def evaluate(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return self.evaluate(node.body)

        elif isinstance(node, ast.Constant):
            return node.value

        elif isinstance(node, ast.Name):
            if node.id in self.variables:
                return self.variables[node.id]
            if node.id in DEFAULT_CONSTANTS:
                return DEFAULT_CONSTANTS[node.id]
            raise ValueError(f"Undefined variable in spectral formula: '{node.id}'")

        elif isinstance(node, ast.UnaryOp):
            operand = self.evaluate(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand
            elif isinstance(node.op, ast.USub):
                return -operand
            raise TypeError(f"Unsupported unary operator: {type(node.op).__name__}")

        elif isinstance(node, ast.BinOp):
            left = self.evaluate(node.left)
            right = self.evaluate(node.right)

            with np.errstate(divide="ignore", invalid="ignore"):
                if isinstance(node.op, ast.Add):
                    return left + right
                elif isinstance(node.op, ast.Sub):
                    return left - right
                elif isinstance(node.op, ast.Mult):
                    return left * right
                elif isinstance(node.op, ast.Div):
                    denom = np.where(right == 0, np.nan, right) if isinstance(right, np.ndarray) else (np.nan if right == 0 else right)
                    return left / denom
                elif isinstance(node.op, ast.Pow):
                    return left ** right
                raise TypeError(f"Unsupported binary operator: {type(node.op).__name__}")

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in self.ALLOWED_FUNCS:
                fn = self.ALLOWED_FUNCS[node.func.id]
                args = [self.evaluate(arg) for arg in node.args]
                with np.errstate(divide="ignore", invalid="ignore"):
                    return fn(*args)
            raise ValueError(f"Disallowed or unknown function call in formula: '{getattr(node.func, 'id', str(node.func))}'")

        raise TypeError(f"Unsupported syntax tree element: {type(node).__name__}")


class SpectralIndexRegistry:
    """Singleton-style registry for Awesome Spectral Indices (ASI)."""

    def __init__(self, json_path: Optional[str] = None):
        self._indices: Dict[str, Dict[str, Any]] = {}
        self._load_registry(json_path or _INDICES_JSON_PATH)

    def _load_registry(self, path: str) -> None:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._indices = data.get("SpectralIndices", {})
            except Exception:
                self._indices = {}
        
        # Ensure foundational indices always exist in registry as guaranteed baseline
        if not self._indices:
            self._indices = self._get_fallback_indices()

    def _get_fallback_indices(self) -> Dict[str, Dict[str, Any]]:
        """Guaranteed fallback dictionary if external JSON is unreadable."""
        return {
            "NDVI": {
                "short_name": "NDVI",
                "long_name": "Normalized Difference Vegetation Index",
                "application_domain": "vegetation",
                "bands": ["N", "R"],
                "formula": "(N - R) / (N + R)",
                "reference": "https://doi.org/10.1016/0034-4257(79)90013-0"
            },
            "NDWI": {
                "short_name": "NDWI",
                "long_name": "Normalized Difference Water Index",
                "application_domain": "water",
                "bands": ["G", "N"],
                "formula": "(G - N) / (G + N)",
                "reference": "https://doi.org/10.1080/01431169608948714"
            },
            "MNDWI": {
                "short_name": "MNDWI",
                "long_name": "Modified Normalized Difference Water Index",
                "application_domain": "water",
                "bands": ["G", "S1"],
                "formula": "(G - S1) / (G + S1)",
                "reference": "https://doi.org/10.1080/01431160600589179"
            },
            "NBR": {
                "short_name": "NBR",
                "long_name": "Normalized Burn Ratio",
                "application_domain": "burn",
                "bands": ["N", "S2"],
                "formula": "(N - S2) / (N + S2)",
                "reference": "https://www.fs.usda.gov/rm/pubs/rmrs_gtr164.pdf"
            },
            "EVI": {
                "short_name": "EVI",
                "long_name": "Enhanced Vegetation Index",
                "application_domain": "vegetation",
                "bands": ["N", "R", "B"],
                "formula": "2.5 * ((N - R) / (N + 6.0 * R - 7.5 * B + 1.0))",
                "reference": "https://doi.org/10.1016/S0034-4257(02)00096-2"
            },
            "NDBI": {
                "short_name": "NDBI",
                "long_name": "Normalized Difference Built-Up Index",
                "application_domain": "urban",
                "bands": ["S1", "N"],
                "formula": "(S1 - N) / (S1 + N)",
                "reference": "https://doi.org/10.1080/0143116031000139863"
            },
            "BSI": {
                "short_name": "BSI",
                "long_name": "Bare Soil Index",
                "application_domain": "soil",
                "bands": ["S1", "R", "N", "B"],
                "formula": "((S1 + R) - (N + B)) / ((S1 + R) + (N + B))",
                "reference": "https://doi.org/10.1109/IGARSS.2002.1026048"
            },
            "NDRE": {
                "short_name": "NDRE",
                "long_name": "Normalized Difference Red Edge Index",
                "application_domain": "vegetation",
                "bands": ["N", "RE1"],
                "formula": "(N - RE1) / (N + RE1)",
                "reference": "https://doi.org/10.1080/014311699212000"
            }
        }

    def list_indices(
        self,
        domain: Optional[str] = None,
        platform: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List indices filtered by domain or satellite platform."""
        results = []
        domain_clean = domain.lower().strip() if domain else None
        platform_clean = platform.lower().strip() if platform else None

        for k, item in self._indices.items():
            if domain_clean and item.get("application_domain", "").lower() != domain_clean:
                continue
            if platform_clean:
                platforms = [p.lower() for p in item.get("platforms", [])]
                if not any(platform_clean in p for p in platforms):
                    continue
            results.append({
                "short_name": item.get("short_name", k),
                "long_name": item.get("long_name", ""),
                "application_domain": item.get("application_domain", ""),
                "bands": item.get("bands", []),
                "formula": item.get("formula", ""),
                "reference": item.get("reference", "")
            })
        return results

    def search_indices(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Search indices by keyword across name, domain, and formula."""
        q = query.lower().strip()
        matches = []
        for k, item in self._indices.items():
            text = f"{k} {item.get('long_name', '')} {item.get('application_domain', '')} {item.get('formula', '')}".lower()
            if q in text:
                matches.append({
                    "short_name": item.get("short_name", k),
                    "long_name": item.get("long_name", ""),
                    "application_domain": item.get("application_domain", ""),
                    "bands": item.get("bands", []),
                    "formula": item.get("formula", ""),
                    "reference": item.get("reference", "")
                })
                if len(matches) >= limit:
                    break
        return matches

    def get_index(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve index definition by short name (case-insensitive)."""
        name_clean = name.strip()
        for k, item in self._indices.items():
            if k.lower() == name_clean.lower() or item.get("short_name", "").lower() == name_clean.lower():
                return item
        return None

    def resolve_band_keys(self, index_name: str, platform: str = "sentinel-2") -> Dict[str, str]:
        """
        Resolve required ASI bands for an index into target platform asset keys.
        
        Returns:
            Dict mapping generic band symbol (e.g. 'N') to platform asset key (e.g. 'B08').
        """
        idx = self.get_index(index_name)
        if not idx:
            raise KeyError(f"Index '{index_name}' not found in registry.")

        p_key = platform.lower().strip()
        mapping = PLATFORM_BAND_MAPPINGS.get(p_key, PLATFORM_BAND_MAPPINGS["sentinel-2"])
        
        resolved = {}
        for b in idx.get("bands", []):
            if b in mapping:
                resolved[b] = mapping[b][0]
            else:
                resolved[b] = b
        return resolved

    def compute_index(
        self,
        index_name: str,
        band_arrays: Dict[str, np.ndarray],
        custom_params: Optional[Dict[str, float]] = None
    ) -> np.ndarray:
        """
        Compute a spectral index dynamically over input NumPy band arrays.

        Args:
            index_name: Name of index (e.g. 'NDVI', 'MNDWI', 'NDBI', 'EVI', 'SAVI').
            band_arrays: Dict mapping standard band symbol ('N', 'R', etc.) to 2D float arrays.
            custom_params: Optional parameter overrides (e.g. {'L': 0.5}).

        Returns:
            Computed 2D float32 array with NaN handling.
        """
        idx = self.get_index(index_name)
        if not idx:
            raise KeyError(f"Index '{index_name}' not found in registry.")

        # Ensure all arrays are float32
        converted_bands = {k: v.astype(np.float32) for k, v in band_arrays.items()}

        # Assemble variables dictionary
        vars_dict: Dict[str, Any] = {**DEFAULT_CONSTANTS}
        if custom_params:
            vars_dict.update(custom_params)
        vars_dict.update(converted_bands)

        # Check required bands (ignoring constants already present in vars_dict)
        required_bands = idx.get("bands", [])
        missing = [b for b in required_bands if b not in vars_dict]
        if missing:
            raise ValueError(f"Missing required bands for index '{index_name}': {missing}. Provided: {list(converted_bands.keys())}")

        # High-performance native vector dispatch for common indices
        name_upper = idx.get("short_name", index_name).upper()
        if name_upper == "NDVI":
            n, r = converted_bands["N"], converted_bands["R"]
            denom = n + r
            with np.errstate(divide="ignore", invalid="ignore"):
                return np.where(denom != 0, (n - r) / denom, np.nan)

        elif name_upper == "NDWI":
            g, n = converted_bands["G"], converted_bands["N"]
            denom = g + n
            with np.errstate(divide="ignore", invalid="ignore"):
                return np.where(denom != 0, (g - n) / denom, np.nan)

        elif name_upper == "MNDWI":
            g, s1 = converted_bands["G"], converted_bands["S1"]
            denom = g + s1
            with np.errstate(divide="ignore", invalid="ignore"):
                return np.where(denom != 0, (g - s1) / denom, np.nan)

        elif name_upper == "NBR":
            n, s2 = converted_bands["N"], converted_bands["S2"]
            denom = n + s2
            with np.errstate(divide="ignore", invalid="ignore"):
                return np.where(denom != 0, (n - s2) / denom, np.nan)

        elif name_upper == "NDBI":
            s1, n = converted_bands["S1"], converted_bands["N"]
            denom = s1 + n
            with np.errstate(divide="ignore", invalid="ignore"):
                return np.where(denom != 0, (s1 - n) / denom, np.nan)

        # Dynamic AST Evaluation for generic formulas
        formula = idx.get("formula", "")
        if not formula:
            raise ValueError(f"No formula defined for index '{index_name}'")

        try:
            tree = ast.parse(formula, mode="eval")
            evaluator = SafeFormulaEvaluator(vars_dict)
            result = evaluator.evaluate(tree)
            if isinstance(result, np.ndarray):
                return result.astype(np.float32)
            # Scalar result broadcast to band shape
            first_arr = next(iter(converted_bands.values()))
            return np.full_like(first_arr, result, dtype=np.float32)
        except Exception as exc:
            raise RuntimeError(f"Failed to evaluate formula for index '{index_name}' ('{formula}'): {str(exc)}")


# Global singleton registry instance
registry = SpectralIndexRegistry()
