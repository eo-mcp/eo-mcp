"""eo-mcp: The Open Source Model Context Protocol (MCP) for Planetary Earth Observation.

Empowers AI agents to autonomously discover, stream, and compute satellite
analytics from free government archives (Copernicus CDSE, USGS Landsat,
Copernicus DEM, Sentinel-1 SAR, Sentinel-5P, MODIS/VIIRS).
"""

__version__ = "0.1.0"
__author__ = "M. Anwar Sounny-Slitine, PhD (sounny.com)"
__license__ = "Apache-2.0"

_LAZY_IMPORTS = {
    "assess_location_hazard": "eo_mcp.workflows",
    "environmental_site_audit": "eo_mcp.workflows",
    "resolve_aoi": "eo_mcp.workflows",
    "execute_pipeline": "eo_mcp.core.pipeline",
    "list_pipeline_recipes": "eo_mcp.core.pipeline",
    "describe_pipeline_recipe": "eo_mcp.core.pipeline",
    "discover_tools": "eo_mcp.registry",
    "get_active_profile": "eo_mcp.registry",
    "get_allowed_tools": "eo_mcp.registry",
}

def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        import importlib
        mod = importlib.import_module(_LAZY_IMPORTS[name])
        val = getattr(mod, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = list(_LAZY_IMPORTS.keys())

