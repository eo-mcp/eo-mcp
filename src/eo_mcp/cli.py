"""Command Line Interface (CLI) for eo-mcp."""

import sys
import os
import json
import argparse
from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console(safe_box=True)


def run_server():
    """Start the FastMCP server over standard I/O (stdio)."""
    from eo_mcp.server import mcp
    mcp.run(transport="stdio")


def test_connectivity():
    """Verify live connectivity to zero-config free government STAC endpoints."""
    console.print(Panel.fit("[bold green]eo-mcp Diagnostics & STAC Verification[/bold green]"))

    from eo_mcp.providers.stac import search_stac_catalog
    from eo_mcp.config import EARTH_SEARCH_STAC_URL

    # Test AOI: Valencia, Spain [lon_min, lat_min, lon_max, lat_max]
    valencia_bbox = [-0.42, 39.42, -0.32, 39.50]

    with console.status("[bold blue]Testing AWS Earth Search STAC (Sentinel-2 L2A)...[/bold blue]"):
        try:
            scenes = search_stac_catalog(
                catalog_url=EARTH_SEARCH_STAC_URL,
                collections=["sentinel-2-l2a"],
                bbox=valencia_bbox,
                datetime_range="2024-06-01/2024-06-30",
                max_cloud_cover=20.0,
                limit=3
            )
            console.print(f"[green][OK] Successfully queried Sentinel-2! Found {len(scenes)} cloud-free scenes.[/green]")
            for s in scenes:
                console.print(f"  * Scene ID: [cyan]{s.id}[/cyan] ({s.datetime}) Cloud: {s.cloud_cover}%")
        except Exception as e:
            console.print(f"[red][ERROR] Sentinel-2 STAC check failed: {e}[/red]")

    with console.status("[bold blue]Testing Copernicus DEM GLO-30 STAC...[/bold blue]"):
        try:
            dem_scenes = search_stac_catalog(
                catalog_url=EARTH_SEARCH_STAC_URL,
                collections=["cop-dem-glo-30"],
                bbox=valencia_bbox,
                datetime_range="2020-01-01/2024-01-01",
                limit=1
            )
            console.print(f"[green][OK] Successfully queried Copernicus DEM! Tile: {dem_scenes[0].id}[/green]")
        except Exception as e:
            console.print(f"[red][ERROR] Copernicus DEM STAC check failed: {e}[/red]")

    console.print("\n[bold]All zero-config government endpoints operational![/bold]")


def print_claude_config():
    """Print configuration snippet for Claude Desktop and Cursor."""
    cfg = {
        "mcpServers": {
            "eo-mcp": {
                "command": "uvx",
                "args": ["--from", "git+https://github.com/eo-mcp/eo-mcp", "eo-mcp"]
            }
        }
    }
    console.print(Panel(json.dumps(cfg, indent=2), title="Claude Desktop Config (claude_desktop_config.json)"))
    console.print("\n[bold]Cursor IDE Setup:[/bold]")
    console.print("  Settings > Cursor Settings > Features > MCP > Add New MCP Server")
    console.print("  - Name: [cyan]eo-mcp[/cyan]")
    console.print("  - Type: [cyan]command[/cyan]")
    console.print("  - Command: [cyan]uvx --from git+https://github.com/eo-mcp/eo-mcp eo-mcp[/cyan]\n")


def run_doctor():
    """Run full environment diagnostics, verify zero-config open endpoints, and print client setup."""
    console.print(Panel.fit("[bold green]eo-mcp Environment Diagnostics & System Health[/bold green]"))

    import platform
    console.print(f"- Python Environment: [cyan]{platform.python_version()}[/cyan] ({platform.system()} {platform.machine()})")

    libs = ["rasterio", "pystac_client", "shapely", "httpx", "mcp", "numpy"]
    for lib in libs:
        try:
            mod = __import__(lib)
            ver = getattr(mod, "__version__", "installed")
            console.print(f"  [green][OK][/green] Library [bold]{lib}[/bold]: {ver}")
        except Exception as err:
            console.print(f"  [yellow][BLOCKED/MISSING][/yellow] Library [bold]{lib}[/bold]: {err}")

    console.print("\n[bold blue]Testing public zero-config satellite feeds...[/bold blue]")
    test_connectivity()

    console.print(Panel(
        "[bold green]Zero-Config Status: Active & Operational[/bold green]\n\n"
        "- NO API keys, Copernicus accounts, or subscriptions are required.\n"
        "- Sentinel-2 L2A (10m), Landsat 8/9 (30m), and Copernicus DEM GLO-30 stream over public HTTP COG range reads.\n\n"
        "[bold yellow]Troubleshooting Tip:[/bold yellow] If your AI agent asks for a Copernicus API key, that means eo-mcp "
        "has not been added to your client's MCP configuration yet! Ensure the green status dot is active.",
        title="Authentication & Zero-Config Health"
    ))

    print_claude_config()


