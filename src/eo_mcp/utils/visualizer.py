"""Visual Artifact Generator & Interactive Map Output Engine for eo-mcp.

Implements Requirement R1:
1. Native 256-color LUT palettes (RdYlGn, Blues, YlOrRd, magma, terrain) using NumPy + Pillow
   with 100% alpha transparency for NaNs / nodata.
2. Georeferenced GeoTIFF raster export via rasterio & affine transform.
3. GeoJSON vector feature export.
4. Standalone, self-contained interactive web map (HTML) embedding Base64 image overlay
   and GeoJSON with dark titanium glassmorphic UI for immediate offline browser inspection.
5. Master export_visual_artifacts() coordinator returning paths and file:// URIs.
"""

import os
import io
import json
import base64
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union, List, Dict, Any, Tuple
import numpy as np
from PIL import Image
# Lazy rasterio detection flag - avoids blocking Windows Smart App Control loader
HAS_RASTERIO = False
if os.environ.get("ENABLE_RASTERIO", "").lower() in ("1", "true", "yes"):
    try:
        import rasterio
        from rasterio.transform import from_bounds
        import affine
        HAS_RASTERIO = True
    except (ImportError, OSError):
        HAS_RASTERIO = False

DEFAULT_OUTPUT_DIR = "./eo_outputs"


# ---------------------------------------------------------------------------
# Output Directory Resolution & URI Helpers
# ---------------------------------------------------------------------------

def get_output_dir(output_dir: Optional[Union[str, Path]] = None) -> Path:
    """
    Safely resolve and create the visual output directory.
    Priority:
    1. Explicit output_dir parameter
    2. EO_OUTPUT_DIR environment variable
    3. Default './eo_outputs' relative to current working directory
    """
    if output_dir is not None:
        target = Path(output_dir)
    elif "EO_OUTPUT_DIR" in os.environ:
        target = Path(os.environ["EO_OUTPUT_DIR"])
    else:
        target = Path(DEFAULT_OUTPUT_DIR)

    resolved = target.resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def path_to_uri(path: Union[str, Path]) -> str:
    """Convert a filesystem path to a standard file:// URI."""
    return Path(path).resolve().as_uri()


# ---------------------------------------------------------------------------
# Native 256-Color LUT Palettes (Pure NumPy + Pillow)
# ---------------------------------------------------------------------------

def _build_linear_lut(anchors: List[Tuple[float, Tuple[int, int, int]]]) -> np.ndarray:
    """Build a 256x3 uint8 lookup table by linear interpolation between anchor points."""
    x = [a[0] for a in anchors]
    r = [a[1][0] for a in anchors]
    g = [a[1][1] for a in anchors]
    b = [a[1][2] for a in anchors]
    xi = np.linspace(0.0, 1.0, 256)
    lut_r = np.clip(np.interp(xi, x, r), 0, 255).astype(np.uint8)
    lut_g = np.clip(np.interp(xi, x, g), 0, 255).astype(np.uint8)
    lut_b = np.clip(np.interp(xi, x, b), 0, 255).astype(np.uint8)
    return np.column_stack([lut_r, lut_g, lut_b])


