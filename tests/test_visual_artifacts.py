"""Automated unit and integration test suite for Visual Artifact Generation & Interactive Map Output.

Requirement R1 / Milestone M1 verification:
- 256-color LUT palettes (RdYlGn, Blues, YlOrRd, magma, terrain, viridis, inferno)
- NaN / NoData alpha transparency handling
- Georeferenced GeoTIFF creation with rasterio and Affine transforms
- GeoJSON vector export
- Standalone offline interactive HTML map generation (Leaflet + offline canvas fallback)
- Master export_visual_artifacts() Interface Contract adherence
- Backwards compatibility with ASCII previews and raw PNG byte generation
"""

import json
import os
from pathlib import Path
import numpy as np
import pytest
from PIL import Image
import shapely.geometry

from eo_mcp.utils.visualizer import (
    get_output_dir,
    path_to_uri,
    get_colormap_lut,
    COLORMAP_LUTS,
    generate_ascii_preview,
    render_preview_png,
    array_to_png_bytes,
    export_geotiff,
    export_geojson,
    generate_standalone_map_html,
    export_visual_artifacts,
)


# ---------------------------------------------------------------------------
# Colormap & LUT Tests
# ---------------------------------------------------------------------------

def test_colormap_luts_palette_structure():
    """Verify all mandated 256-color LUT palettes are correctly initialized."""
    required_palettes = ["rdylgn", "blues", "ylorrd", "magma", "terrain"]
    for palette in required_palettes:
        lut = get_colormap_lut(palette)
        assert isinstance(lut, np.ndarray)
        assert lut.shape == (256, 3), f"LUT for {palette} must be shape (256, 3)"
        assert lut.dtype == np.uint8, f"LUT for {palette} must be uint8"

    # Case-insensitivity & alias handling
    assert np.array_equal(get_colormap_lut("RdYlGn"), get_colormap_lut("rdylgn"))
    assert np.array_equal(get_colormap_lut("BLUES"), get_colormap_lut("blues"))
    assert np.array_equal(get_colormap_lut("Yl_Or_Rd"), get_colormap_lut("ylorrd"))

    # Unknown colormap falls back gracefully without crashing
    unknown_lut = get_colormap_lut("non_existent_palette")
    assert unknown_lut.shape == (256, 3)


def test_colormap_color_progression():
    """Verify scientifically expected color transitions in key palettes."""
    # RdYlGn: Index 0 should be red-dominant; Index 255 should be green-dominant
    rdylgn = get_colormap_lut("RdYlGn")
    assert rdylgn[0, 0] > rdylgn[0, 1]  # Red > Green at low NDVI
    assert rdylgn[255, 1] > rdylgn[255, 0]  # Green > Red at high NDVI

    # Blues: Index 0 should be light/pale; Index 255 should be deep dark blue
    blues = get_colormap_lut("Blues")
    assert np.mean(blues[0]) > 200  # Pale / light water
    assert blues[255, 2] > blues[255, 0]  # Blue > Red at deep water

    # magma: Index 0 near-black; Index 255 high luminance (pale yellow)
    magma = get_colormap_lut("magma")
    assert np.mean(magma[0]) < 10
    assert np.mean(magma[255]) > 200

    # terrain: Index 255 snow white (255, 255, 255)
    terrain = get_colormap_lut("terrain")
    assert np.array_equal(terrain[255], [255, 255, 255])


# ---------------------------------------------------------------------------
# PNG Preview & NaN Transparency Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("palette", ["RdYlGn", "Blues", "YlOrRd", "magma", "terrain", "viridis"])
def test_render_preview_png_all_palettes(palette, tmp_path):
    """Verify PNG preview generation works cleanly across all palettes."""
    data = np.linspace(-1.0, 1.0, 1600).reshape((40, 40)).astype(np.float32)
    out_file = tmp_path / f"test_{palette}.png"

    res_path = render_preview_png(data, colormap=palette, output_path=out_file)
    assert Path(res_path).is_file()

    img = Image.open(out_file)
    assert img.mode == "RGBA"
    assert img.size == (40, 40)