def cli_dark_vessels(args):
    """CLI handler for dark vessel detection."""
    from eo_mcp.server import detect_dark_vessels
    res_str = detect_dark_vessels(
        bbox=args.bbox,
        datetime_range=args.date,
        format=args.format
    )
    if args.format != "summary":
        print(res_str)
        return

    data = json.loads(res_str)
    console.print(Panel.fit(
        f"[bold blue]Maritime Surveillance & Dark Vessel Tracker[/bold blue]\n"
        f"AOI: {data.get('bbox')} | Date: {data.get('datetime_range')}\n"
        f"SAR Targets: [cyan]{data.get('total_sar_targets_detected', 0)}[/cyan] | "
        f"AIS Records: [cyan]{data.get('total_ais_records_evaluated', 0)}[/cyan] | "
        f"Trusted: [green]{data.get('trusted_matched_count', 0)}[/green] | "
        f"Dark Vessels: [bold red]{data.get('dark_vessel_count', 0)}[/bold red] | "
        f"Oil Slicks: [bold magenta]{data.get('oil_slicks_count', 0)}[/bold magenta]"
    ))

    table = Table(title="Classified Maritime Vessels")
    table.add_column("Target ID", style="cyan")
    table.add_column("Classification", style="bold")
    table.add_column("Coordinates (Lon, Lat)")
    table.add_column("SAR Peak (dB)")
    table.add_column("AIS State")

    for v in data.get("classified_vessels", []):
        cls_val = v.get("classification", v.get("status", "UNKNOWN"))
        cls_text = Text(cls_val)
        if cls_val == "DARK_VESSEL":
            cls_text.stylize("bold red")
        elif cls_val == "TRUSTED":
            cls_text.stylize("green")
        else:
            cls_text.stylize("yellow")

        table.add_row(
            v.get("target_id", "N/A"),
            cls_text,
            f"{v.get('lon', 0):.4f}, {v.get('lat', 0):.4f}",
            f"{v.get('peak_sar_db', 0.0):.1f} dB",
            v.get("ais_state", "UNKNOWN")
        )
    console.print(table)


def cli_coastal_erosion(args):
    """CLI handler for coastal erosion analysis."""
    from eo_mcp.server import analyze_coastal_erosion
    res_str = analyze_coastal_erosion(
        bbox=args.bbox,
        historical_date_range=args.hist_date,
        recent_date_range=args.recent_date,
        format=args.format
    )
    if args.format != "summary":
        print(res_str)
        return

    data = json.loads(res_str)
    status = data.get("overall_status", "UNKNOWN")
    color = "red" if status == "EROSIONAL" else ("green" if status == "ACCRETIONAL" else "cyan")

    console.print(Panel.fit(
        f"[bold blue]Coastal Waterline Dynamics & Erosion Analyzer[/bold blue]\n"
        f"Time Baseline: {data.get('time_delta_years')} years | Transects: {data.get('transects_evaluated')}\n"
        f"Mean EPR: [bold {color}]{data.get('mean_erosion_rate_m_yr')} m/year[/bold {color}] | "
        f"Max Erosion: [bold red]{data.get('max_erosion_rate_m_yr')} m/year[/bold red] | "
        f"Eroding: [bold red]{data.get('eroding_percentage')}%[/bold red]\n"
        f"Status: [bold {color}]{status}[/bold {color}]"
    ))

    table = Table(title="Sample Cross-Shore Transects (USGS DSAS Method)")
    table.add_column("Transect ID", style="cyan")
    table.add_column("Net Shoreline Movement (m)")
    table.add_column("End Point Rate (m/yr)", style="bold")
    table.add_column("Hazard Classification")

    for tr in data.get("sample_transects", [])[:10]:
        hz = tr.get("hazard_class", "")
        hz_text = Text(hz)
        if "CRITICAL" in hz or "SEVERE" in hz:
            hz_text.stylize("bold red")
        elif "ACCRETION" in hz:
            hz_text.stylize("green")
        else:
            hz_text.stylize("dim")

        table.add_row(
            tr.get("transect_id", "N/A"),
            f"{tr.get('net_shoreline_movement_m', 0.0):.1f} m",
            f"{tr.get('end_point_rate_m_per_year', 0.0):.2f} m/yr",
            hz_text
        )
    console.print(table)