# Canonical Scientific Anchor Definitions
_COLORMAP_ANCHORS = {
    # RdYlGn (NDVI / Vegetation Health): Crimson Red -> Tan/Yellow -> Bright Green -> Deep Forest Green
    "rdylgn": [
        (0.0, (165, 0, 38)),
        (0.25, (215, 48, 39)),
        (0.50, (254, 224, 139)),
        (0.75, (102, 189, 99)),
        (1.0, (0, 104, 55)),
    ],
    # Blues (NDWI / MNDWI / Inundation Depth): Ice Blue -> Sky Blue -> Royal Blue -> Deep Navy
    "blues": [
        (0.0, (247, 251, 255)),
        (0.25, (198, 219, 239)),
        (0.50, (107, 174, 214)),
        (0.75, (33, 113, 181)),
        (1.0, (8, 48, 107)),
    ],
    # YlOrRd (dNBR Burn Severity / Wildfires): Pale Yellow -> Orange -> Red -> Dark Crimson
    "ylorrd": [
        (0.0, (255, 255, 204)),
        (0.25, (254, 217, 118)),
        (0.50, (254, 153, 41)),
        (0.75, (227, 26, 28)),
        (1.0, (128, 0, 38)),
    ],
    # magma (LST / Urban Heat Island): Deep Dark Violet -> Magenta -> Orange -> Radiant Pale Yellow
    "magma": [
        (0.0, (0, 0, 4)),
        (0.25, (81, 18, 124)),
        (0.50, (182, 54, 121)),
        (0.75, (251, 136, 97)),
        (1.0, (252, 253, 191)),
    ],
    # terrain (DEM Elevation): Lowland Green -> Olive -> Sienna Ridge -> Slate Rock -> Snow White
    "terrain": [
        (0.0, (51, 153, 102)),
        (0.33, (204, 187, 102)),
        (0.66, (153, 102, 51)),
        (0.85, (170, 170, 170)),
        (1.0, (255, 255, 255)),
    ],
    # viridis (Perceptually Uniform General Purpose): Dark Purple -> Blue -> Teal -> Green -> Yellow
    "viridis": [
        (0.0, (68, 1, 84)),
        (0.25, (59, 82, 139)),
        (0.50, (33, 145, 140)),
        (0.75, (94, 201, 98)),
        (1.0, (253, 231, 37)),
    ],
    # inferno (High Contrast Thermal / Fire): Black -> Dark Purple -> Red/Orange -> Warm Gold
    "inferno": [
        (0.0, (0, 0, 4)),
        (0.25, (87, 16, 110)),
        (0.50, (187, 55, 84)),
        (0.75, (249, 142, 9)),
        (1.0, (252, 255, 164)),
    ],
}

# Precompute 256x3 tables for fast lookup
COLORMAP_LUTS: Dict[str, np.ndarray] = {
    name: _build_linear_lut(anchors)
    for name, anchors in _COLORMAP_ANCHORS.items()
}


def get_colormap_lut(colormap: str = "RdYlGn") -> np.ndarray:
    """Retrieve 256x3 uint8 lookup table for a given colormap name (case-insensitive)."""
    clean_name = colormap.lower().replace("_", "").replace("-", "")
    if clean_name in COLORMAP_LUTS:
        return COLORMAP_LUTS[clean_name]
    # Fallback to RdYlGn or viridis
    return COLORMAP_LUTS.get("rdylgn", COLORMAP_LUTS["viridis"])


# ---------------------------------------------------------------------------
# ASCII & PNG Preview Generation
# ---------------------------------------------------------------------------

