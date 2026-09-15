"""Unit and integration tests for the zero-infrastructure user-defined pipeline engine."""

import json
import pytest
from eo_mcp.core.pipeline import (
    list_pipeline_recipes,
    describe_pipeline_recipe,
    execute_pipeline,
    query_osm_infrastructure_exposure,
    PipelineContext,
    PipelineStep,
    RECIPES
)
from eo_mcp.server import (
    run_pipeline as server_run_pipeline,
    list_pipeline_recipes as server_list_pipeline_recipes,
    describe_pipeline_recipe as server_describe_pipeline_recipe
)


def test_list_and_describe_recipes():
    recipes = list_pipeline_recipes()
    assert len(recipes) >= 4
    recipe_names = [r["name"] for r in recipes]
    assert "compound_wildfire_runoff_risk" in recipe_names
    assert "coastal_storm_surge_infrastructure_exposure" in recipe_names
    assert "agricultural_drought_thermal_stress" in recipe_names
    assert "maritime_environmental_patrol" in recipe_names

    # Describe recipe
    spec = describe_pipeline_recipe("compound_wildfire_runoff_risk")
    assert spec["name"] == "compound_wildfire_runoff_risk"
    assert "steps" in spec
    assert len(spec["steps"]) == 6

    # Error handling for unknown recipe
    with pytest.raises(ValueError):
        describe_pipeline_recipe("non_existent_recipe")


def test_pipeline_context_variable_resolution():
    ctx = PipelineContext(
        name="test_pipeline",
        description="test",
        location_query="Valencia",
        bbox=[-0.42, 39.42, -0.32, 39.50],
        display_name="Valencia, Spain",
        parameters={"water_rise": 1.75, "alpha": "test_val"},
        variables={"step1_out": {"metric": 42}}
    )

    assert ctx.get_var("$parameters.water_rise") == 1.75
    assert ctx.get_var("$parameters.alpha") == "test_val"
    assert ctx.get_var("$parameters.missing", default=99) == 99
    assert ctx.get_var("$step1_out") == {"metric": 42}
    assert ctx.get_var("literal_string") == "literal_string"


def test_query_osm_infrastructure_exposure():
    bbox = [-0.42, 39.42, -0.32, 39.50]
    exp = query_osm_infrastructure_exposure(bbox=bbox, hazard_footprint_ha=75.0, timeout_sec=3.0)
    
    assert "data_source" in exp
    assert exp["aoi_area_km2"] > 0
    assert exp["total_transport_network_km"] > 0
    assert exp["exposed_transport_network_km"] >= 0
    assert "exposure_risk_tier" in exp
    assert exp["exposure_risk_tier"] in ("CRITICAL", "HIGH", "MODERATE", "LOW")
    assert "exposed_critical_facilities" in exp


def test_execute_coastal_storm_surge_recipe():
    res_str = execute_pipeline(
        spec="coastal_storm_surge_infrastructure_exposure",
        location=[-0.42, 39.42, -0.32, 39.50],
        format="summary",
        water_level_rise_m=1.5,
        storm_surge_m=0.5
    )
    data = json.loads(res_str)
    assert data["pipeline"]["status"] in ("SUCCESS", "PARTIAL_SUCCESS")
    assert data["pipeline"]["name"] == "coastal_storm_surge_infrastructure_exposure"
    assert "compound_risk_scorecard" in data
    assert "compound_risk_index_score" in data["compound_risk_scorecard"]
    assert "critical_infrastructure_exposure" in data
    assert len(data["step_execution_log"]) == 5


def test_execute_wildfire_runoff_recipe():
    res_str = execute_pipeline(
        spec="compound_wildfire_runoff_risk",
        location=[-120.2, 38.6, -120.0, 38.8],
        format="summary",
        days=2
    )
    data = json.loads(res_str)
    assert data["pipeline"]["status"] in ("SUCCESS", "PARTIAL_SUCCESS")
    assert len(data["step_execution_log"]) == 6
    assert "compound_risk_scorecard" in data


def test_execute_agricultural_drought_recipe():
    res_str = execute_pipeline(
        spec="agricultural_drought_thermal_stress",
        location=[-4.5, 37.5, -4.3, 37.7],
        format="summary"
    )
    data = json.loads(res_str)
    assert data["pipeline"]["status"] in ("SUCCESS", "PARTIAL_SUCCESS")
    assert len(data["step_execution_log"]) == 5


def test_execute_maritime_patrol_recipe():
    res_str = execute_pipeline(
        spec="maritime_environmental_patrol",
        location=[24.5, 59.8, 25.2, 60.2],
        format="summary"
    )
    data = json.loads(res_str)
    assert data["pipeline"]["status"] in ("SUCCESS", "PARTIAL_SUCCESS")
    assert len(data["step_execution_log"]) == 3


def test_execute_custom_user_spec():
    custom_spec = {
        "name": "custom_canopy_water_pipeline",
        "description": "User-defined NDVI and NDWI pipeline",
        "parameters": {
            "p_index": "ndvi"
        },
        "steps": [
            {
                "id": "s1_ndvi",
                "type": "spectral_index",
                "params": {"index_type": "$parameters.p_index"},
                "output_var": "veg_results"
            },
            {
                "id": "s2_ndwi",
                "type": "spectral_index",
                "params": {"index_type": "ndwi"},
                "output_var": "water_results"
            },
            {
                "id": "s3_exposure",
                "type": "exposure_overlay",
                "output_var": "exposure_results"
            },
            {
                "id": "s4_synthesis",
                "type": "compound_risk_synthesis",
                "output_var": "compound_summary"
            }
        ]
    }
    res_str = execute_pipeline(
        spec=custom_spec,
        location=[-0.42, 39.42, -0.32, 39.50],
        format="summary"
    )
    data = json.loads(res_str)
    assert data["pipeline"]["name"] == "custom_canopy_water_pipeline"
    assert data["pipeline"]["status"] == "SUCCESS"
    assert len(data["step_execution_log"]) == 4


def test_pipeline_geojson_format():
    res_geo = execute_pipeline(
        spec="coastal_storm_surge_infrastructure_exposure",
        location=[-0.42, 39.42, -0.32, 39.50],
        format="geojson"
    )
    geo = json.loads(res_geo)
    assert geo["type"] == "FeatureCollection"
    assert len(geo["features"]) >= 1
    types = [f["properties"]["feature_type"] for f in geo["features"]]
    assert "PIPELINE_AOI" in types


def test_pipeline_csv_format():
    csv_str = execute_pipeline(
        spec="coastal_storm_surge_infrastructure_exposure",
        location=[-0.42, 39.42, -0.32, 39.50],
        format="csv"
    )
    lines = [line.strip() for line in csv_str.strip().splitlines() if line.strip()]
    assert len(lines) >= 3
    assert "pipeline_name,location" in lines[0]
    assert "step_id,step_type,status" in csv_str


def test_server_fastmcp_pipeline_tools():
    # Test list_pipeline_recipes
    recipes_json = server_list_pipeline_recipes()
    recipes = json.loads(recipes_json)
    assert len(recipes) >= 4

    # Test describe_pipeline_recipe
    desc_json = server_describe_pipeline_recipe("agricultural_drought_thermal_stress")
    desc = json.loads(desc_json)
    assert desc["name"] == "agricultural_drought_thermal_stress"

    # Test run_pipeline tool
    run_res = server_run_pipeline(
        spec="agricultural_drought_thermal_stress",
        location="-0.42, 39.42, -0.32, 39.50",
        format="summary"
    )
    data = json.loads(run_res)
    assert data["pipeline"]["name"] == "agricultural_drought_thermal_stress"