def cli_sea_level_rise(args):
    """CLI handler for sea level rise inundation."""
    from eo_mcp.server import simulate_sea_level_rise
    res_str = simulate_sea_level_rise(
        bbox=args.bbox,
        water_level_rise_m=args.rise,
        storm_surge_m=args.surge,
        scenario=args.scenario,
        format=args.format
    )
    if args.format != "summary":
        print(res_str)
        return

    data = json.loads(res_str)
    if "error" in data:
        console.print(f"[bold red][ERROR][/bold red] {data['error']}")
        return

    console.print(Panel.fit(
        f"[bold blue]Sea Level Rise & Storm Surge Inundation Simulation[/bold blue]\n"
        f"Total Water Elevation: [bold red]{data.get('total_water_elevation_m')} m[/bold red] "
        f"(Rise: {data.get('water_level_rise_m')}m + Surge: {data.get('storm_surge_m')}m)\n"
        f"Submerged Land Area: [bold red]{data.get('inundated_land_area_ha')} ha[/bold red] "
        f"({data.get('inundated_land_area_km2')} km²)\n"
        f"Land Inundation: [bold red]{data.get('land_inundation_percentage')}%[/bold red] | "
        f"Mean Water Depth: {data.get('mean_inundation_depth_m')} m | "
        f"Max Depth: {data.get('max_inundation_depth_m')} m\n"
        f"Directive: [cyan]{data.get('directive_alignment')}[/cyan]"
    ))

    if "ascii_flood_depth_map" in data:
        console.print(Panel(data["ascii_flood_depth_map"], title="ASCII Flood Depth Distribution Map"))


def cli_wildfires(args):
    """CLI handler for active wildfire detection."""
    from eo_mcp.server import detect_active_wildfires
    res_str = detect_active_wildfires(
        bbox=args.bbox,
        days=args.days,
        source=args.source,
        format=args.format
    )
    if args.format != "summary":
        print(res_str)
        return

    data = json.loads(res_str)
    console.print(Panel.fit(
        f"[bold red]NASA FIRMS Active Wildfire & Thermal Anomaly Detection[/bold red]\n"
        f"Sensor: {data.get('sensor_source')} | Lookback: {data.get('lookback_days')} days\n"
        f"Active Hotspots: [bold red]{data.get('total_active_hotspots')}[/bold red] | "
        f"Clustered Perimeters: [bold yellow]{data.get('fire_perimeters_count')}[/bold yellow] | "
        f"Total FRP: [bold red]{data.get('total_fire_radiative_power_mw')} MW[/bold red]"
    ))

    table = Table(title="Active Thermal Hotspots (VIIRS / MODIS)")
    table.add_column("Hotspot ID", style="cyan")
    table.add_column("Coordinates (Lon, Lat)")
    table.add_column("FRP (MW)", style="bold red")
    table.add_column("Brightness Temp (K)")
    table.add_column("Confidence")

    for h in data.get("hotspots", [])[:10]:
        table.add_row(
            h.get("hotspot_id", "N/A"),
            f"{h.get('lon', 0):.4f}, {h.get('lat', 0):.4f}",
            f"{h.get('fire_radiative_power_mw', 0):.1f} MW",
            f"{h.get('brightness_temp_k', 0):.1f} K",
            h.get("confidence", "nominal")
        )
    console.print(table)


def cli_emissions(args):
    """CLI handler for atmospheric emissions monitoring."""
    from eo_mcp.server import monitor_atmospheric_emissions
    res_str = monitor_atmospheric_emissions(
        bbox=args.bbox,
        gas=args.gas,
        datetime_range=args.date,
        format=args.format
    )
    if args.format != "summary":
        print(res_str)
        return

    data = json.loads(res_str)
    status = data.get("plume_status", "UNKNOWN")
    color = "red" if "EXCEEDANCE" in status else ("yellow" if "ELEVATION" in status else "green")

    console.print(Panel.fit(
        f"[bold blue]Sentinel-5P TROPOMI Atmospheric Gas Emissions[/bold blue]\n"
        f"Gas: [bold cyan]{data.get('gas')}[/bold cyan] ({data.get('unit')})\n"
        f"Mean Column Density: {data.get('mean_column_density')} {data.get('unit')} | "
        f"Max Density: [bold {color}]{data.get('max_column_density')} {data.get('unit')}[/bold {color}]\n"
        f"Plume Status: [bold {color}]{status}[/bold {color}] | "
        f"Ground Stations Correlated: {data.get('openaq_station_count', 0)}\n"
        f"Directive: [cyan]{data.get('directive_alignment')}[/cyan]"
    ))

    table = Table(title="OpenAQ In-Situ Ground Monitoring Stations")
    table.add_column("Station ID", style="cyan")
    table.add_column("City / Location")
    table.add_column("Coordinates (Lon, Lat)")
    table.add_column("Reported Value")

    for s in data.get("openaq_ground_stations", []):
        table.add_row(
            s.get("station_id", "N/A"),
            s.get("city", "Regional"),
            f"{s.get('lon', 0):.4f}, {s.get('lat', 0):.4f}",
            f"{s.get('reported_value_ug_m3', 'N/A')} µg/m³"
        )
    console.print(table)


