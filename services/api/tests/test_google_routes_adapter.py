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
