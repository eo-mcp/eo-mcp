"""Tool Registry and Category Management for eo-mcp.

Implements the Neon-style tool categorization and progressive discovery pattern.
Allows MCP clients and AI agents to:
1. Discover tools dynamically via search or category filters.
2. Scope loaded tools using profiles (e.g., 'workflows', 'hazards', 'climate', 'minimal')
   to prevent context window bloat and tool selection confusion.
"""

from typing import Dict, List, Optional, Any
import os

# Tool categories definition
TOOL_CATEGORIES = {
    "workflows": {
        "description": "Ergonomic composite workflows bundling multi-step tasks (geocoding, search, analytics) into single token-efficient calls.",
        "tools": [
            "assess_location_hazard",
            "environmental_site_audit",
        ]
    },
    "core": {
        "description": "Fundamental spatial and STAC catalog discovery primitives.",
        "tools": [
            "eo_geocode",
            "stac_search",
            "list_supported_collections",
            "discover_eo_tools",
        ]
    },
    "spectral": {
        "description": "Spectral index computation, SAR radar backscatter, and elevation profile extraction.",
        "tools": [
            "calculate_spectral_index",
            "get_elevation_profile",
            "detect_water_sar",
        ]
    },
    "hazards": {
        "description": "Planetary hazard assessment: sea level rise, wildfires, burn severity, and coastal erosion.",
        "tools": [
            "simulate_sea_level_rise",
            "detect_active_wildfires",
            "calculate_burn_severity",
            "analyze_coastal_erosion",
        ]
    },
    "climate": {
        "description": "Long-term climate, environmental, and agricultural monitoring.",
        "tools": [
            "analyze_urban_heat_island",
            "analyze_reservoir_drought",
            "monitor_crop_phenology",
            "monitor_atmospheric_emissions",
        ]
    },
    "maritime": {
        "description": "Maritime domain awareness, radar vessel detection, and AIS correlation.",
        "tools": [
            "detect_dark_vessels",
        ]
    },
    "advanced": {
        "description": "Advanced code execution, authenticated data access, and credential management.",
        "tools": [
            "run_geospatial_script",
            "configure_credentials",
            "get_credential_status",
            "download_copernicus_granule",
        ]
    }
}

# Pre-defined profiles mapping to one or more categories
PROFILES = {
    "all": list(TOOL_CATEGORIES.keys()),
    "workflows": ["workflows", "core"],
    "hazards": ["workflows", "hazards", "core"],
    "climate": ["workflows", "climate", "core"],
    "maritime": ["workflows", "maritime", "core"],
    "minimal": ["workflows", "core"],
    "spectral": ["workflows", "spectral", "core"],
}


def get_active_profile() -> str:
    """Get the currently configured profile name from environment."""
    return os.getenv("EO_MCP_PROFILE", "all").lower().strip()


def get_allowed_tools(profile: Optional[str] = None) -> List[str]:
    """
    Get list of tool names permitted by the active or specified profile.
    If profile specifies comma-separated categories, those categories are included.
    """
    prof = profile or get_active_profile()
    
    # Check if profile is a preset
    if prof in PROFILES:
        categories = PROFILES[prof]
    else:
        # Check if user specified comma-separated categories e.g. "workflows,hazards"
        categories = [c.strip() for c in prof.split(",") if c.strip() in TOOL_CATEGORIES]
        if not categories:
            categories = PROFILES["all"]

    allowed = set()
    for cat in categories:
        if cat in TOOL_CATEGORIES:
            allowed.update(TOOL_CATEGORIES[cat]["tools"])
    return sorted(list(allowed))


def is_tool_enabled(tool_name: str, profile: Optional[str] = None) -> bool:
    """Check if a tool is enabled under the current or specified profile."""
    prof = profile or get_active_profile()
    if prof == "all":
        return True
    return tool_name in get_allowed_tools(prof)


def discover_tools(category: Optional[str] = None, query: Optional[str] = None) -> Dict[str, Any]:
    """
    Search and inspect tools across categories.
    Used for client-side progressive tool discovery.
    """
    results = {}
    q = query.lower().strip() if query else None

    for cat_name, cat_data in TOOL_CATEGORIES.items():
        if category and category.lower() != cat_name.lower():
            continue

        cat_tools = []
        for t in cat_data["tools"]:
            if not q or q in t.lower() or q in cat_name.lower() or q in cat_data["description"].lower():
                cat_tools.append(t)

        if cat_tools:
            results[cat_name] = {
                "description": cat_data["description"],
                "tools": cat_tools
            }

    return {
        "active_profile": get_active_profile(),
        "categories_matched": len(results),
        "results": results
    }