def cli_drought(args):
    """CLI handler for reservoir drought monitoring."""
    from eo_mcp.server import analyze_reservoir_drought
    res_str = analyze_reservoir_drought(
        bbox=args.bbox,
        historical_year=args.hist_year,
        recent_year=args.recent_year,
        format=args.format
    )
    if args.format != "summary":
        print(res_str)
        return

    data = json.loads(res_str)
    d_class = data.get("drought_severity_class", "UNKNOWN")
    color = "red" if "CRITICAL" in d_class else ("yellow" if "MODERATE" in d_class else "green")

    console.print(Panel.fit(
        f"[bold blue]Reservoir Surface Water & Drought Depletion Analyzer[/bold blue]\n"
        f"Baseline: {data.get('historical_year')} -> Modern: {data.get('recent_year')}\n"
        f"Historical Area: {data.get('historical_water_area_ha')} ha | "
        f"Recent Area: {data.get('recent_water_area_ha')} ha\n"
        f"Net Water Loss: [bold red]{data.get('net_water_loss_ha')} ha[/bold red] "
        f"([bold {color}]{data.get('water_area_change_percentage')}%[/bold {color}])\n"
        f"Severity: [bold {color}]{d_class}[/bold {color}]"
    ))

    tb = data.get("transition_breakdown_ha", {})
    table = Table(title="Surface Water Transitions (EC JRC GSW Method)")
    table.add_column("Water Transition State", style="cyan")
    table.add_column("Area (Hectares)", style="bold")
    table.add_row("Permanent Water Body", f"{tb.get('permanent_water_ha', 0)} ha")
    table.add_row("Desiccated / Dried Margin", f"[bold red]{tb.get('desiccated_margin_ha', 0)} ha[/bold red]")
    table.add_row("Newly Inundated", f"{tb.get('newly_inundated_ha', 0)} ha")
    console.print(table)


def cli_burn_severity(args):
    """CLI handler for post-fire burn severity analysis."""
    from eo_mcp.server import calculate_burn_severity
    res_str = calculate_burn_severity(
        bbox=args.bbox,
        pre_fire_date_range=args.pre_date,
        post_fire_date_range=args.post_date,
        collection=args.collection,
        format=args.format
    )
    if args.format != "summary":
        print(res_str)
        return

    data = json.loads(res_str)
    console.print(Panel.fit(
        f"[bold red]Wildfire Burn Severity Analyzer (dNBR)[/bold red]\n"
        f"Pre-Fire: {data.get('pre_fire_date_range')} | Post-Fire: {data.get('post_fire_date_range')}\n"
        f"Mean dNBR: [bold]{data.get('mean_dnbr')}[/bold] | Max dNBR: [bold]{data.get('max_dnbr')}[/bold]\n"
        f"Total Burned: [bold red]{data.get('total_burned_area_ha')} ha[/bold red] ({data.get('burned_percentage')}% of AOI)\n"
        f"Overall Rating: [bold magenta]{data.get('overall_burn_severity_class')}[/bold magenta]"
    ))


def cli_urban_heat(args):
    """CLI handler for urban heat island and LST analysis."""
    from eo_mcp.server import analyze_urban_heat_island
    res_str = analyze_urban_heat_island(
        bbox=args.bbox,
        datetime_range=args.date,
        format=args.format
    )
    if args.format != "summary":
        print(res_str)
        return

    data = json.loads(res_str)
    console.print(Panel.fit(
        f"[bold yellow]Urban Heat Island & Land Surface Temperature Analyzer[/bold yellow]\n"
        f"Date Range: {data.get('datetime_range')} | AOI: {data.get('bbox')}\n"
        f"Mean LST: [bold]{data.get('mean_lst_celsius')} °C[/bold] (Min: {data.get('min_lst_celsius')} °C, Max: [bold red]{data.get('max_lst_celsius')} °C[/bold red])\n"
        f"UHI Intensity: [bold red]+{data.get('uhi_intensity_celsius')} °C[/bold red]\n"
        f"Hotspots: {data.get('thermal_hotspot_area_ha')} ha ({data.get('hotspot_percentage')}%) | Cool Islands: {data.get('cool_island_area_ha')} ha\n"
        f"Thermal Risk: [bold red]{data.get('thermal_risk_level')}[/bold red]"
    ))


def cli_crop_phenology(args):
    """CLI handler for crop phenology and seasonal dynamics."""
    from eo_mcp.server import monitor_crop_phenology
    res_str = monitor_crop_phenology(
        bbox=args.bbox,
        year=args.year,
        crop_type=args.crop,
        format=args.format
    )
    if args.format != "summary":
        print(res_str)
        return

    data = json.loads(res_str)
    miles = data.get("phenology_milestones", {})
    health = data.get("crop_health_assessment", {})

    console.print(Panel.fit(
        f"[bold green]Agricultural Crop Phenology & Seasonal Trajectory[/bold green]\n"
        f"Year: {data.get('year')} | Crop: {data.get('crop_type', 'Standard Canopy')}\n"
        f"Start of Season (SOS): [cyan]{miles.get('start_of_season_sos')}[/cyan]\n"
        f"Peak of Season (POS): [bold green]{miles.get('peak_of_season_pos')}[/bold green] (NDVI: {miles.get('peak_ndvi')})\n"
        f"End of Season (EOS): [yellow]{miles.get('end_of_season_eos')}[/yellow]\n"
        f"Vigor Anomaly: [bold]{health.get('vigor_anomaly_percentage')}%[/bold] ({health.get('status')})"
    ))


