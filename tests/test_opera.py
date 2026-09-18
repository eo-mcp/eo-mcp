"""Tests for NASA OPERA provider and query_nasa_opera tool."""

import json
import pytest
from eo_mcp.providers.opera import (
    search_opera_products,
    list_opera_product_types,
    OPERA_COLLECTIONS
)
from eo_mcp.server import query_nasa_opera


def test_list_opera_product_types():
    coll = list_opera_product_types()
    assert "dswx" in coll
    assert "dist" in coll
    assert "rtc" in coll
    assert coll["dswx"]["id"] == "OPERA_L3_DSWX-HLS_V1"


def test_search_opera_products():
    bbox = [-0.42, 39.42, -0.32, 39.50]
    date_range = "2024-06-01/2024-06-30"

    products = search_opera_products(
        product_type="dswx",
        bbox=bbox,
        datetime_range=date_range,
        limit=2
    )
    assert len(products) > 0
    prod = products[0]
    assert prod.product_type == "dswx"
    assert "B01_WTR" in prod.assets or len(prod.assets) > 0
    assert len(prod.bbox) == 4


def test_query_nasa_opera_tool_summary():
    bbox = [-0.42, 39.42, -0.32, 39.50]
    res_str = query_nasa_opera(
        bbox=bbox,
        datetime_range="2024-06-01/2024-06-30",
        product_type="dist",
        format="summary"
    )
    data = json.loads(res_str)
    assert data["provider"] == "NASA JPL OPERA via NASA CMR"
    assert data["product_type"] == "dist"
    assert data["granules_found"] >= 1
    assert "items" in data


def test_query_nasa_opera_tool_geojson():
    bbox = [-0.42, 39.42, -0.32, 39.50]
    res_str = query_nasa_opera(
        bbox=bbox,
        datetime_range="2024-06-01/2024-06-30",
        product_type="rtc",
        format="geojson"
    )
    data = json.loads(res_str)
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 1
    assert data["features"][0]["geometry"]["type"] == "Polygon"
