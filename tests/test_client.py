from __future__ import annotations

import httpx
import pytest

from wdpa_mcp.client import WdpaClient, WdpaError


def test_client_init() -> None:
    client = WdpaClient(token="test-token", base_url="https://api.protectedplanet.net/v3/")
    assert client.base_url == "https://api.protectedplanet.net/v3"
    assert client.token == "test-token"


def test_fallback_search_and_proximity() -> None:
    client = WdpaClient(token=None)
    areas = client.search_protected_areas("Algonquin")
    assert len(areas) >= 1
    assert areas[0]["name"] == "Algonquin Provincial Park"
    assert areas[0]["wdpa_id"] == 2281

    details = client.get_protected_area_details(741)
    assert details["name"] == "Yellowstone National Park"
    assert details["iucn_category"] == "II"

    # Near Yellowstone coordinates: 44.6, -110.5
    nearby = client.check_protected_area_nearby(44.6, -110.5, radius_km=10)
    assert nearby["is_inside_or_adjacent"] is True
    assert len(nearby["nearby_protected_areas"]) >= 1

    # National coverage fallback
    cov = client.get_country_protection_coverage("CAN")
    assert cov["country"] == "Canada"
    assert cov["terrestrial_coverage_pct"] > 0


def test_search_protected_areas_api() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v3/protected_areas/search"
        assert request.url.params["token"] == "token123"
        return httpx.Response(
            200,
            json={
                "protected_areas": [
                    {
                        "id": 9999,
                        "name": "Kruger National Park",
                        "designation": {"name": "National Park"},
                        "iucn_category": {"name": "II"},
                        "countries": [{"name": "South Africa"}],
                        "reported_area": 19485.0,
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = WdpaClient(token="token123", transport=transport)
    results = client.search_protected_areas("Kruger", country_code="ZAF")
    assert len(results) == 1
    assert results[0]["name"] == "Kruger National Park"
    assert results[0]["wdpa_id"] == 9999


def test_get_protected_area_details_api() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v3/protected_areas/9999"
        return httpx.Response(
            200,
            json={
                "protected_area": {
                    "id": 9999,
                    "name": "Kruger National Park",
                    "designation": "National Park",
                    "iucn_category": "II",
                    "country": "South Africa",
                }
            },
        )

    transport = httpx.MockTransport(handler)
    client = WdpaClient(token="token123", transport=transport)
    details = client.get_protected_area_details(9999)
    assert details["name"] == "Kruger National Park"


def test_get_country_protection_coverage_api() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v3/countries/ZAF"
        return httpx.Response(
            200,
            json={
                "country": {
                    "name": "South Africa",
                    "statistics": {
                        "pame_percentage_pa_land_cover": 9.2,
                        "pame_percentage_pa_marine_cover": 15.5,
                        "pa_count": 1600,
                    },
                }
            },
        )

    transport = httpx.MockTransport(handler)
    client = WdpaClient(token="token123", transport=transport)
    stats = client.get_country_protection_coverage("ZAF")
    assert stats["country"] == "South Africa"
    assert stats["terrestrial_coverage_pct"] == 9.2


def test_error_handling() -> None:
    def handler_500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Protected Planet Error")

    client = WdpaClient(token="token123", transport=httpx.MockTransport(handler_500))
    with pytest.raises(WdpaError, match="Protected Planet API request failed"):
        client.get_protected_area_details(123456789)

    # When API fails for a known fallback park, it recovers from FALLBACK_PARKS
    details = client.get_protected_area_details(741)
    assert details["name"] == "Yellowstone National Park"

    # When API search fails, it falls back to local reference database
    search_fallback = client.search_protected_areas("Yellowstone")
    assert len(search_fallback) >= 1

    # When API country coverage fails, it falls back
    cov_fallback = client.get_country_protection_coverage("USA")
    assert cov_fallback["country"] == "United States"

    # Missing park without token raises WdpaError
    client_no_token = WdpaClient(token=None)
    with pytest.raises(WdpaError, match="not found"):
        client_no_token.get_protected_area_details(9999999)

    def handler_bad_json(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"invalid-json{")

    client2 = WdpaClient(token="token123", transport=httpx.MockTransport(handler_bad_json))
    with pytest.raises(WdpaError, match="Invalid JSON"):
        client2.get_protected_area_details(123456789)


def test_filter_protected_areas_by_designation() -> None:
    client = WdpaClient()

    # Ramsar filter
    ramsar = client.filter_protected_areas_by_designation(designation_type="Ramsar")
    assert len(ramsar) == 1
    assert "Okavango" in ramsar[0]["name"]

    # Marine filter
    marine = client.filter_protected_areas_by_designation(marine_only=True)
    assert len(marine) == 1
    assert "Great Barrier Reef" in marine[0]["name"]

    # IUCN category filter
    cat_ii = client.filter_protected_areas_by_designation(iucn_category="II")
    assert any("Yellowstone" in p["name"] for p in cat_ii)
