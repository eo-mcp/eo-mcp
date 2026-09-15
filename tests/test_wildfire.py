"""Unit tests for NASA FIRMS wildfire & thermal anomaly detection engine."""

import pytest
import json
from eo_mcp.core.wildfire import (
    fetch_firms_hotspots,
    cluster_fire_perimeters,
    wildfires_to_geojson,
    wildfires_to_csv
)


def test_firms_hotspot_fetching():
    bbox = [-120.5, 38.5, -120.0, 39.0]
    hotspots = fetch_firms_hotspots(bbox=bbox, days=2, source="VIIRS_NOAA20_NRT")
    assert isinstance(hotspots, list)
    assert len(hotspots) > 0
    for h in hotspots:
        assert "hotspot_id" in h
        assert "lat" in h
        assert "lon" in h
        assert "fire_radiative_power_mw" in h
        assert h["fire_radiative_power_mw"] > 0
        assert "brightness_temp_k" in h
        assert h["brightness_temp_k"] > 273.15
        assert bbox[0] <= h["lon"] <= bbox[2]
        assert bbox[1] <= h["lat"] <= bbox[3]


def test_fire_perimeter_clustering():
    sample_hotspots = [
        {
            "hotspot_id": "FIRE-001",
            "lat": 38.601,
            "lon": -120.251,
            "fire_radiative_power_mw": 55.0,
            "brightness_temp_k": 355.0,
            "confidence": "high",
            "acquisition_date": "2024-06-15"
        },
        {
            "hotspot_id": "FIRE-002",
            "lat": 38.604,
            "lon": -120.253,
            "fire_radiative_power_mw": 65.0,
            "brightness_temp_k": 368.0,
            "confidence": "high",
            "acquisition_date": "2024-06-15"
        },
        {
            "hotspot_id": "FIRE-003",
            "lat": 38.850,
            "lon": -120.100,
            "fire_radiative_power_mw": 22.0,
            "brightness_temp_k": 325.0,
            "confidence": "nominal",
            "acquisition_date": "2024-06-15"
        }
    ]
    perimeters = cluster_fire_perimeters(sample_hotspots, cluster_dist_km=2.0)
    assert len(perimeters) == 2  # Two distinct geographic clusters

    # Find the larger cluster
    main_cluster = next(p for p in perimeters if p["active_hotspot_count"] == 2)
    assert main_cluster["total_fire_radiative_power_mw"] == 120.0
    assert main_cluster["fire_danger_class"] == "EXTREME"
    assert "polygon_coordinates" in main_cluster
    assert len(main_cluster["polygon_coordinates"]) == 5  # Closed ring


def test_wildfires_geojson_and_csv_export():
    hotspots = [
        {
            "hotspot_id": "FIRE-001",
            "lat": 38.601,
            "lon": -120.251,
            "fire_radiative_power_mw": 55.0,
            "brightness_temp_k": 355.0,
            "confidence": "high",
            "acquisition_date": "2024-06-15"
        }
    ]
    perimeters = cluster_fire_perimeters(hotspots, cluster_dist_km=2.0)
    results = {
        "bbox": [-120.5, 38.5, -120.0, 39.0],
        "lookback_days": 2,
        "sensor_source": "VIIRS_NOAA20_NRT",
        "total_active_hotspots": len(hotspots),
        "fire_perimeters_count": len(perimeters),
        "total_fire_radiative_power_mw": 55.0,
        "hotspots": hotspots,
        "perimeters": perimeters
    }

    # GeoJSON verification
    geojson = wildfires_to_geojson(results)
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 2  # 1 hotspot Point + 1 perimeter Polygon

    point_feat = next(f for f in geojson["features"] if f["geometry"]["type"] == "Point")
    assert "HOTSPOT" in point_feat["properties"]["feature_type"]
    assert point_feat["properties"]["fire_radiative_power_mw"] == 55.0

    poly_feat = next(f for f in geojson["features"] if f["geometry"]["type"] == "Polygon")
    assert poly_feat["properties"]["feature_type"] == "FIRE_PERIMETER"

    # CSV verification
    csv_str = wildfires_to_csv(results)
    assert "hotspot_id" in csv_str
    assert "fire_radiative_power_mw" in csv_str
    assert "FIRE-001" in csv_str
