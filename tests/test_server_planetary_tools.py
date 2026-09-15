"""Integration tests for all 6 FastMCP planetary hazard and climate tools."""

import json
import pytest
from eo_mcp.server import (
    detect_dark_vessels,
    analyze_coastal_erosion,
    simulate_sea_level_rise,
    detect_active_wildfires,
    monitor_atmospheric_emissions,
    analyze_reservoir_drought
)


def test_server_dark_vessels_all_formats():
    bbox = [24.5, 59.8, 25.2, 60.2]
    dt = "2024-06-01/2024-06-30"

    # 1. Summary
    res_summary = detect_dark_vessels(bbox=bbox, datetime_range=dt, format="summary")
    data = json.loads(res_summary)
    assert "dark_vessels_count" in data
    assert "classified_vessels" in data
    assert "oil_slicks" in data

    # 2. GeoJSON
    res_geojson = detect_dark_vessels(bbox=bbox, datetime_range=dt, format="geojson")
    geo = json.loads(res_geojson)
    assert geo["type"] == "FeatureCollection"
    assert len(geo["features"]) > 0

    # 3. CSV
    res_csv = detect_dark_vessels(bbox=bbox, datetime_range=dt, format="csv")
    assert "target_id" in res_csv
    assert "status" in res_csv


def test_server_coastal_erosion_all_formats():
    bbox = [-2.85, 56.32, -2.75, 56.38]
    h_dt = "2019-05-01/2019-08-31"
    r_dt = "2024-05-01/2024-08-31"

    # 1. Summary
    res_summary = analyze_coastal_erosion(
        bbox=bbox, historical_date_range=h_dt, recent_date_range=r_dt, format="summary"
    )
    data = json.loads(res_summary)
    assert "mean_end_point_rate_m_yr" in data
    assert "transects" in data

    # 2. GeoJSON
    res_geojson = analyze_coastal_erosion(
        bbox=bbox, historical_date_range=h_dt, recent_date_range=r_dt, format="geojson"
    )
    geo = json.loads(res_geojson)
    assert geo["type"] == "FeatureCollection"
    assert len(geo["features"]) > 0

    # 3. CSV
    res_csv = analyze_coastal_erosion(
        bbox=bbox, historical_date_range=h_dt, recent_date_range=r_dt, format="csv"
    )
    assert "transect_id" in res_csv
    assert "end_point_rate_m_yr" in res_csv


def test_server_sea_level_rise_all_formats():
    bbox = [22.8, 38.6, 23.2, 38.9]

    # 1. Summary with IPCC scenario
    res_summary = simulate_sea_level_rise(bbox=bbox, scenario="SSP5-8.5", format="summary")
    data = json.loads(res_summary)
    assert "inundated_area_ha" in data
    assert "ipcc_scenario" in data

    # 2. GeoJSON
    res_geojson = simulate_sea_level_rise(bbox=bbox, water_level_rise_m=1.2, format="geojson")
    geo = json.loads(res_geojson)
    assert geo["type"] == "FeatureCollection"
    assert len(geo["features"]) == 1

    # 3. CSV
    res_csv = simulate_sea_level_rise(bbox=bbox, water_level_rise_m=1.2, format="csv")
    assert "water_level_rise_m" in res_csv
    assert "inundated_area_ha" in res_csv


def test_server_wildfires_all_formats():
    bbox = [-120.5, 38.5, -120.0, 39.0]

    # 1. Summary
    res_summary = detect_active_wildfires(bbox=bbox, days=2, format="summary")
    data = json.loads(res_summary)
    assert "total_active_hotspots" in data
    assert "fire_perimeters_count" in data

    # 2. GeoJSON
    res_geojson = detect_active_wildfires(bbox=bbox, days=2, format="geojson")
    geo = json.loads(res_geojson)
    assert geo["type"] == "FeatureCollection"

    # 3. CSV
    res_csv = detect_active_wildfires(bbox=bbox, days=2, format="csv")
    assert "hotspot_id" in res_csv


def test_server_emissions_all_formats():
    bbox = [2.2, 48.7, 2.5, 49.0]

    # 1. Summary
    res_summary = monitor_atmospheric_emissions(bbox=bbox, gas="NO2", format="summary")
    data = json.loads(res_summary)
    assert "mean_column_density" in data
    assert "openaq_station_count" in data

    # 2. GeoJSON
    res_geojson = monitor_atmospheric_emissions(bbox=bbox, gas="NO2", format="geojson")
    geo = json.loads(res_geojson)
    assert geo["type"] == "FeatureCollection"

    # 3. CSV
    res_csv = monitor_atmospheric_emissions(bbox=bbox, gas="NO2", format="csv")
    assert "gas" in res_csv


def test_server_drought_all_formats():
    bbox = [-4.5, 37.5, -4.0, 38.0]

    # 1. Summary
    res_summary = analyze_reservoir_drought(bbox=bbox, historical_year=2019, recent_year=2024, format="summary")
    data = json.loads(res_summary)
    assert "historical_water_area_ha" in data
    assert "drought_severity_class" in data

    # 2. GeoJSON
    res_geojson = analyze_reservoir_drought(bbox=bbox, historical_year=2019, recent_year=2024, format="geojson")
    geo = json.loads(res_geojson)
    assert geo["type"] == "FeatureCollection"

    # 3. CSV
    res_csv = analyze_reservoir_drought(bbox=bbox, historical_year=2019, recent_year=2024, format="csv")
    assert "historical_water_area_ha" in res_csv
