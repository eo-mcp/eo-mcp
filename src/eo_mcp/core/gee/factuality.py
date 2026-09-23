"""Scientific factuality auditing and declarative Mermaid pipeline generation for GEE.

Adapts the scientific rigor from Frontier Development Lab (FDL / ESA gee-mcp):
1. Programmatic auditing of Earth Observation scientific assumptions (atmospheric
   correction, cloud edge omission, cross-sensor radiometric consistency, spatial resampling).
2. Declarative Mermaid graph generation mapping the end-to-end EO processing chain.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def audit_factuality_assumptions(pipeline_params: Dict[str, Any]) -> List[Dict[str, str]]:
    """Audit an Earth Engine processing pipeline for implicit scientific assumptions.

    Evaluates sensor choices, temporal windows, atmospheric processing levels,
    and reduction methods to surface scientific risks requiring expert verification.

    Args:
        pipeline_params: Dictionary containing workflow parameters:
            - 'sensor': Sensor key (e.g. 'sentinel2_sr', 'landsat5_t1_sr')
            - 'year': Calendar year
            - 'reducer': Reduction method ('median', 'greenest', etc.)
            - 'indices': List of computed indices ('NDVI', 'NDWI', etc.)
            - 'cloud_threshold': Optional cloud threshold percentage
            - 'scale_m': Spatial resolution in meters

    Returns:
        List of audit findings with title, assumption, scientific impact, and expert question.
    """
    findings: List[Dict[str, str]] = []
    sensor = str(pipeline_params.get("sensor", "")).lower()
    year = int(pipeline_params.get("year", 2024))
    reducer = str(pipeline_params.get("reducer", "median")).lower()
    indices = [str(i).upper() for i in pipeline_params.get("indices", [])]

    # Check 1: Historical MSS Top of Atmosphere vs Surface Reflectance
    if "mss" in sensor or year <= 1984:
        findings.append({
            "title": "Top-of-Atmosphere (TOA) Radiometric Calibration in MSS Era",
            "assumption": "Landsat MSS lacks an official Collection 2 Surface Reflectance (SR) product and uses TOA conversion.",
            "scientific_impact": "Atmospheric scattering (Rayleigh and aerosol) may artificially elevate visible band values relative to modern SR collections.",
            "question_for_expert": "Has dark object subtraction (DOS) or relative radiometric normalization been considered before comparing MSS indices against Landsat 8 or Sentinel-2?",
        })

    # Check 2: Cross-Sensor Sensor Harmonization
    if "sentinel2" in sensor and year >= 2015 and any(i in ["NDVI", "EVI", "SAVI"] for i in indices):
        findings.append({
            "title": "Cross-Sensor Spectral Bandpass Differences",
            "assumption": "Sentinel-2 MSI and Landsat 8/9 OLI NIR bandpasses differ slightly (S2 B8 is 842nm, L8 B5 is 865nm).",
            "scientific_impact": "Direct vegetation index comparisons without Roy et al. (2016) polynomial transformation can introduce +/- 0.03 systematic offset.",
            "question_for_expert": "Are cross-sensor coefficients required for this quantitative time-series, or is raw index comparability sufficient for change detection?",
        })

    # Check 3: Temporal Composite Reducer Bias
    if reducer == "median":
        findings.append({
            "title": "Temporal Median Smoothing of Dynamic Hydrological Phenomena",
            "assumption": "A seasonal median reducer assumes stationary surface conditions across the composite date window.",
            "scientific_impact": "Ephemeral events (flash flood peak extents, active fire scars, rapid harvest) will be smoothed out by the median operator.",
            "question_for_expert": "If monitoring rapid environmental transitions, should minimum water index or percentile reducers be used instead of median?",
        })
    elif reducer == "greenest":
        findings.append({
            "title": "Greenest-Pixel Peak Biomass Selection Bias",
            "assumption": "Quality mosaic selects pixels at maximum NDVI across the temporal window.",
            "scientific_impact": "Result represents peak growing season biomass rather than average seasonal vegetation cover.",
            "question_for_expert": "Is peak biomass the appropriate ecological baseline for this land degradation or agricultural audit?",
        })

    # Check 4: Water Index Cloud Shadow Misclassification
    if "NDWI" in indices or "MNDWI" in indices:
        findings.append({
            "title": "Topographic and Cloud Shadow Spectral Confusion with Water",
            "assumption": "Low NIR reflectance from unmasked terrain shadows can mimic open water spectral signatures.",
            "scientific_impact": "Mountainous or steep terrain shadows can create false positive water inundation pixels.",
            "question_for_expert": "Should Copernicus DEM slope masking (e.g. slope < 5 degrees) be applied to eliminate topographic shadow false positives?",
        })

    return findings


def generate_mermaid_pipeline(pipeline_spec: Dict[str, Any]) -> str:
    """Generate a clean, declarative Mermaid flowchart of the GEE processing chain.

    Args:
        pipeline_spec: Configuration describing dataset, sensors, filters, reducers, indices, and outputs.

    Returns:
        Mermaid flowchart string formatted for markdown embedding.
    """
    year = pipeline_spec.get("year", 2024)
    sensor = pipeline_spec.get("sensor", "Sentinel-2 / Landsat")
    reducer = pipeline_spec.get("reducer", "median")
    indices = pipeline_spec.get("indices", ["NDVI"])
    outputs = pipeline_spec.get("outputs", ["Zonal Statistics", "Thumbnail URL"])

    indices_str = ", ".join(indices) if indices else "Standard Reflectance"
    outputs_str = ", ".join(outputs) if outputs else "Analytics Result"

    lines = [
        "```mermaid",
        "flowchart TD",
        f"    A[\"Catalog Discovery: {sensor} ({year})\"] --> B[\"Temporal & Spatial AOI Filter\"]",
        "    B --> C[\"QA Bitmask Cloud & Shadow Masking\"]",
        "    C --> D[\"Band Harmonization (Standard Namespace)\"]",
        "    D --> E{\"Scene Count >= min_scenes?\"}",
        "    E -- Yes --> F[\"Reducer: " + reducer.capitalize() + "\"]",
        "    E -- No --> E_Fallback[\"Fallback: Backup Sensor & Window Expansion\"]",
        "    E_Fallback --> F",
        f"    F --> G[\"Compute Spectral Indices: {indices_str}\"]",
        f"    G --> H[\"Export / Analytics: {outputs_str}\"]",
        "```",
    ]
    return "\n".join(lines)