def generate_ascii_preview(data: np.ndarray, width: int = 40, height: int = 20) -> str:
    """
    Generate an ASCII density map from a 2D float array (e.g. NDVI or elevation).
    Helps text-only LLMs understand spatial clustering and distribution.
    """
    if data.ndim == 3:
        data = data[0]

    h, w = data.shape
    step_y = max(1, h // height)
    step_x = max(1, w // width)
    sub = data[::step_y, ::step_x]

    ramp = " .:-=+*#%@"
    valid = sub[~np.isnan(sub)]
    if len(valid) == 0:
        return "[Empty or All-NaN Raster]"

    min_val, max_val = np.min(valid), np.max(valid)
    val_range = max(1e-5, max_val - min_val)

    lines = []
    for row in sub:
        line_chars = []
        for val in row:
            if np.isnan(val):
                line_chars.append(" ")
            else:
                norm = int(((val - min_val) / val_range) * (len(ramp) - 1))
                norm = max(0, min(len(ramp) - 1, norm))
                line_chars.append(ramp[norm])
        lines.append("".join(line_chars))

    return "\n".join(lines)


def render_preview_png(
    data: np.ndarray,
    colormap: str = "RdYlGn",
    output_path: Optional[Union[str, Path]] = None,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    nodata: Optional[float] = None,
) -> Union[Path, bytes]:
    """
    Render a 2D float array into a color-ramped 4-channel RGBA PNG.
    NaNs and NoData pixels receive alpha=0 (100% transparent), enabling clean
    map overlays.

    Args:
        data: 2D or 3D NumPy array. If 3D, first band is used.
        colormap: Palette name ('RdYlGn', 'Blues', 'YlOrRd', 'magma', 'terrain', 'viridis', etc.).
        output_path: File path to save the PNG. If None, returns PNG bytes.
        vmin: Minimum value for normalization. If None, computes min of valid pixels.
        vmax: Maximum value for normalization. If None, computes max of valid pixels.
        nodata: Explicit nodata value to treat as transparent.

    Returns:
        Path to written PNG file if output_path is given, or PNG raw bytes if None.
    """
    arr = np.asarray(data)
    if arr.ndim == 3:
        arr = arr[0]

    h, w = arr.shape
    lut = get_colormap_lut(colormap)

    valid = ~np.isnan(arr) & ~np.isinf(arr)
    if nodata is not None:
        valid = valid & (arr != nodata)

    rgba = np.zeros((h, w, 4), dtype=np.uint8)

    if np.any(valid):
        valid_vals = arr[valid]
        min_v = float(vmin) if vmin is not None else float(np.min(valid_vals))
        max_v = float(vmax) if vmax is not None else float(np.max(valid_vals))
        rng = max(1e-6, max_v - min_v)

        norm = np.clip((arr[valid] - min_v) / rng * 255.0, 0, 255).astype(np.uint8)
        rgba[valid, :3] = lut[norm]
        rgba[valid, 3] = 255  # Fully opaque for data pixels
    # Non-valid pixels remain rgba == [0, 0, 0, 0] (fully transparent)

    img = Image.fromarray(rgba, mode="RGBA")

    if output_path is not None:
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out, format="PNG", optimize=True)
        return out
    else:
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()


def array_to_png_bytes(data: np.ndarray, colormap: str = "viridis") -> bytes:
    """Convert a normalized 2D numpy array into a color-ramped PNG image byte buffer."""
    res = render_preview_png(data, colormap=colormap, output_path=None)
    assert isinstance(res, bytes)
    return res


# ---------------------------------------------------------------------------
# Georeferenced Raster & Vector Exporters
# ---------------------------------------------------------------------------

def export_geotiff(
    array: np.ndarray,
    bbox: List[float],
    output_path: Union[str, Path],
    crs: str = "EPSG:4326",
    nodata: Optional[float] = None,
) -> Path:
    """
    Export a 2D or 3D NumPy array as a georeferenced GeoTIFF (.tif) with Affine transform.

    Args:
        array: 2D (height, width) or 3D (bands, height, width) array.
        bbox: Bounding box [min_lon, min_lat, max_lon, max_lat].
        output_path: Destination file path.
        crs: Coordinate Reference System (default 'EPSG:4326').
        nodata: Nodata value written to raster metadata. Default np.nan for floats.

    Returns:
        Resolved Path to generated GeoTIFF (or None if rasterio is unavailable).
    """
    if not HAS_RASTERIO:
        return None

    arr = np.asarray(array)
    if arr.ndim == 2:
        count = 1
        height, width = arr.shape
        data_to_write = arr[np.newaxis, ...]
    elif arr.ndim == 3:
        count, height, width = arr.shape
        data_to_write = arr
    else:
        raise ValueError(f"Array must be 2D or 3D, got ndim={arr.ndim}")

    min_lon, min_lat, max_lon, max_lat = bbox
    transform = from_bounds(min_lon, min_lat, max_lon, max_lat, width, height)

    if nodata is not None:
        nd_val = nodata
    elif np.issubdtype(arr.dtype, np.floating):
        nd_val = float(np.nan)
    else:
        nd_val = None

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": count,
        "dtype": arr.dtype,
        "crs": crs,
        "transform": transform,
        "nodata": nd_val,
        "compress": "lzw",
    }

    out = Path(output_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out, "w", **profile) as dst:
        dst.write(data_to_write)

    return out


