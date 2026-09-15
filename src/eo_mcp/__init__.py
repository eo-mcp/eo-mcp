"""eo-mcp: The Open Source Model Context Protocol (MCP) for Planetary Earth Observation.

Empowers AI agents to autonomously discover, stream, and compute satellite
analytics from free government archives (Copernicus CDSE, USGS Landsat,
Copernicus DEM, Sentinel-1 SAR, Sentinel-5P, MODIS/VIIRS).
"""

__version__ = "0.1.0"
__author__ = "M. Anwar Sounny-Slitine, PhD (sounny.com)"
__license__ = "Apache-2.0"

from eo_mcp.workflows import assess_location_hazard, environmental_site_audit, resolve_aoi
from eo_mcp.core.pipeline import execute_pipeline, list_pipeline_recipes, describe_pipeline_recipe
from eo_mcp.registry import discover_tools, get_active_profile, get_allowed_tools

__all__ = [
    "assess_location_hazard",
    "environmental_site_audit",
    "resolve_aoi",
    "execute_pipeline",
    "list_pipeline_recipes",
    "describe_pipeline_recipe",
    "discover_tools",
    "get_active_profile",
    "get_allowed_tools",
]