def test_nan_transparency_in_preview(tmp_path):
    """Verify NaNs and NoData pixels receive alpha=0 (fully transparent)."""
    h, w = 40, 40
    data = np.ones((h, w), dtype=np.float32) * 0.75

    # Top-left quadrant has NaNs
    data[:20, :20] = np.nan
    # Bottom-left quadrant has explicit nodata value
    data[20:, :20] = -9999.0

    out_file = tmp_path / "transparency_test.png"
    render_preview_png(data, colormap="RdYlGn", output_path=out_file, nodata=-9999.0)

    img = Image.open(out_file)
    rgba = np.array(img)

    # NaNs should have alpha == 0
    assert np.all(rgba[:20, :20, 3] == 0), "NaN pixels must have alpha=0 (transparent)"
    # Nodata pixels should have alpha == 0
    assert np.all(rgba[20:, :20, 3] == 0), "NoData pixels must have alpha=0 (transparent)"
    # Valid pixels should have alpha == 255
    assert np.all(rgba[:20, 20:, 3] == 255), "Valid pixels must have alpha=255 (opaque)"
    assert np.all(rgba[20:, 20:, 3] == 255), "Valid pixels must have alpha=255 (opaque)"


def test_all_nan_array_preview(tmp_path):
    """Verify all-NaN array produces valid transparent image without crashing."""
    data = np.full((30, 30), np.nan, dtype=np.float32)
    out_file = tmp_path / "all_nan.png"

    render_preview_png(data, output_path=out_file)
    img = Image.open(out_file)
    rgba = np.array(img)
    assert np.all(rgba[:, :, 3] == 0)


def test_3d_array_preview_squeezes_first_band(tmp_path):
    """Verify 3D array uses first band for 2D PNG preview."""
    data = np.random.rand(3, 30, 30).astype(np.float32)
    out_file = tmp_path / "multiband_preview.png"
    render_preview_png(data, output_path=out_file)

    img = Image.open(out_file)
    assert img.size == (30, 30)
    assert img.mode == "RGBA"


# ---------------------------------------------------------------------------
# GeoTIFF Exporter Tests
# ---------------------------------------------------------------------------

def test_export_geotiff_bounds_crs_affine(tmp_path):
    """Verify GeoTIFF raster export sets correct CRS, Affine transform, and bounds."""
    from eo_mcp.utils.visualizer import HAS_RASTERIO
    if not HAS_RASTERIO:
        pytest.skip("rasterio is disabled or unavailable")
    rasterio = pytest.importorskip("rasterio")

    height, width = 50, 80
    data = np.random.rand(height, width).astype(np.float32)
    bbox = [-0.42, 39.42, -0.32, 39.50]  # Valencia bbox
    out_file = tmp_path / "valencia_test.tif"

    res_path = export_geotiff(data, bbox=bbox, output_path=out_file, crs="EPSG:4326")
    assert Path(res_path).is_file()

    with rasterio.open(out_file) as src:
        assert src.crs.to_string() == "EPSG:4326"
        assert src.count == 1
        assert src.height == height
        assert src.width == width
        assert src.bounds.left == pytest.approx(-0.42, rel=1e-5)
        assert src.bounds.bottom == pytest.approx(39.42, rel=1e-5)
        assert src.bounds.right == pytest.approx(-0.32, rel=1e-5)
        assert src.bounds.top == pytest.approx(39.50, rel=1e-5)

        read_data = src.read(1)
        assert np.allclose(data, read_data)


def test_export_geotiff_multiband(tmp_path):
    """Verify multiband 3D array export produces multi-channel GeoTIFF."""
    from eo_mcp.utils.visualizer import HAS_RASTERIO
    if not HAS_RASTERIO:
        pytest.skip("rasterio is disabled or unavailable")
    rasterio = pytest.importorskip("rasterio")

    bands, height, width = 4, 30, 40
    data = np.random.rand(bands, height, width).astype(np.float32)
    bbox = [10.0, 50.0, 11.0, 51.0]
    out_file = tmp_path / "multiband.tif"

    export_geotiff(data, bbox=bbox, output_path=out_file)

    with rasterio.open(out_file) as src:
        assert src.count == 4
        assert src.height == height
        assert src.width == width


# ---------------------------------------------------------------------------
# GeoJSON Exporter Tests
# ---------------------------------------------------------------------------