def export_geojson(
    features_or_geom: Any,
    output_path: Union[str, Path],
    properties: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Export vector geometries or features to a RFC 7946 GeoJSON file (.geojson).

    Accepts:
    - GeoJSON FeatureCollection dict
    - GeoJSON Feature dict
    - GeoJSON Geometry dict
    - List of features or geometries
    - Shapely geometry object (via __geo_interface__)
    - JSON string representation
    """
    if isinstance(features_or_geom, str):
        data = json.loads(features_or_geom)
    elif hasattr(features_or_geom, "__geo_interface__"):
        geom = features_or_geom.__geo_interface__
        data = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": geom,
                "properties": properties or {}
            }]
        }
    elif isinstance(features_or_geom, dict):
        if features_or_geom.get("type") == "FeatureCollection":
            data = features_or_geom
        elif features_or_geom.get("type") == "Feature":
            data = {
                "type": "FeatureCollection",
                "features": [features_or_geom]
            }
        elif "type" in features_or_geom and "coordinates" in features_or_geom:
            data = {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "geometry": features_or_geom,
                    "properties": properties or {}
                }]
            }
        else:
            data = features_or_geom
    elif isinstance(features_or_geom, list):
        features = []
        for item in features_or_geom:
            if isinstance(item, dict) and item.get("type") == "Feature":
                features.append(item)
            elif hasattr(item, "__geo_interface__"):
                features.append({
                    "type": "Feature",
                    "geometry": item.__geo_interface__,
                    "properties": properties or {}
                })
            elif isinstance(item, dict) and "coordinates" in item:
                features.append({
                    "type": "Feature",
                    "geometry": item,
                    "properties": properties or {}
                })
        data = {"type": "FeatureCollection", "features": features}
    else:
        raise ValueError(f"Unsupported geometry or feature format: {type(features_or_geom)}")

    out = Path(output_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return out


# ---------------------------------------------------------------------------
# Self-Contained Offline Interactive Map Generator (HTML)
# ---------------------------------------------------------------------------

def _get_css_gradient(colormap: str) -> Tuple[str, str, str]:
    """Return CSS gradient string, min label, and max label for HUD legend."""
    c = colormap.lower().replace("_", "").replace("-", "")
    if c == "rdylgn":
        return "linear-gradient(to right, #a50026, #d73027, #fee08b, #66bd63, #006837)", "-1.0", "+1.0"
    elif c == "blues":
        return "linear-gradient(to right, #f7fbff, #c6dbef, #6baed6, #2171b5, #08306b)", "0.0m", "> 2.5m"
    elif c == "ylorrd":
        return "linear-gradient(to right, #ffffcc, #fed976, #fe9929, #e31a1c, #800026)", "Unburned", "High Severity"
    elif c == "magma":
        return "linear-gradient(to right, #000004, #51127c, #b63679, #fb8861, #fcfdbf)", "Cool", "Severe Heat"
    elif c == "terrain":
        return "linear-gradient(to right, #339966, #ccbb66, #996633, #aaaaaa, #ffffff)", "0 m", "3000+ m"
    else:
        return "linear-gradient(to right, #440154, #3b528b, #21918c, #5ec962, #fde725)", "Min", "Max"


def generate_standalone_map_html(
    preview_png_path: Optional[Union[str, Path]],
    bbox: List[float],
    title: str = "Earth Observation Visualizer",
    vector_geojson: Optional[Union[Dict[str, Any], str]] = None,
    colormap_legend: Optional[Union[Dict[str, Any], str]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> str:
    """
    Generate a self-contained, single-file interactive web map (HTML).
    Features:
    - Zero backend runtime dependencies (runs directly from file:/// in any browser).
    - Embeds raster preview PNG as a Base64 data URI in an image overlay.
    - Embeds vector GeoJSON features if provided.
    - Apple dark titanium glassmorphic HUD panel with title, UTC timestamp, coordinates,
      and metrics scorecard.
    - Calibrated interactive colormap legend and raster opacity slider.
    - Resilient offline fallback: If internet is unreachable, renders embedded raster
      and vector layers immediately onto an HTML5 Canvas without blank screens.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    center_lon = (min_lon + max_lon) / 2.0
    center_lat = (min_lat + max_lat) / 2.0

    # Base64 encode preview PNG if provided
    b64_data_uri = ""
    if preview_png_path is not None:
        p = Path(preview_png_path)
        if p.is_file():
            with open(p, "rb") as f:
                b64_str = base64.b64encode(f.read()).decode("utf-8")
                b64_data_uri = f"data:image/png;base64,{b64_str}"

    # Normalize GeoJSON payload
    if isinstance(vector_geojson, str):
        geojson_obj = json.loads(vector_geojson)
    elif isinstance(vector_geojson, dict):
        geojson_obj = vector_geojson
    else:
        geojson_obj = {"type": "FeatureCollection", "features": []}
    geojson_json_str = json.dumps(geojson_obj)

    # Format metrics scorecard
    metrics_rows_html = ""
    if metrics:
        rows = []
        for k, v in metrics.items():
            label = str(k).replace("_", " ").title()
            val_str = f"{v:.4f}" if isinstance(v, float) else str(v)
            rows.append(f"""
                <div class="metric-row">
                    <span class="metric-label">{label}</span>
                    <span class="metric-value">{val_str}</span>
                </div>
            """)
        metrics_rows_html = "".join(rows)

    # Colormap legend details
    cmap_name = "RdYlGn"
    if isinstance(colormap_legend, str):
        cmap_name = colormap_legend
    elif isinstance(colormap_legend, dict):
        cmap_name = colormap_legend.get("name", "RdYlGn")

    css_gradient, min_lbl, max_lbl = _get_css_gradient(cmap_name)
    if isinstance(colormap_legend, dict):
        min_lbl = str(colormap_legend.get("min", min_lbl))
        max_lbl = str(colormap_legend.get("max", max_lbl))

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | eo-mcp Visualizer</title>
    <!-- Leaflet Engine (Online CDN + Resilient Offline Fallback) -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        :root {{
            --bg-glass: rgba(15, 23, 42, 0.88);
            --border-glass: rgba(255, 255, 255, 0.12);
            --accent: #38bdf8;
            --accent-gradient: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body, html {{
            width: 100%; height: 100%; overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #0b0f19; color: var(--text-main);
        }}
        #map, #offline-canvas-container {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        }}
        #offline-canvas {{
            width: 100%; height: 100%; display: block;
        }}

        /* Dark Titanium Glassmorphic HUD Panel */
        .glass-panel {{
            position: absolute;
            top: 20px;
            left: 20px;
            width: 380px;
            max-height: calc(100vh - 40px);
            background: var(--bg-glass);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--border-glass);
            border-radius: 14px;
            padding: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
            z-index: 1000;
            overflow-y: auto;
        }}
        .header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }}
        h1 {{ font-size: 1.15rem; font-weight: 700; color: #fff; letter-spacing: -0.02em; }}
        .badge {{
            background: var(--accent-gradient);
            color: #0b0f19;
            font-size: 0.68rem;
            font-weight: 800;
            padding: 3px 8px;
            border-radius: 9999px;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        .timestamp {{ font-size: 0.75rem; color: var(--text-muted); margin-bottom: 12px; }}
        
        .section-title {{
            font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
            color: var(--text-muted); letter-spacing: 0.05em; margin: 12px 0 6px 0;
        }}

        .metrics-card, .coords-card {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 10px;
            padding: 10px 12px;
            margin-bottom: 12px;
        }}
        .metric-row {{
            display: flex; justify-content: space-between; padding: 4px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            font-size: 0.82rem;
        }}
        .metric-row:last-child {{ border-bottom: none; }}
        .metric-label {{ color: var(--text-muted); }}
        .metric-value {{ font-weight: 600; color: #e2e8f0; font-family: monospace; }}

        /* Legend Ramp */
        .legend-card {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 10px;
            padding: 10px 12px;
            margin-bottom: 12px;
        }}
        .legend-bar {{
            height: 14px;
            border-radius: 7px;
            background: {css_gradient};
            border: 1px solid rgba(255, 255, 255, 0.2);
            margin: 6px 0 4px 0;
        }}
        .legend-labels {{
            display: flex; justify-content: space-between;
            font-size: 0.72rem; color: var(--text-muted); font-family: monospace;
        }}

        /* Opacity Slider */
        .slider-container {{
            display: flex; align-items: center; justify-content: space-between;
            gap: 10px; font-size: 0.8rem; color: var(--text-muted); margin-top: 6px;
        }}
        .slider-container input[type=range] {{
            flex: 1; accent-color: var(--accent); cursor: pointer;
        }}

        .btn {{
            width: 100%;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid var(--border-glass);
            color: #fff;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 0.8rem;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s ease;
            margin-top: 8px;
        }}
        .btn:hover {{
            background: rgba(56, 189, 248, 0.2);
            border-color: #38bdf8;
            color: #38bdf8;
        }}
        .footer {{
            margin-top: 14px; font-size: 0.7rem; color: #64748b; text-align: center;
        }}
        .leaflet-container {{ background: #0b0f19 !important; }}
    </style>
</head>
<body>
    <div class="glass-panel">
        <div class="header">
            <h1>{title}</h1>
            <span class="badge">EO Visualizer</span>
        </div>
        <div class="timestamp">Acquisition / Export: {now_iso}</div>

        <div class="section-title">Bounding Box (WGS84)</div>
        <div class="coords-card">
            <div class="metric-row"><span class="metric-label">West Lon</span><span class="metric-value">{min_lon:.5f}°</span></div>
            <div class="metric-row"><span class="metric-label">East Lon</span><span class="metric-value">{max_lon:.5f}°</span></div>
            <div class="metric-row"><span class="metric-label">South Lat</span><span class="metric-value">{min_lat:.5f}°</span></div>
            <div class="metric-row"><span class="metric-label">North Lat</span><span class="metric-value">{max_lat:.5f}°</span></div>
        </div>

        {f'<div class="section-title">Quantitative Analytics</div><div class="metrics-card">{metrics_rows_html}</div>' if metrics_rows_html else ''}

        <div class="section-title">Colormap Legend ({cmap_name})</div>
        <div class="legend-card">
            <div class="legend-bar"></div>
            <div class="legend-labels">
                <span>{min_lbl}</span>
                <span>Mid</span>
                <span>{max_lbl}</span>
            </div>
            <div class="slider-container">
                <span>Raster Opacity:</span>
                <input id="opacity-slider" type="range" min="0" max="100" value="85" oninput="setOpacity(this.value)">
                <span id="opacity-val">85%</span>
            </div>
        </div>

        <button class="btn" onclick="resetMapView()">Reset Bounding View</button>

        <div class="footer">
            eo-mcp Planetary Model Context Protocol &bull; Zero Backend Single-File Map
        </div>
    </div>

    <!-- Map Containers -->
    <div id="map"></div>
    <div id="offline-canvas-container" style="display:none;">
        <canvas id="offline-canvas"></canvas>
    </div>

    <script>
        const bbox = [{min_lon}, {min_lat}, {max_lon}, {max_lat}];
        const rasterDataUri = "{b64_data_uri}";
        const geojsonData = {geojson_json_str};

        let map = null;
        let rasterLayer = null;
        let vectorLayer = null;

        function setOpacity(val) {{
            document.getElementById('opacity-val').innerText = val + '%';
            if (rasterLayer && typeof rasterLayer.setOpacity === 'function') {{
                rasterLayer.setOpacity(val / 100);
            }} else if (window.offlineRenderer) {{
                window.offlineRenderer.opacity = val / 100;
                window.offlineRenderer.draw();
            }}
        }}

        function resetMapView() {{
            if (map) {{
                map.fitBounds([[bbox[1], bbox[0]], [bbox[3], bbox[2]]], {{ padding: [60, 60] }});
            }} else if (window.offlineRenderer) {{
                window.offlineRenderer.reset();
            }}
        }}

        // Initialize Map
        if (typeof L !== 'undefined') {{
            try {{
                map = L.map('map', {{
                    center: [{center_lat}, {center_lon}],
                    zoom: 12,
                    zoomControl: true,
                    attributionControl: false
                }});

                // Dark matter basemap (loads when internet is available)
                L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                    maxZoom: 19,
                    subdomains: 'abcd'
                }}).addTo(map);

                // Add embedded Base64 raster overlay
                if (rasterDataUri) {{
                    const bounds = [[bbox[1], bbox[0]], [bbox[3], bbox[2]]];
                    rasterLayer = L.imageOverlay(rasterDataUri, bounds, {{
                        opacity: 0.85,
                        interactive: true
                    }}).addTo(map);
                }}

                // Add vector GeoJSON overlay
                if (geojsonData && geojsonData.features && geojsonData.features.length > 0) {{
                    vectorLayer = L.geoJSON(geojsonData, {{
                        style: function(feature) {{
                            const p = feature.properties || {{}};
                            return {{
                                color: p.stroke || p.color || '#38bdf8',
                                weight: 2,
                                fillColor: p.fill || p['fill-color'] || '#ef4444',
                                fillOpacity: 0.5
                            }};
                        }},
                        pointToLayer: function(feature, latlng) {{
                            return L.circleMarker(latlng, {{
                                radius: 6,
                                fillColor: '#f59e0b',
                                color: '#ffffff',
                                weight: 1.5,
                                fillOpacity: 0.9
                            }});
                        }},
                        onEachFeature: function(feature, layer) {{
                            const p = feature.properties || {{}};
                            let popup = '<div style="font-family:sans-serif;font-size:12px;"><strong>Feature Attributes</strong><br/>';
                            for (const [k, v] of Object.entries(p)) {{
                                popup += `<b>${{k}}:</b> ${{v}}<br/>`;
                            }}
                            popup += '</div>';
                            layer.bindPopup(popup);
                        }}
                    }}).addTo(map);
                }}

                L.control.scale({{ imperial: false, metric: true }}).addTo(map);
                map.fitBounds([[bbox[1], bbox[0]], [bbox[3], bbox[2]]], {{ padding: [60, 60] }});
            }} catch (err) {{
                console.warn("Leaflet initialization failed, falling back to offline canvas:", err);
                initOfflineCanvas();
            }}
        }} else {{
            initOfflineCanvas();
        }}

        // Offline Canvas Renderer (Air-gapped / No CDN access)
        function initOfflineCanvas() {{
            document.getElementById('map').style.display = 'none';
            const container = document.getElementById('offline-canvas-container');
            container.style.display = 'block';
            const canvas = document.getElementById('offline-canvas');
            const ctx = canvas.getContext('2d');

            function resize() {{
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
            }}
            window.addEventListener('resize', () => {{ resize(); renderer.draw(); }});
            resize();

            const renderer = {{
                opacity: 0.85,
                panX: 0,
                panY: 0,
                zoom: 1.0,
                img: null,
                reset: function() {{
                    this.panX = 0;
                    this.panY = 0;
                    this.zoom = 1.0;
                    this.draw();
                }},
                draw: function() {{
                    ctx.fillStyle = "#0b0f19";
                    ctx.fillRect(0, 0, canvas.width, canvas.height);

                    // Draw grid lines
                    ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
                    ctx.lineWidth = 1;
                    const step = 60 * this.zoom;
                    for (let x = (this.panX % step); x < canvas.width; x += step) {{
                        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
                    }}
                    for (let y = (this.panY % step); y < canvas.height; y += step) {{
                        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
                    }}

                    // Draw raster image centered in view
                    const pad = 80;
                    const targetW = (canvas.width - pad * 2) * this.zoom;
                    const targetH = (canvas.height - pad * 2) * this.zoom;
                    const posX = (canvas.width - targetW) / 2 + this.panX;
                    const posY = (canvas.height - targetH) / 2 + this.panY;

                    if (this.img && this.img.complete) {{
                        ctx.globalAlpha = this.opacity;
                        ctx.drawImage(this.img, posX, posY, targetW, targetH);
                        ctx.globalAlpha = 1.0;

                        // Bounding Box outline
                        ctx.strokeStyle = "#38bdf8";
                        ctx.lineWidth = 2;
                        ctx.strokeRect(posX, posY, targetW, targetH);
                    }}

                    // Notice tag
                    ctx.fillStyle = "rgba(255, 255, 255, 0.4)";
                    ctx.font = "12px monospace";
                    ctx.fillText("Offline Fallback Canvas Mode [Pan: Drag | Zoom: Scroll]", 420, canvas.height - 20);
                }}
            }};

            if (rasterDataUri) {{
                const img = new Image();
                img.onload = () => {{ renderer.img = img; renderer.draw(); }};
                img.src = rasterDataUri;
            }} else {{
                renderer.draw();
            }}

            window.offlineRenderer = renderer;

            // Pan and Zoom interaction
            let isDragging = false, startX, startY;
            canvas.addEventListener('mousedown', (e) => {{
                isDragging = true;
                startX = e.clientX - renderer.panX;
                startY = e.clientY - renderer.panY;
            }});
            window.addEventListener('mousemove', (e) => {{
                if (!isDragging) return;
                renderer.panX = e.clientX - startX;
                renderer.panY = e.clientY - startY;
                renderer.draw();
            }});
            window.addEventListener('mouseup', () => {{ isDragging = false; }});
            canvas.addEventListener('wheel', (e) => {{
                e.preventDefault();
                const factor = e.deltaY < 0 ? 1.1 : 0.9;
                renderer.zoom = Math.max(0.2, Math.min(5.0, renderer.zoom * factor));
                renderer.draw();
            }});
        }}
    </script>
</body>
</html>
"""

    if output_path is not None:
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(html_content)

    return html_content


# ---------------------------------------------------------------------------
# Master Artifact Export Coordinator
# ---------------------------------------------------------------------------

def export_visual_artifacts(
    array: Optional[np.ndarray],
    bbox: List[float],
    name: str,
    colormap: str = "RdYlGn",
    vector_geojson: Optional[Union[Dict[str, Any], str]] = None,
    output_dir: Union[str, Path] = DEFAULT_OUTPUT_DIR,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    title: Optional[str] = None,
    metrics: Optional[Dict[str, Any]] = None,
    export_geotiff_raster: bool = True,
) -> Dict[str, Any]:
    """
    Export full visual artifact suite (PNG preview, GeoTIFF, GeoJSON, and self-contained HTML map).

    Conforms to the Interface Contract specified in PROJECT.md:
    Returns dictionary with:
    - 'preview_path': Absolute path to .png (or None)
    - 'preview_uri': file:// URI (or None)
    - 'geotiff_path': Absolute path to .tif (or None)
    - 'geotiff_uri': file:// URI (or None)
    - 'geojson_path': Absolute path to .geojson (or None)
    - 'geojson_uri': file:// URI (or None)
    - 'map_path': Absolute path to .html
    - 'map_uri': file:// URI
    - 'visual_artifacts': Nested sub-dictionary for structured consumers
    """
    out_dir = get_output_dir(output_dir)

    # Deterministic yet collision-resistant slug
    clean_name = name.lower().replace(" ", "_").replace("/", "_")
    bbox_str = f"{bbox[0]:.4f}_{bbox[1]:.4f}_{bbox[2]:.4f}_{bbox[3]:.4f}"
    hash_tag = hashlib.sha256(f"{clean_name}_{bbox_str}".encode("utf-8")).hexdigest()[:6]
    base_name = f"{clean_name}_{hash_tag}"

    preview_path: Optional[str] = None
    preview_uri: Optional[str] = None
    geotiff_path: Optional[str] = None
    geotiff_uri: Optional[str] = None
    geojson_path: Optional[str] = None
    geojson_uri: Optional[str] = None

    # 1. Raster Processing (PNG Preview + GeoTIFF)
    if array is not None:
        png_file = out_dir / f"{base_name}.png"
        render_preview_png(
            data=array,
            colormap=colormap,
            output_path=png_file,
            vmin=vmin,
            vmax=vmax,
        )
        preview_path = str(png_file.resolve())
        preview_uri = path_to_uri(png_file)

        if export_geotiff_raster and HAS_RASTERIO:
            tif_file = out_dir / f"{base_name}.tif"
            geotiff_res = export_geotiff(
                array=array,
                bbox=bbox,
                output_path=tif_file,
            )
            if geotiff_res is not None:
                geotiff_path = str(tif_file.resolve())
                geotiff_uri = path_to_uri(tif_file)

    # 2. Vector Processing (GeoJSON)
    if vector_geojson is not None:
        geojson_file = out_dir / f"{base_name}.geojson"
        export_geojson(
            features_or_geom=vector_geojson,
            output_path=geojson_file,
        )
        geojson_path = str(geojson_file.resolve())
        geojson_uri = path_to_uri(geojson_file)

    # 3. Interactive Web Map (HTML)
    map_file = out_dir / f"{base_name}.html"
    map_title = title or f"{name.replace('_', ' ').title()} Visualizer"
    generate_standalone_map_html(
        preview_png_path=preview_path,
        bbox=bbox,
        title=map_title,
        vector_geojson=vector_geojson,
        colormap_legend=colormap,
        metrics=metrics,
        output_path=map_file,
    )
    map_path = str(map_file.resolve())
    map_uri = path_to_uri(map_file)

    result = {
        "preview_path": preview_path,
        "preview_uri": preview_uri,
        "geotiff_path": geotiff_path,
        "geotiff_uri": geotiff_uri,
        "geojson_path": geojson_path,
        "geojson_uri": geojson_uri,
        "map_path": map_path,
        "map_uri": map_uri,
        "visual_artifacts": {
            "preview_png": preview_path,
            "preview_png_uri": preview_uri,
            "interactive_map": map_path,
            "interactive_map_uri": map_uri,
            "geotiff": geotiff_path,
            "geotiff_uri": geotiff_uri,
            "geojson": geojson_path,
            "geojson_uri": geojson_uri,
        }
    }

    return result
