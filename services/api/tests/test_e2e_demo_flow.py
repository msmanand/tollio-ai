import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)
FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


def test_full_demo_flow_from_commute_plan_to_save_and_budget_status():
    request_payload = _load_fixture("demo_commute_request.json")
    expected = _load_fixture("demo_expected_assertions.json")

    status_response = client.get("/api/v1/system/status")
    assert status_response.status_code == 200
    system_status = status_response.json()
    assert set(expected["required_status_fields"]).issubset(system_status.keys())
    assert system_status["api_status"] == "ok"
    assert system_status["routes_mode"] == "mock"

    commute_response = client.post("/api/v1/commute/plan", json=request_payload)
    assert commute_response.status_code == 200
    commute_plan = commute_response.json()
    assert set(expected["required_commute_fields"]).issubset(commute_plan.keys())

    route_segments = commute_plan["route_segments"]
    map_markers = commute_plan["map_markers"]
    gantry_decisions = commute_plan["gantry_decisions"]

    assert route_segments
    assert map_markers
    assert gantry_decisions
    assert any(marker["marker_type"] == expected["expected_origin_marker"] for marker in map_markers)
    assert any(marker["marker_type"] == expected["expected_destination_marker"] for marker in map_markers)

    assert commute_plan["optimized_route_cost"] <= expected["max_daily_budget"]
    assert commute_plan["estimated_savings"] > 0
    assert commute_plan["added_minutes"] >= 0
    assert any(segment["distance_miles"] >= 0 for segment in route_segments)
    assert any(decision["value_score"] >= 0 for decision in gantry_decisions)
    assert any(decision["toll_cost_avoided"] > 0 for decision in gantry_decisions)
    assert any(decision["added_minutes"] >= 0 for decision in gantry_decisions)
    assert any(
        "budget" in decision["budget_effect"].lower()
        or "budget" in decision["reason"].lower()
        or decision["toll_cost_avoided"] > 0
        for decision in gantry_decisions
    )

    concept_text = " ".join(
        [
            commute_plan["budget_impact"],
            commute_plan["explanation"],
            " ".join(decision["reason"] for decision in gantry_decisions),
            " ".join(segment["road_name"] for segment in route_segments),
            " ".join(marker["description"] for marker in map_markers),
        ]
    ).lower()
    assert "budget" in concept_text
    assert "toll" in concept_text
    assert "gantry" in concept_text
    assert route_segments and map_markers

    save_response = client.post(
        "/api/v1/trips/save",
        json={
            "commute_plan_id": "demo-frisco-downtown-0830",
            "user_label": "Frisco to Downtown Dallas by 8:30",
        },
    )
    assert save_response.status_code == 200
    assert save_response.json()["status"] in {"accepted", "saved"}

    budget_response = client.get("/api/v1/budget/status")
    assert budget_response.status_code == 200
    budget_status = budget_response.json()
    assert budget_status["budget_period"] == "daily"
    assert budget_status["budget_limit"] == expected["max_daily_budget"]
    assert budget_status["remaining_budget"] >= 0
