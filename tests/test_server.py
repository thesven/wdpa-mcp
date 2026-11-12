from __future__ import annotations

import httpx
import pytest

from wdpa_mcp.client import WdpaClient, WdpaError
from wdpa_mcp.server import _format_parks_summary, create_server


@pytest.fixture
def mock_client() -> WdpaClient:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "/search" in path:
            return httpx.Response(
                200,
                json={
                    "protected_areas": [
                        {
                            "id": 741,
                            "name": "Yellowstone National Park",
                            "designation": {"name": "National Park"},
                            "iucn_category": {"name": "II"},
                        }
                    ]
                },
            )
        if "/protected_areas/741" in path:
            return httpx.Response(
                200,
                json={
                    "protected_area": {
                        "id": 741,
                        "name": "Yellowstone National Park",
                        "designation": "National Park",
                        "iucn_category": "II",
                    }
                },
            )
        if "/countries/USA" in path:
            return httpx.Response(
                200,
                json={
                    "country": {
                        "name": "United States",
                        "statistics": {"pame_percentage_pa_land_cover": 13.0, "pa_count": 35000},
                    }
                },
            )
        return httpx.Response(404, text="Not Found")

    return WdpaClient(token="mock-token", transport=httpx.MockTransport(handler))


@pytest.fixture
def failing_client() -> WdpaClient:
    class FailingClient(WdpaClient):
        def check_protected_area_nearby(self, lat: float, lon: float, radius_km: int = 25):
            raise WdpaError("Nearby failure")

        def search_protected_areas(
            self, query: str, country_code: str | None = None, limit: int = 15
        ):
            raise WdpaError("Search failure")

        def get_protected_area_details(self, wdpa_id: int):
            raise WdpaError("Details failure")

        def get_country_protection_coverage(self, country_iso3: str):
            raise WdpaError("Coverage failure")

        def list_country_protected_areas(self, *args, **kwargs):
            raise WdpaError("Country listing failure")

        def get_protected_area_boundary_envelope(self, *args, **kwargs):
            raise WdpaError("Envelope failure")

    return FailingClient()


def test_format_parks_summary() -> None:
    assert _format_parks_summary([]) == "No protected areas found."
    sample = [
        {
            "name": "Banff",
            "iucn_category": "II",
            "distance_km": 5,
            "designation": "NP",
            "wdpa_id": 1,
        }
    ]
    res = _format_parks_summary(sample)
    assert "Banff" in res
    assert "5 km away" in res


@pytest.mark.asyncio
async def test_server_tools(mock_client: WdpaClient) -> None:
    server = create_server(mock_client)

    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    assert "check_protected_area_nearby" in tool_names
    assert "search_protected_areas" in tool_names
    assert "get_protected_area_details" in tool_names
    assert "get_country_protection_coverage" in tool_names
    assert "filter_protected_areas_by_designation" in tool_names
    assert "list_country_protected_areas" in tool_names
    assert "get_protected_area_boundary_envelope" in tool_names

    res = await server.call_tool(
        "check_protected_area_nearby", {"lat": 44.6, "lon": -110.5, "radius_km": 15}
    )
    assert "Yellowstone" in res.content[0].text

    res = await server.call_tool("search_protected_areas", {"query": "Yellowstone"})
    assert "Yellowstone" in res.content[0].text

    res = await server.call_tool("get_protected_area_details", {"wdpa_id": 741})
    assert "Yellowstone" in res.content[0].text

    res = await server.call_tool("get_country_protection_coverage", {"country_iso3": "USA"})
    assert "United States" in res.content[0].text

    res = await server.call_tool(
        "filter_protected_areas_by_designation", {"designation_type": "National Park"}
    )
    assert "National Park" in res.content[0].text

    res = await server.call_tool("list_country_protected_areas", {"country_iso3": "CAN"})
    assert "Banff" in res.content[0].text or "Algonquin" in res.content[0].text

    res = await server.call_tool("get_protected_area_boundary_envelope", {"wdpa_id": 741})
    assert "Boundary envelope" in res.content[0].text


@pytest.mark.asyncio
async def test_server_tool_errors(failing_client: WdpaClient) -> None:
    server = create_server(failing_client)

    res1 = await server.call_tool("check_protected_area_nearby", {"lat": 0.0, "lon": 0.0})
    assert "Nearby failure" in res1.content[0].text

    res2 = await server.call_tool("search_protected_areas", {"query": "test"})
    assert "Search failure" in res2.content[0].text

    res3 = await server.call_tool("get_protected_area_details", {"wdpa_id": 9999999})
    assert "Details failure" in res3.content[0].text

    res4 = await server.call_tool("get_country_protection_coverage", {"country_iso3": "XYZ"})
    assert "Coverage failure" in res4.content[0].text

    res5 = await server.call_tool(
        "filter_protected_areas_by_designation", {"designation_type": "Ramsar"}
    )
    assert "Okavango" in res5.content[0].text

    res6 = await server.call_tool("list_country_protected_areas", {"country_iso3": "CAN"})
    assert "Country listing failure" in res6.content[0].text

    res7 = await server.call_tool("get_protected_area_boundary_envelope", {"wdpa_id": 999})
    assert "Envelope failure" in res7.content[0].text
