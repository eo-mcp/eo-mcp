# eo-mcp Agent Guidelines & Scientific Determinism Invariants

> **Repository:** `G:\My Drive\eo-mcp`  
> **Classification:** Open Source Planetary Earth Observation Model Context Protocol (MCP)  
> **Domain:** https://eo-mcp.github.io  
> **Target Runtimes:** Claude Desktop, Cursor, Antigravity, Python Agents  

---

## 1. The Core Scientific Invariant: Zero Generative AI Imagery

### The "No Nano Banana" Policy (Absolute Ban on AI-Generated Visuals)
In `eo-mcp`, all synthetic, diffusion-based, or generative text-to-image tools (including **Nano Banana**, Google Imagen, Midjourney, DALL-E, Stable Diffusion, and any other prompt-to-image models) are **STRICTLY OFF LIMITS AND FORBIDDEN**.

#### Why This Rule Is Non-Negotiable
Earth Observation (EO) is high-stakes scientific telemetry. Remote sensing data is deployed for:
1. **Civil Protection & Disaster Response:** Evacuation perimeters during active wildfire fronts and dam breach flooding.
2. **Maritime Domain Awareness:** Interdicting illicit, sanctions-evading, or uncooperative "dark vessels" in international waters.
3. **Climate & Hydrological Engineering:** Quantifying sub-meter coastal inundation and post-fire debris-flow risk.

Generative AI imagery hallucinates non-existent topography, invents false thermal anomalies, corrupts geographic coordinates, and fabricates fake radar returns. Using generative AI images in place of real remote sensing data destroys scientific provenance, violates physical conservation laws, and undermines evaluator trust.

#### The Deterministic Visual Mandate
Every visual artifact, map, chart, and raster output produced by or for `eo-mcp` must be:
- **100% Script-Driven:** Generated programmatically by deterministic Python scripts (`eo_mcp.utils.visualizer`, `numpy`, `PIL`, `matplotlib`, `rasterio`).
- **Bound to Ground-Truth Spatial Data:** Computed directly from verified satellite arrays, digital elevation models (Copernicus DEM GLO-30), thermal radiance ratios (NASA FIRMS VIIRS), SAR backscatter ($\sigma_0$), and GeoJSON vectors.
- **Exported as Verifiable Open Formats:** Georeferenced GeoTIFF (`.tif`), calibrated 256-color LUT PNG (`.png`), standard GeoJSON (`.geojson`), or self-contained interactive Leaflet/MapLibre HTML web maps (`.html`).

---

## 2. Visual & Formatting Standards

1. **Zero Em Dashes:**
   - Strictly never use em dashes (unicode 8212) anywhere in code, docstrings, markdown files, commit messages, or web content. Use hyphens, commas, colons, or parentheses instead.
2. **Clean Planetary Topography:**
   - Never draw synthetic HUD circles, artificial target rings, or faux sci-fi grid lines over planetary bodies (Earth, Mars, Moon). Let authentic remote sensing rasters, spectral indices, and genuine vector layers command the canvas.
3. **Visual-First Density (50% to 70%):**
   - For documentation cards and visual reports, the authentic spatial raster or map must command 50% to 70% of the canvas, anchored by concise technical telemetry metadata.

---

## 3. Runtime & Platform Resilience

1. **Windows Smart App Control (SAC) Compatibility:**
   - Never place unhandled top-level imports of unsigned C-extensions (such as raw `rasterio` wheels).
   - Always wrap binary raster drivers in resilient `try...except (ImportError, OSError)` fallbacks (as implemented in `eo_mcp.core.raster` and `eo_mcp.utils.visualizer`), ensuring that pure-NumPy and Pillow pipelines execute flawlessly even on restricted corporate or government Windows machines.
2. **STAC API Protocol:**
   - Always use `eo_mcp.providers.stac.get_stac_client()` and `HttpxStacApiIO` for STAC queries to prevent OpenSSL `SSLEOFError` and CloudFront HTTP/2 connection drops.
3. **Test Integrity:**
   - All web documentation pages (`index.html`, `docs.html`, `methodology.html`, `contact.html`, `privacy.html`, `terms.html`) must pass `tests/test_challenger_verification.py` without structural or broken-link errors.
