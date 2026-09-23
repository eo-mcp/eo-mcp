"""Google Earth Engine (GEE) integration module for eo-mcp.

Bridges open STAC/COG client-side streaming with planetary GEE server-side compute.
Implements 50-year multi-sensor temporal harmonization (Landsat MSS 1972 through Sentinel-2),
QA cloud masking, spectral index computation, zonal statistics, raster masking,
threshold area extraction, and scientific factuality auditing.
"""

from eo_mcp.core.gee.session import init_ee, is_ee_available, get_ee_status
from eo_mcp.core.gee.sensors import (
    COLLECTIONS,
    STANDARD_BANDS,
    get_sensors_for_year,
    harmonized_bands_for,
)
from eo_mcp.core.gee.composite_registry import (
    register_composite,
    get_composite,
    list_composites,
    clear_composites,
)
from eo_mcp.core.gee.indices import (
    KNOWN_INDICES,
    computable_indices,
    add_indices,
)
from eo_mcp.core.gee.factuality import (
    audit_factuality_assumptions,
    generate_mermaid_pipeline,
)

__all__ = [
    "init_ee",
    "is_ee_available",
    "get_ee_status",
    "COLLECTIONS",
    "STANDARD_BANDS",
    "get_sensors_for_year",
    "harmonized_bands_for",
    "register_composite",
    "get_composite",
    "list_composites",
    "clear_composites",
    "KNOWN_INDICES",
    "computable_indices",
    "add_indices",
    "audit_factuality_assumptions",
    "generate_mermaid_pipeline",
]
