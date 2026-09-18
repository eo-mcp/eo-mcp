"""Tests for Spatial SQL Analytics engine and query_spatial_sql tool."""

import json
import pytest
from eo_mcp.core.spatial_sql import execute_spatial_sql_query
from eo_mcp.server import query_spatial_sql


@pytest.fixture
def sample_features():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "poly_1",
                "properties": {"name": "Zone A", "severity": "HIGH", "score": 92.5},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0.0, 0.0], [0.01, 0.0], [0.01, 0.01], [0.0, 0.01], [0.0, 0.0]]]
                }
            },
            {
                "type": "Feature",
                "id": "poly_2",
                "properties": {"name": "Zone B", "severity": "LOW", "score": 41.0},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0.02, 0.02], [0.03, 0.02], [0.03, 0.03], [0.02, 0.03], [0.02, 0.02]]]
                }
            },
            {
                "type": "Feature",
                "id": "pt_1",
                "properties": {"name": "Sensor 1", "severity": "HIGH", "score": 88.0},
                "geometry": {
                    "type": "Point",
                    "coordinates": [0.005, 0.005]
                }
            }
        ]
    }


def test_spatial_sql_where_filter(sample_features):
    sql = "SELECT id, name, severity FROM features WHERE severity = 'HIGH'"
    res = execute_spatial_sql_query(sql, sample_features)
    assert res["count"] == 2
    assert "columns" in res
    assert "id" in res["columns"]


def test_spatial_sql_area_and_centroid(sample_features):
    sql = "SELECT id, ST_Area(geom) as area_ha, ST_Centroid(geom) as centroid FROM features WHERE severity = 'HIGH'"
    res = execute_spatial_sql_query(sql, sample_features)
    assert res["count"] == 2
    assert "area_ha" in res["columns"]
    assert "centroid" in res["columns"]


def test_query_spatial_sql_tool(sample_features):
    geojson_str = json.dumps(sample_features)
    sql = "SELECT id, name, score FROM features WHERE score > 50"
    res_str = query_spatial_sql(sql=sql, geojson=geojson_str)
    res = json.loads(res_str)
    assert res["count"] == 2
    assert len(res["rows"]) == 2