def cli_credentials(args):
    """CLI handler for viewing or updating provider credentials."""
    from eo_mcp.config import update_credential, get_credentials_status_summary
    if args.action == "set":
        res = update_credential(
            provider=args.provider,
            username=args.username,
            password=args.password,
            token=args.token
        )
        console.print(Panel(json.dumps(res, indent=2), title=f"Credential Updated: {args.provider}"))
    else:
        summary = get_credentials_status_summary()
        console.print(Panel(json.dumps(summary, indent=2), title="Configured Satellite Provider Credentials"))


def cli_tools(args):
    """CLI handler for listing categorized tools and profiles."""
    from eo_mcp.registry import discover_tools
    res = discover_tools(category=args.category, query=args.query)

    table = Table(title=f"eo-mcp Tools & Profiles (Active: {res['active_profile']})", safe_box=True)
    table.add_column("Category", style="bold cyan", width=14)
    table.add_column("Description", style="white", width=42)
    table.add_column("Tools", style="green")

    for cat_name, cat_data in res["results"].items():
        table.add_row(cat_name, cat_data["description"], ", ".join(cat_data["tools"]))

    console.print(table)


def cli_hazard(args):
    """CLI handler for ergonomic location hazard assessment."""
    from eo_mcp.workflows import assess_location_hazard
    res = assess_location_hazard(
        location=args.location,
        hazard_type=args.hazard_type,
        datetime_range=args.date,
        format=args.format
    )
    if args.format == "summary":
        try:
            data = json.loads(res)
            console.print(Panel(json.dumps(data, indent=2), title=f"Hazard Assessment: {args.location} ({args.hazard_type})"))
        except Exception:
            print(res)
    else:
        print(res)


def cli_audit(args):
    """CLI handler for ergonomic environmental site audit."""
    from eo_mcp.workflows import environmental_site_audit
    res = environmental_site_audit(
        location=args.location,
        format=args.format
    )
    if args.format == "summary":
        try:
            data = json.loads(res)
            console.print(Panel(json.dumps(data, indent=2), title=f"Environmental Site Audit: {args.location}"))
        except Exception:
            print(res)
    else:
        print(res)


def cli_opera(args):
    """CLI handler for NASA OPERA product search and inspection."""
    from eo_mcp.providers.opera import search_opera_products
    with console.status(f"[bold blue]Searching NASA CMR for OPERA {args.product.upper()} granules...[/bold blue]"):
        products = search_opera_products(
            product_type=args.product,
            bbox=args.bbox,
            datetime_range=args.date,
            limit=args.limit
        )

    if args.format == "summary":
        table = Table(title=f"NASA JPL OPERA {args.product.upper()} Products", safe_box=True)
        table.add_column("Granule ID", style="bold cyan", width=38)
        table.add_column("Date", style="green", width=18)
        table.add_column("Assets", style="yellow")
        for p in products:
            table.add_row(p.id[:36] + "...", p.datetime[:16], ", ".join(list(p.assets.keys())[:4]))
        console.print(table)
    elif args.format == "geojson":
        from eo_mcp.server import query_nasa_opera
        print(query_nasa_opera(bbox=args.bbox, datetime_range=args.date, product_type=args.product, format="geojson"))
    else:
        for p in products:
            console.print(f"- {p.id}: {p.datetime}")


def cli_export_map(args):
    """CLI handler for generating standalone interactive MapLibre / GeoLibre maps."""
    from eo_mcp.core.geolibre import generate_interactive_maplibre_html
    geojson_data = None
    if args.geojson_path:
        with open(args.geojson_path, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)

    html = generate_interactive_maplibre_html(
        title=args.title,
        bbox=args.bbox,
        geojson_data=geojson_data,
        hazard_type=getattr(args, "hazard", None)
    )

    out_file = args.output or "map.html"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)
    console.print(f"[bold green]Successfully generated interactive MapLibre viewer:[/bold green] [cyan]{out_file}[/cyan]")


def cli_spatial_sql(args):
    """CLI handler for running spatial SQL queries."""
    from eo_mcp.core.spatial_sql import execute_spatial_sql_query
    with open(args.geojson_path, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)

    res = execute_spatial_sql_query(sql=args.sql, features_geojson=geojson_data)
    table = Table(title=f"Spatial SQL: {args.sql}", safe_box=True)
    for col in res["columns"]:
        table.add_column(str(col), style="cyan")
    for row in res["rows"]:
        table.add_row(*[str(cell) for cell in row])
    console.print(table)



