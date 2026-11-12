from __future__ import annotations

import argparse
import sys
from typing import Any

from mcp.server import MCPServer

from . import __version__
from .client import WdpaClient, WdpaError

DEFAULT_INSTRUCTIONS = """
WDPA MCP Server: Query the World Database on Protected Areas (WDPA) and Protected Planet
for national parks, nature reserves, marine protected areas, and conservation boundaries.

Key Best Practices:
1. When evaluating biodiversity observations (from iNaturalist, eBird, or GBIF), call
   `check_protected_area_nearby` with coordinates (`lat`, `lon`, `radius_km`) to determine
   if the wildlife sighting occurred inside or adjacent to a recognized conservation reserve.
2. Call `search_protected_areas` to find parks or wilderness reserves by name or country.
3. Call `get_protected_area_details` using a WDPA ID to inspect IUCN management categories
   (e.g., Ia Strict Nature Reserve, II National Park, VI Sustainable Use), legal designations,
   and governance arrangements.
4. Call `get_country_protection_coverage` to retrieve national terrestrial and marine protected
   area coverage percentages (monitoring progress toward global 30x30 biodiversity targets).
""".strip()


def _format_parks_summary(parks: list[dict[str, Any]]) -> str:
    if not parks:
        return "No protected areas found."
    lines = []
    for p in parks[:10]:
        name = p.get("name") or "Unnamed protected area"
        cat = p.get("iucn_category") or "N/A"
        dist = f" ({p.get('distance_km')} km away)" if "distance_km" in p else ""
        desig = p.get("designation") or "Reserve"
        lines.append(f"- {name} [{desig}, IUCN {cat}]{dist} (WDPA: {p.get('wdpa_id')})")
    return "\n".join(lines)


def create_server(client: WdpaClient | None = None) -> MCPServer:
    """Create and configure the WDPA / Protected Planet MCPServer instance."""
    api = client or WdpaClient()

    server = MCPServer(
        "wdpa",
        version=__version__,
        instructions=DEFAULT_INSTRUCTIONS,
    )

    @server.tool()
    def check_protected_area_nearby(
        lat: float,
        lon: float,
        radius_km: int = 25,
    ) -> dict[str, Any]:
        """Assess whether GPS coordinates fall within or near a protected conservation area."""
        try:
            res = api.check_protected_area_nearby(lat=lat, lon=lon, radius_km=radius_km)
            res["summary"] = _format_parks_summary(res["nearby_protected_areas"])
            return res
        except WdpaError as exc:
            return {
                "error": str(exc),
                "nearby_protected_areas": [],
                "summary": f"Proximity query failed: {exc}",
            }

    @server.tool()
    def search_protected_areas(
        query: str,
        country_code: str | None = None,
        limit: int = 15,
    ) -> dict[str, Any]:
        """Search protected conservation areas by name, designation, or ISO country."""
        try:
            areas = api.search_protected_areas(query=query, country_code=country_code, limit=limit)
            summary = _format_parks_summary(areas)
            return {"protected_areas": areas, "count": len(areas), "summary": summary}
        except WdpaError as exc:
            return {
                "error": str(exc),
                "protected_areas": [],
                "count": 0,
                "summary": f"Search failed: {exc}",
            }

    @server.tool()
    def get_protected_area_details(wdpa_id: int) -> dict[str, Any]:
        """Retrieve complete governance, IUCN management category, and area for a WDPA site."""
        try:
            details = api.get_protected_area_details(wdpa_id=wdpa_id)
            name = details.get("name")
            desig = details.get("designation")
            cat = details.get("iucn_category")
            gov = details.get("governance_type") or "Not reported"
            summary = (
                f"{name} (WDPA: {wdpa_id}) | Designation: {desig} | "
                f"IUCN Category: {cat} | Governance: {gov}"
            )
            return {"protected_area": details, "summary": summary}
        except WdpaError as exc:
            return {"error": str(exc), "summary": f"Details lookup failed: {exc}"}

    @server.tool()
    def get_country_protection_coverage(country_iso3: str) -> dict[str, Any]:
        """Retrieve national protected area coverage percentages and 30x30 statistics."""
        try:
            stats = api.get_country_protection_coverage(country_iso3=country_iso3)
            c_name = stats.get("country", country_iso3)
            land = stats.get("terrestrial_coverage_pct")
            marine = stats.get("marine_coverage_pct")
            total = stats.get("total_protected_areas")
            summary = (
                f"{c_name} ({country_iso3}): {land}% terrestrial protected, "
                f"{marine}% marine protected ({total} total protected areas)"
            )
            return {"country_statistics": stats, "summary": summary}
        except WdpaError as exc:
            return {"error": str(exc), "summary": f"Coverage query failed: {exc}"}

    return server


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="wdpa-mcp",
        description="Model Context Protocol (MCP) server for WDPA and Protected Planet",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol to use (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind for SSE transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind for SSE transport (default: 8000)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    server = create_server()
    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        server.run(transport="sse", host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
