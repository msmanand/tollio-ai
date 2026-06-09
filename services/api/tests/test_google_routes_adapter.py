import json
from pathlib import Path

from app.adapters import google_routes_adapter


def test_adapter_returns_mock_route_options_without_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.setenv("ENABLE_LIVE_ROUTES", "false")

    routes = google_routes_adapter.get_route_options(
        "Frisco",
        "Downtown Dallas",
        "08:30",
        "balanced",
    )

    assert routes
    assert routes[0].data_source == "mock_google_routes_adapter"
    assert routes[0].segments
    assert routes[0].map_markers


def test_adapter_does_not_call_live_api_when_live_routes_disabled(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("live Google Routes API should not be called")

    monkeypatch.setenv("ENABLE_LIVE_ROUTES", "false")
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "placeholder-not-used")
    monkeypatch.setattr(google_routes_adapter, "_get_live_route_options", fail_if_called)

    routes = google_routes_adapter.get_route_options(
        "Frisco",
        "Downtown Dallas",
        "08:30",
        "balanced",
    )

    assert routes[0].data_source == "mock_google_routes_adapter"


def test_live_mode_without_key_does_not_call_live_api(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("live Google Routes API should not be called")

    monkeypatch.setenv("ENABLE_LIVE_ROUTES", "true")
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.setattr(google_routes_adapter, "_get_live_route_options", fail_if_called)

    routes = google_routes_adapter.get_route_options(
        "Frisco",
        "Downtown Dallas",
        "08:30",
        "urgent",
    )

    assert google_routes_adapter.live_routes_enabled() is False
    assert routes[0].data_source == "mock_google_routes_adapter"


def test_mock_mode_requires_no_secrets(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_ROUTES_API_KEY", raising=False)
    monkeypatch.setenv("ENABLE_LIVE_ROUTES", "false")

    assert google_routes_adapter.live_routes_enabled() is False
    assert google_routes_adapter.get_route_options("Frisco", "Downtown Dallas", "08:30", "balanced")


def test_normalize_route_segments_includes_distance_miles():
    segments = google_routes_adapter.normalize_route_segments(
        {
            "segments": [
                {
                    "segment_label": "Test segment",
                    "road_name": "Test Road",
                    "start_location": "A",
                    "end_location": "B",
                    "segment_type": "local_road",
                    "estimated_minutes": 3,
                    "estimated_cost": 0.0,
                    "distance_miles": 1.2,
                }
            ]
        }
    )

    assert segments[0].distance_miles == 1.2


def test_live_parser_handles_sample_google_routes_response_fixture():
    fixture_path = Path(__file__).parent / "fixtures" / "google_routes_sample.json"
    response_payload = json.loads(fixture_path.read_text())

    routes = google_routes_adapter._normalize_live_response(
        response_payload,
        origin="Frisco",
        destination="Downtown Dallas",
    )

    assert len(routes) == 1
    route = routes[0]
    assert route.route_id == "google_routes_1"
    assert route.route_label == "Google Routes option 1: DEFAULT_ROUTE"
    assert route.total_minutes == 42
    assert route.total_distance_miles == 30.0
    assert route.estimated_toll_cost == 7.25
    assert route.polyline == "sample_live_google_polyline"
    assert route.data_source == "live_google_routes_api"
    assert len(route.segments) == 2
    assert route.segments[0].segment_type == "toll"
    assert route.segments[0].estimated_cost == 7.25
    assert route.map_markers[0].marker_type == "origin"