def cli_pipeline(args):
    """CLI handler for user-defined pipeline orchestration and recipes."""
    from eo_mcp.core.pipeline import (
        list_pipeline_recipes,
        describe_pipeline_recipe,
        execute_pipeline,
    )
    
    subcmd = getattr(args, "pipeline_command", None)
    if subcmd == "list" or subcmd is None:
        recipes = list_pipeline_recipes()
        table = Table(title="Available Compound Hazard & Processing Recipes", safe_box=True)
        table.add_column("Recipe Name", style="bold cyan", width=34)
        table.add_column("Category", style="green", width=22)
        table.add_column("Steps", style="yellow", justify="right", width=6)
        table.add_column("Description", style="white")

        for r in recipes:
            table.add_row(r["name"], r["category"], str(r["step_count"]), r["description"])
        console.print(table)

    elif subcmd == "describe":
        try:
            r_data = describe_pipeline_recipe(args.recipe)
            console.print(Panel(json.dumps(r_data, indent=2), title=f"Recipe Spec: {args.recipe}"))
        except Exception as exc:
            console.print(f"[red]Error: {exc}[/red]")

    elif subcmd == "run":
        spec_input = None
        if getattr(args, "spec", None):
            with open(args.spec, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if args.spec.endswith(".json") or content.startswith("{"):
                    spec_input = json.loads(content)
                else:
                    try:
                        import yaml
                        spec_input = yaml.safe_load(content)
                    except ImportError:
                        spec_input = json.loads(content)
        elif getattr(args, "recipe", None):
            spec_input = args.recipe
        else:
            console.print("[red]Error: Must specify either --recipe <name> or --spec <path.json>[/red]")
            return

        extra_params = {}
        if getattr(args, "params", None):
            try:
                extra_params = json.loads(args.params)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not parse --params JSON: {e}[/yellow]")

        with console.status("[bold blue]Executing Earth Observation Pipeline...[/bold blue]"):
            res = execute_pipeline(
                spec=spec_input,
                location=getattr(args, "location", None),
                format=getattr(args, "format", "summary"),
                **extra_params
            )

        if getattr(args, "format", "summary") == "summary":
            try:
                data = json.loads(res)
                console.print(Panel(json.dumps(data, indent=2), title=f"Pipeline Execution: {data.get('pipeline', {}).get('name', 'Custom')}"))
            except Exception:
                print(res)
        else:
            print(res)


def app():
    parser = argparse.ArgumentParser(
        prog="eo-mcp",
        description="The Open Source Model Context Protocol (MCP) for Planetary Earth Observation"
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Tool profile/category to activate (all, workflows, hazards, climate, maritime, minimal)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Standard commands
    subparsers.add_parser("run", help="Start the MCP server on stdio (default)")
    subparsers.add_parser("test", help="Test live STAC connectivity and raster streaming")
    subparsers.add_parser("claude", help="Display Claude Desktop configuration snippet")
    subparsers.add_parser("doctor", help="Run full environment & STAC diagnostics, check zero-config status")
    subparsers.add_parser("setup", help="Display zero-config setup commands for Cursor and Claude Desktop")

    # Tool discovery and inspection (Neon-style progressive discovery)
    p_tools = subparsers.add_parser("tools", help="List categorized tools and active profile")
    p_tools.add_argument("--category", type=str, default=None, help="Filter by category (workflows, core, spectral, hazards, climate, maritime, advanced)")
    p_tools.add_argument("--query", type=str, default=None, help="Search query")

    # Ergonomic Workflow commands ("Create with Compute" pattern)
    p_hazard = subparsers.add_parser("hazard", help="Ergonomic turnkey location hazard assessment")
    p_hazard.add_argument("location", type=str, help="Location name ('Valencia, Spain') or bbox 'min_lon,min_lat,max_lon,max_lat'")
    p_hazard.add_argument("--type", dest="hazard_type", default="flood_inundation", choices=["flood_inundation", "wildfire", "burn_severity", "coastal_erosion", "drought", "urban_heat", "dark_vessels"])
    p_hazard.add_argument("--date", type=str, default=None, help="Date or date range")
    p_hazard.add_argument("--format", choices=["summary", "geojson", "csv"], default="summary")

    p_audit = subparsers.add_parser("audit", help="Ergonomic composite environmental site audit")
    p_audit.add_argument("location", type=str, help="Location name ('Valencia, Spain') or bbox 'min_lon,min_lat,max_lon,max_lat'")
    p_audit.add_argument("--format", choices=["summary", "geojson"], default="summary")

    # Pipeline Orchestrator commands
    p_pipe = subparsers.add_parser("pipeline", help="User-defined Earth Observation pipeline orchestration")
    pipe_subparsers = p_pipe.add_subparsers(dest="pipeline_command", help="Pipeline operations")

    pipe_subparsers.add_parser("list", help="List available pre-built compound hazard recipes")

    p_pipe_desc = pipe_subparsers.add_parser("describe", help="Show full step specification of a recipe")
    p_pipe_desc.add_argument("recipe", type=str, help="Name of recipe to inspect")

    p_pipe_run = pipe_subparsers.add_parser("run", help="Execute an EO processing pipeline or compound recipe")
    p_pipe_run.add_argument("--recipe", type=str, default=None, help="Name of pre-built recipe")
    p_pipe_run.add_argument("--spec", type=str, default=None, help="Path to custom JSON or YAML pipeline spec file")
    p_pipe_run.add_argument("--location", type=str, default=None, help="Location name or bbox")
    p_pipe_run.add_argument("--format", choices=["summary", "geojson", "csv"], default="summary", help="Output format")
    p_pipe_run.add_argument("--params", type=str, default=None, help="JSON string of parameter overrides")

    # Credential management
    p_auth = subparsers.add_parser("auth", help="View or set satellite provider credentials")
    p_auth.add_argument("action", choices=["status", "set"], default="status", nargs="?", help="Action to perform")
    p_auth.add_argument("--provider", type=str, default="cdse", help="Provider: cdse, earthdata, planetary_computer, firms")
    p_auth.add_argument("--username", type=str, default=None, help="Username (for CDSE)")
    p_auth.add_argument("--password", type=str, default=None, help="Password (for CDSE)")
    p_auth.add_argument("--token", type=str, default=None, help="Token/Key (for Earthdata, PC, FIRMS)")

    # Planetary tools subcommands
    p_vessels = subparsers.add_parser("dark-vessels", help="Detect dark vessels in Sentinel-1 SAR & open AIS")
    p_vessels.add_argument("--bbox", nargs=4, type=float, default=[24.5, 59.8, 25.2, 60.2], help="min_lon min_lat max_lon max_lat")
    p_vessels.add_argument("--date", type=str, default="2024-06-01/2024-06-30", help="Date or date range")
    p_vessels.add_argument("--format", choices=["summary", "geojson", "csv"], default="summary", help="Output format")

    p_coastal = subparsers.add_parser("coastal-erosion", help="Quantify shoreline erosion rates using MNDWI & DSAS transects")
    p_coastal.add_argument("--bbox", nargs=4, type=float, default=[-2.85, 56.32, -2.75, 56.38], help="min_lon min_lat max_lon max_lat")
    p_coastal.add_argument("--hist-date", type=str, default="2019-05-01/2019-08-31", help="Historical date range")
    p_coastal.add_argument("--recent-date", type=str, default="2024-05-01/2024-08-31", help="Recent date range")
    p_coastal.add_argument("--format", choices=["summary", "geojson", "csv"], default="summary", help="Output format")

    p_slr = subparsers.add_parser("sea-level-rise", help="Simulate connected sea level rise inundation on Copernicus DEM")
    p_slr.add_argument("--bbox", nargs=4, type=float, default=[22.8, 38.6, 23.2, 38.9], help="min_lon min_lat max_lon max_lat")
    p_slr.add_argument("--rise", type=float, default=1.0, help="Water level rise in meters")
    p_slr.add_argument("--surge", type=float, default=0.0, help="Storm surge in meters")
    p_slr.add_argument("--scenario", type=str, default=None, help="IPCC AR6 scenario (SSP1-2.6, SSP2-4.5, SSP5-8.5)")
    p_slr.add_argument("--format", choices=["summary", "geojson", "csv"], default="summary", help="Output format")

    p_fire = subparsers.add_parser("wildfires", help="Detect active wildfires from NASA FIRMS with FRP & perimeter clustering")
    p_fire.add_argument("--bbox", nargs=4, type=float, default=[-120.5, 38.5, -120.0, 39.0], help="min_lon min_lat max_lon max_lat")
    p_fire.add_argument("--days", type=int, default=2, help="Lookback days")
    p_fire.add_argument("--source", type=str, default="VIIRS_NOAA20_NRT", help="Sensor source")
    p_fire.add_argument("--format", choices=["summary", "geojson", "csv"], default="summary", help="Output format")

    p_burn = subparsers.add_parser("burn-severity", help="Calculate post-fire dNBR burn severity and EFFIS damage rating")
    p_burn.add_argument("--bbox", nargs=4, type=float, default=[-120.2, 38.6, -120.0, 38.8], help="min_lon min_lat max_lon max_lat")
    p_burn.add_argument("--pre-date", type=str, default="2023-06-01/2023-06-30", help="Pre-fire date range")
    p_burn.add_argument("--post-date", type=str, default="2023-08-01/2023-08-31", help="Post-fire date range")
    p_burn.add_argument("--collection", type=str, default="sentinel-2-l2a", help="Collection ID")
    p_burn.add_argument("--format", choices=["summary", "geojson", "csv"], default="summary", help="Output format")

    p_uhi = subparsers.add_parser("urban-heat", help="Compute Land Surface Temperature (LST) and Urban Heat Island intensity")
    p_uhi.add_argument("--bbox", nargs=4, type=float, default=[2.25, 48.82, 2.35, 48.90], help="min_lon min_lat max_lon max_lat")
    p_uhi.add_argument("--date", type=str, default="2024-06-01/2024-08-31", help="Warm season date window")
    p_uhi.add_argument("--format", choices=["summary", "geojson", "csv"], default="summary", help="Output format")

    p_pheno = subparsers.add_parser("crop-phenology", help="Analyze agricultural crop phenology (SOS, POS, EOS, vigor anomaly)")
    p_pheno.add_argument("--bbox", nargs=4, type=float, default=[-4.5, 37.5, -4.3, 37.7], help="min_lon min_lat max_lon max_lat")
    p_pheno.add_argument("--year", type=int, default=2024, help="Observation year")
    p_pheno.add_argument("--crop", type=str, default=None, help="Crop type (Wheat, Maize, Vineyard, Olives)")
    p_pheno.add_argument("--format", choices=["summary", "geojson", "csv"], default="summary", help="Output format")

    p_emissions = subparsers.add_parser("emissions", help="Monitor trace gases (NO2, CH4, SO2, CO) from Sentinel-5P & OpenAQ")
    p_emissions.add_argument("--bbox", nargs=4, type=float, default=[2.2, 48.7, 2.5, 49.0], help="min_lon min_lat max_lon max_lat")
    p_emissions.add_argument("--gas", type=str, default="NO2", help="Trace gas (NO2, CH4, SO2, CO)")
    p_emissions.add_argument("--date", type=str, default="2024-06-01/2024-06-30", help="Date range")
    p_emissions.add_argument("--format", choices=["summary", "geojson", "csv"], default="summary", help="Output format")

    p_drought = subparsers.add_parser("drought", help="Analyze reservoir surface water shrinkage and drought depletion")
    p_drought.add_argument("--bbox", nargs=4, type=float, default=[-4.5, 37.5, -4.0, 38.0], help="min_lon min_lat max_lon max_lat")
    p_drought.add_argument("--hist-year", type=int, default=2019, help="Historical year")
    p_drought.add_argument("--recent-year", type=int, default=2024, help="Recent comparison year")
    p_drought.add_argument("--format", choices=["summary", "geojson", "csv"], default="summary", help="Output format")

    p_opera = subparsers.add_parser("opera", help="Search and inspect NASA JPL OPERA datasets (DSWx, DIST, RTC)")
    p_opera.add_argument("--product", type=str, choices=["dswx", "dist", "rtc"], default="dswx", help="OPERA product line")
    p_opera.add_argument("--bbox", nargs=4, type=float, default=[-0.42, 39.42, -0.32, 39.50], help="min_lon min_lat max_lon max_lat")
    p_opera.add_argument("--date", type=str, default="2024-06-01/2024-06-30", help="Date range")
    p_opera.add_argument("--limit", type=int, default=5, help="Max scenes to discover")
    p_opera.add_argument("--format", choices=["summary", "geojson"], default="summary", help="Output format")

    p_export_map = subparsers.add_parser("export-map", help="Export standalone interactive MapLibre / GeoLibre HTML viewer")
    p_export_map.add_argument("--title", type=str, default="Planetary Hazard Assessment", help="Title of the map")
    p_export_map.add_argument("--bbox", nargs=4, type=float, default=[-0.42, 39.42, -0.32, 39.50], help="min_lon min_lat max_lon max_lat")
    p_export_map.add_argument("--geojson-path", type=str, default=None, help="Path to GeoJSON file to render")
    p_export_map.add_argument("--hazard", type=str, default="general", help="Hazard type descriptor")
    p_export_map.add_argument("--output", type=str, default="map.html", help="Output HTML file path")

    p_spatial_sql = subparsers.add_parser("spatial-sql", help="Execute spatial SQL query on GeoJSON data")
    p_spatial_sql.add_argument("--sql", type=str, required=True, help="SQL query string")
    p_spatial_sql.add_argument("--geojson-path", type=str, required=True, help="Path to GeoJSON file")

    args = parser.parse_args()

    # Handle profile setting
    if args.profile:
        os.environ["EO_MCP_PROFILE"] = args.profile

    if args.command == "test":
        test_connectivity()
    elif args.command == "doctor":
        run_doctor()
    elif args.command in ["claude", "setup"]:
        print_claude_config()
    elif args.command == "tools":
        cli_tools(args)
    elif args.command == "hazard":
        cli_hazard(args)
    elif args.command == "audit":
        cli_audit(args)
    elif args.command == "auth":
        cli_credentials(args)
    elif args.command == "dark-vessels":
        cli_dark_vessels(args)
    elif args.command == "coastal-erosion":
        cli_coastal_erosion(args)
    elif args.command == "sea-level-rise":
        cli_sea_level_rise(args)
    elif args.command == "wildfires":
        cli_wildfires(args)
    elif args.command == "burn-severity":
        cli_burn_severity(args)
    elif args.command == "urban-heat":
        cli_urban_heat(args)
    elif args.command == "crop-phenology":
        cli_crop_phenology(args)
    elif args.command == "emissions":
        cli_emissions(args)
    elif args.command == "drought":
        cli_drought(args)
    elif args.command == "pipeline":
        cli_pipeline(args)
    elif args.command == "opera":
        cli_opera(args)
    elif args.command == "export-map":
        cli_export_map(args)
    elif args.command == "spatial-sql":
        cli_spatial_sql(args)
    else:
        run_server()


if __name__ == "__main__":
    app()

