"""Tests for GeoLibre integration, MapLibre HTML generator, and GeoAgent action planning."""

import json
import pytest
from eo_mcp.core.geolibre import (
    bbox_to_center_zoom,
    export_geolibre_project_json,
    plan_geoagent_actions,
    generate_interactive_maplibre_html
)
from eo_mcp.server import export_interactive_map, export_geolibre_project


def test_bbox_to_center_zoom():
    bbox = [-0.42, 39.42, -0.32, 39.50]
    cam = bbox_to_center_zoom(bbox)
    assert pytest.approx(cam["center"][0], 0.01) == -0.37
    assert pytest.approx(cam["center"][1], 0.01) == 39.46
    assert 1.0 <= cam["zoom"] <= 18.0


def test_export_geolibre_project_json():
    bbox = [-0.42, 39.42, -0.32, 39.50]
    layers = [
        {
            "id": "valencia_flood",
            "type": "fill",
            "source": {"type": "geojson", "data": {"type": "FeatureCollection", "features": []}}
        }
    ]
    proj = export_geolibre_project_json(
        title="Valencia Flood Inundation",
        bbox=bbox,
        layers=layers,
        basemap_theme="dark"
    )
    assert proj["name"] == "Valencia Flood Inundation"
    assert proj["created_with"] == "eo-mcp"
    assert len(proj["layers"]) == 1
    assert "map" in proj
    assert proj["map"]["bounds"] == bbox


def test_plan_geoagent_actions():
    bbox = [-0.42, 39.42, -0.32, 39.50]
    layers = [{"id": "flood_poly", "type": "fill", "source": "src1"}]
    actions = plan_geoagent_actions(bbox=bbox, layers=layers)
    assert len(actions) == 2
    assert actions[0]["tool"] == "flyTo"
    assert actions[1]["tool"] == "addLayer"
    assert actions[1]["parameters"]["id"] == "flood_poly"


def test_generate_interactive_maplibre_html():
    bbox = [-0.42, 39.42, -0.32, 39.50]
    sample_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"hazard": "flood", "depth_m": 1.2},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-0.40, 39.44], [-0.35, 39.44], [-0.35, 39.48], [-0.40, 39.48], [-0.40, 39.44]
                    ]]
                }
            }
        ]
    }
    html = generate_interactive_maplibre_html(
        title="Valencia Flood Map",
        bbox=bbox,
        geojson_data=sample_geojson,
        summary_metrics={"inundated_area_ha": 450.5, "max_depth_m": 2.1},
        hazard_type="flood"
    )
    assert "<!DOCTYPE html>" in html
    assert "maplibregl" in html
    assert "Valencia Flood Map" in html
    assert "inundated_area_ha" in html.lower() or "Inundated Area Ha" in html


def test_export_interactive_map_tool():
    bbox = [-0.42, 39.42, -0.32, 39.50]
    res_str = export_interactive_map(
        title="Test Interactive Map",
        bbox=bbox,
        geojson=json.dumps({"type": "FeatureCollection", "features": []})
    )
    res = json.loads(res_str)
    assert res["status"] == "success"
    assert res["title"] == "Test Interactive Map"
    assert "html_snippet" in res