def test_export_geojson_feature_collection(tmp_path):
    """Verify GeoJSON FeatureCollection export."""
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-0.375, 39.465]},
                "properties": {"name": "Sensor 1", "risk": "high"}
            }
        ]
    }
    out_file = tmp_path / "points.geojson"
    export_geojson(fc, out_file)

    with open(out_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["type"] == "FeatureCollection"
    assert len(loaded["features"]) == 1
    assert loaded["features"][0]["properties"]["risk"] == "high"


def test_export_geojson_shapely_geometry(tmp_path):
    """Verify GeoJSON exporter handles Shapely geometry objects."""
    poly = shapely.geometry.box(-0.40, 39.44, -0.35, 39.48)
    out_file = tmp_path / "box.geojson"
    export_geojson(poly, out_file, properties={"type": "flood_zone"})

    with open(out_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["type"] == "FeatureCollection"
    assert len(loaded["features"]) == 1
    assert loaded["features"][0]["geometry"]["type"] == "Polygon"
    assert loaded["features"][0]["properties"]["type"] == "flood_zone"


# ---------------------------------------------------------------------------
# Standalone Interactive HTML Map Tests
# ---------------------------------------------------------------------------

def test_generate_standalone_map_html(tmp_path):
    """Verify self-contained single-file HTML map generation."""
    # Create sample PNG preview
    preview_png = tmp_path / "test_preview.png"
    arr = np.random.rand(30, 30).astype(np.float32)
    render_preview_png(arr, colormap="RdYlGn", output_path=preview_png)

    bbox = [-0.42, 39.42, -0.32, 39.50]
    out_html = tmp_path / "standalone_map.html"

    metrics = {
        "mean_ndvi": 0.5824,
        "max_ndvi": 0.8912,
        "inundated_hectares": 340.5
    }

    html = generate_standalone_map_html(
        preview_png_path=preview_png,
        bbox=bbox,
        title="Valencia Flood Inundation & Vegetation",
        vector_geojson={"type": "FeatureCollection", "features": []},
        colormap_legend="RdYlGn",
        metrics=metrics,
        output_path=out_html,
    )

    assert out_html.is_file()
    assert "<!DOCTYPE html>" in html
    assert "Valencia Flood Inundation & Vegetation" in html
    assert "data:image/png;base64," in html, "Preview PNG must be embedded as Base64 URI"
    assert "mean_ndvi" in html.lower() or "Mean Ndvi" in html
    assert "340.5" in html
    assert "leaflet" in html.lower()
    assert "initOfflineCanvas" in html, "Resilient offline canvas fallback must be present"
    assert "-0.42" in html
    assert "39.5" in html


def test_generate_standalone_map_html_vector_only(tmp_path):
    """Verify HTML map generation works when preview PNG is None (vector-only mode)."""
    bbox = [-122.5, 37.7, -122.3, 37.9]
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-122.4, 37.8]},
                "properties": {"incident": "fire_hotspot"}
            }
        ]
    }
    out_html = tmp_path / "vector_map.html"
    html = generate_standalone_map_html(
        preview_png_path=None,
        bbox=bbox,
        title="San Francisco Incidents",
        vector_geojson=geojson,
        output_path=out_html,
    )

    assert out_html.is_file()
    assert "San Francisco Incidents" in html
    assert "fire_hotspot" in html


# ---------------------------------------------------------------------------
# Master export_visual_artifacts() Coordinator Tests
# ---------------------------------------------------------------------------

