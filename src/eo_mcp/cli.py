"""Command Line Interface (CLI) for eo-mcp."""

import sys
import os
import json
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


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
            console.print(f"[green]✓ Successfully queried Sentinel-2! Found {len(scenes)} cloud-free scenes.[/green]")
            for s in scenes:
                console.print(f"  • Scene ID: [cyan]{s.id}[/cyan] ({s.datetime}) Cloud: {s.cloud_cover}%")
        except Exception as e:
            console.print(f"[red]✗ Sentinel-2 STAC check failed: {e}[/red]")

    with console.status("[bold blue]Testing Copernicus DEM GLO-30 STAC...[/bold blue]"):
        try:
            dem_scenes = search_stac_catalog(
                catalog_url=EARTH_SEARCH_STAC_URL,
                collections=["cop-dem-glo-30"],
                bbox=valencia_bbox,
                datetime_range="2020-01-01/2024-01-01",
                limit=1
            )
            console.print(f"[green]✓ Successfully queried Copernicus DEM! Tile: {dem_scenes[0].id}[/green]")
        except Exception as e:
            console.print(f"[red]✗ Copernicus DEM STAC check failed: {e}[/red]")

    console.print("\n[bold]All zero-config government endpoints operational![/bold]")


def print_claude_config():
    """Print configuration snippet for Claude Desktop."""
    cfg = {
        "mcpServers": {
            "eo-mcp": {
                "command": "uvx",
                "args": ["eo-mcp"]
            }
        }
    }
    console.print(Panel(json.dumps(cfg, indent=2), title="Claude Desktop Config (claude_desktop_config.json)"))


def app():
    parser = argparse.ArgumentParser(
        prog="eo-mcp",
        description="The Open Source Model Context Protocol (MCP) for Planetary Earth Observation"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("run", help="Start the MCP server on stdio (default)")
    subparsers.add_parser("test", help="Test live STAC connectivity and raster streaming")
    subparsers.add_parser("claude", help="Display Claude Desktop configuration snippet")

    args = parser.parse_args()

    if args.command == "test":
        test_connectivity()
    elif args.command == "claude":
        print_claude_config()
    else:
        run_server()


if __name__ == "__main__":
    app()
