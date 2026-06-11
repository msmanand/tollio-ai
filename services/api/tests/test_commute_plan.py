from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def _sample_request():
    return {
        "origin": "Frisco",
        "destination": "Downtown Dallas",
        "arrival_time": "08:30",
        "urgency_mode": "balanced",
        "daily_budget": 8,
        "weekly_budget": 40,
        "monthly_budget": 160,
        "budget_period": "daily",
        "toll_pass_type": "NTTA TollTag",
        "vehicle_mpg": 28,
        "gas_price": 3.25,
        "avoid_excessive_signals": True,
    }


def test_commute_plan_returns_expected_fields():
    response = client.post("/api/v1/commute/plan", json=_sample_request())

    assert response.status_code == 200
    body = response.json()
    expected_fields = {
        "recommended_route_summary",
        "natural_route_cost",
        "optimized_route_cost",
        "estimated_savings",
        "added_minutes",
        "budget_impact",
        "gantry_decisions",
        "explanation",
        "confidence_level",
        "data_sources_used",
        "map_route_polyline",
        "natural_route_polyline",
        "optimized_route_polyline",
        "route_segments",
        "map_markers",
    }

    assert expected_fields.issubset(body.keys())
    assert body["optimized_route_cost"] == 4.13
    assert body["estimated_savings"] == 0.34
    assert body["optimized_route_polyline"] == "placeholder_exit_legacy_reenter_north_dallas"
    assert any(
        decision["action"] == "exit_before_gantry"
        for decision in body["gantry_decisions"]
    )


def test_invalid_urgency_mode_fails_validation():
    payload = _sample_request()
    payload["urgency_mode"] = "fastest"

    response = client.post("/api/v1/commute/plan", json=payload)

    assert response.status_code == 422


def test_gantry_decisions_not_empty_for_sample_route():
    response = client.post("/api/v1/commute/plan", json=_sample_request())

    assert response.status_code == 200
    assert response.json()["gantry_decisions"]
    assert any(
        "selected budget" in decision["budget_effect"]
        for decision in response.json()["gantry_decisions"]
    )


def test_commute_plan_includes_route_segments_from_adapter():
    response = client.post("/api/v1/commute/plan", json=_sample_request())

    assert response.status_code == 200
    route_segments = response.json()["route_segments"]
    assert route_segments
    assert route_segments[0]["road_name"] == "Dallas North Tollway"
    assert "distance_miles" in route_segments[0]
    assert route_segments[0]["tolltag_rate"] == 2.19
    assert route_segments[0]["zipcash_rate"] == 4.38
    assert route_segments[0]["rate_confidence"] == "exact"


def test_commute_plan_includes_map_markers_from_adapter():
    response = client.post("/api/v1/commute/plan", json=_sample_request())

    assert response.status_code == 200
    map_markers = response.json()["map_markers"]
    assert map_markers
    assert any(marker["marker_type"] == "exit" for marker in map_markers)


def test_commute_plan_returns_brain_recommendation_for_ntta_toll_points():
    payload = _sample_request()
    payload["origin"] = "Royal Lane"
    payload["destination"] = "Trinity Mills Main Lane Gantry"

    response = client.post("/api/v1/commute/plan", json=payload)

    assert response.status_code == 200
    body = response.json()
    recommendation = body["brain_recommendation"]
    assert recommendation["natural_entry"] == "Walnut Hill/Royal"
    assert recommendation["better_entry"] == "Forest/Harvest Hill"
    assert recommendation["natural_exit"] == "Trinity Mills/Frankford"
    assert recommendation["better_exit"] == "Keller Springs"
    assert recommendation["toll_saved"] > 0
    assert recommendation["net_saving"] > 0
    assert body["recommended_strategy"] is None
    assert [option["label"] for option in body["brain_options"]] == ["Natural Route", "Optimized Route"]