def test_export_visual_artifacts_contract(tmp_path):
    """Verify export_visual_artifacts adheres strictly to PROJECT.md interface contract."""
    data = np.random.rand(50, 50).astype(np.float32)
    bbox = [-0.42, 39.42, -0.32, 39.50]
    vector_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-0.40, 39.44], [-0.35, 39.44], [-0.35, 39.48], [-0.40, 39.48], [-0.40, 39.44]
                    ]]
                },
                "properties": {"hazard": "flood"}
            }
        ]
    }

    result = export_visual_artifacts(
        array=data,
        bbox=bbox,
        name="valencia_ndvi_analysis",
        colormap="RdYlGn",
        vector_geojson=vector_data,
        output_dir=tmp_path,
        metrics={"mean": 0.54, "peak": 0.92},
        title="Valencia NDVI & Inundation"
    )

    # 1. Check all required contract keys exist
    expected_keys = [
        "preview_path", "preview_uri",
        "geotiff_path", "geotiff_uri",
        "geojson_path", "geojson_uri",
        "map_path", "map_uri",
        "visual_artifacts"
    ]
    for key in expected_keys:
        assert key in result, f"Key '{key}' missing from export_visual_artifacts result"

    # 2. Check files exist on disk
    assert Path(result["preview_path"]).is_file()
    if result["geotiff_path"] is not None:
        assert Path(result["geotiff_path"]).is_file()
    assert Path(result["geojson_path"]).is_file()
    assert Path(result["map_path"]).is_file()

    # 3. Check URIs format
    assert result["preview_uri"].startswith("file://")
    if result["geotiff_uri"] is not None:
        assert result["geotiff_uri"].startswith("file://")
    assert result["geojson_uri"].startswith("file://")
    assert result["map_uri"].startswith("file://")

    # 4. Check nested visual_artifacts sub-dict
    va = result["visual_artifacts"]
    assert va["preview_png"] == result["preview_path"]
    assert va["interactive_map"] == result["map_path"]
    assert va["geotiff"] == result["geotiff_path"]
    assert va["geojson"] == result["geojson_path"]


def test_export_visual_artifacts_without_geotiff(tmp_path):
    """Verify export_geotiff_raster=False omits GeoTIFF generation."""
    data = np.random.rand(30, 30).astype(np.float32)
    bbox = [0.0, 0.0, 1.0, 1.0]

    result = export_visual_artifacts(
        array=data,
        bbox=bbox,
        name="no_tif_test",
        output_dir=tmp_path,
        export_geotiff_raster=False
    )

    assert result["preview_path"] is not None
    assert result["geotiff_path"] is None
    assert result["geotiff_uri"] is None


def test_export_visual_artifacts_vector_only(tmp_path):
    """Verify vector-only execution omits raster preview and GeoTIFF cleanly."""
    bbox = [10.0, 20.0, 11.0, 21.0]
    vector_data = {"type": "FeatureCollection", "features": []}

    result = export_visual_artifacts(
        array=None,
        bbox=bbox,
        name="vector_only_test",
        vector_geojson=vector_data,
        output_dir=tmp_path
    )

    assert result["preview_path"] is None
    assert result["geotiff_path"] is None
    assert result["geojson_path"] is not None
    assert result["map_path"] is not None


# ---------------------------------------------------------------------------
# Output Directory Resolution Tests
# ---------------------------------------------------------------------------

def test_get_output_dir_custom_and_env(monkeypatch, tmp_path):
    """Verify output directory resolution order."""
    custom_dir = tmp_path / "custom_outputs"
    resolved = get_output_dir(custom_dir)
    assert resolved == custom_dir.resolve()
    assert resolved.is_dir()

    env_dir = tmp_path / "env_outputs"
    monkeypatch.setenv("EO_OUTPUT_DIR", str(env_dir))
    resolved_env = get_output_dir()
    assert resolved_env == env_dir.resolve()
    assert resolved_env.is_dir()


def test_path_to_uri():
    """Verify path_to_uri produces compliant file:// URIs."""
    p = Path("eo_outputs/sample.png")
    uri = path_to_uri(p)
    assert uri.startswith("file://")
    assert "sample.png" in uri


# ---------------------------------------------------------------------------
# Backwards Compatibility Tests
# ---------------------------------------------------------------------------

def test_generate_ascii_preview_backwards_compatible():
    """Verify legacy ASCII preview generation remains fully functional."""
    data = np.array([
        [0.1, 0.2, 0.8],
        [0.0, np.nan, 0.9],
        [-0.5, 0.3, 0.7]
    ], dtype=np.float32)
    preview = generate_ascii_preview(data, width=10, height=5)
    assert isinstance(preview, str)
    assert len(preview) > 0
    assert "@" in preview or "#" in preview  # density characters present


def test_array_to_png_bytes_backwards_compatible():
    """Verify array_to_png_bytes returns valid PNG binary stream."""
    data = np.random.rand(20, 20).astype(np.float32)
    png_bytes = array_to_png_bytes(data, colormap="RdYlGn")
    assert isinstance(png_bytes, bytes)
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n"), "Must start with PNG signature bytes"
