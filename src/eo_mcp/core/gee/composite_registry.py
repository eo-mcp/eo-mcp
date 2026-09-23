"""Session-scoped composite registry for stateful GEE workflows in eo-mcp.

Holds active ee.Image composites in an in-memory session registry, exposing lightweight
composite_id handles (e.g., 'composite_1', 'composite_2').
Enables multi-turn AI agent workflows (index computation, zonal statistics, thumbnail
rendering, and GeoTIFF export) without requiring the agent to re-specify complex collection
filters or re-compute expensive reducers on every tool call.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

_COMPOSITES: Dict[str, Dict[str, Any]] = {}
_COUNTER = {"n": 0}


def register_composite(
    image: Any,
    region: Any,
    scale: int,
    bands: List[str],
    sensor: str,
    year: int,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Register an ee.Image composite and return a unique composite_id handle.

    Args:
        image: ee.Image object.
        region: ee.Geometry defining the area of interest.
        scale: Spatial resolution in meters.
        bands: List of band names present on the composite.
        sensor: Source sensor key (e.g., 'sentinel2_sr').
        year: Target year of the composite.
        metadata: Optional dictionary of provenance metadata.

    Returns:
        String identifier such as 'composite_1'.
    """
    _COUNTER["n"] += 1
    cid = f"composite_{_COUNTER['n']}"
    _COMPOSITES[cid] = {
        "image": image,
        "region": region,
        "scale": scale,
        "bands": list(bands),
        "sensor": sensor,
        "year": year,
        "metadata": metadata or {},
    }
    return cid


def get_composite(composite_id: str) -> Dict[str, Any]:
    """Retrieve an active composite entry by its ID.

    Args:
        composite_id: Handle returned by register_composite.

    Returns:
        Dictionary containing image, region, scale, bands, sensor, year.

    Raises:
        ValueError: If composite_id is not found in the registry.
    """
    if composite_id not in _COMPOSITES:
        known = list(_COMPOSITES.keys()) or ["none (call gee_build_composite first)"]
        raise ValueError(
            f"Unknown composite_id '{composite_id}'. Available in session: {known}"
        )
    return _COMPOSITES[composite_id]


def update_composite(composite_id: str, image: Any, bands: List[str]) -> None:
    """Update the ee.Image and band list for an existing composite handle (e.g. after adding indices)."""
    entry = get_composite(composite_id)
    entry["image"] = image
    entry["bands"] = list(bands)


def list_composites() -> List[Dict[str, Any]]:
    """List summary metadata for all active composites in the current session."""
    summaries = []
    for cid, data in _COMPOSITES.items():
        summaries.append({
            "composite_id": cid,
            "sensor": data["sensor"],
            "year": data["year"],
            "scale_m": data["scale"],
            "band_count": len(data["bands"]),
            "bands": data["bands"],
        })
    return summaries


def clear_composites() -> None:
    """Clear all registered composites from the session."""
    _COMPOSITES.clear()
    _COUNTER["n"] = 0
