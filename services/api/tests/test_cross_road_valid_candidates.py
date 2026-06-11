from fastapi.testclient import TestClient

from app.data.ntta_matrix import find_road, find_exit_index
from main import app


client = TestClient(app)


def test_api_accepts_from_road_and_to_road_separately():
    response = client.post(
        "/api/v1/optimize/entry-exit",
        json={
            "from_road": "DNT",
            "from_exit": "Walnut Hill/Royal",
            "to_road": "DNT",
            "to_exit": "Trinity Mills/Frankford",
            "payment": "tolltag",
            "traffic_mode": "offpeak",
            "vehicle_type": "gas",
            "mpg": 28,
            "gas_price": 3.25,
        },
    )

    assert response.status_code == 200
    assert response.json()["natural_route"]["route_path_label"] == "DNT"


def test_same_road_trip_still_works():
    body = client.post(
        "/api/v1/optimize/entry-exit",
        json={
            "from_road": "DNT",
            "from_exit": "Walnut Hill/Royal",
            "to_road": "DNT",
            "to_exit": "Trinity Mills/Frankford",
            "payment": "tolltag",
            "traffic_mode": "offpeak",
            "vehicle_type": "gas",
            "mpg": 28,
            "gas_price": 3.25,
        },
    ).json()

    assert {option["label"] for option in body["all_candidates"]} == {
        "Natural Route",
        "Best Value Route",
        "Cheapest Route",
        "Fastest Compatible Route",
    }


def test_cross_road_request_returns_valid_connected_path():
    response = client.post(
        "/api/v1/optimize/entry-exit",
        json={
            "from_road": "DNT",
            "from_exit": "Walnut Hill/Royal",
            "to_road": "SH-121",
            "to_exit": "Coit",
            "payment": "tolltag",
            "traffic_mode": "offpeak",
            "vehicle_type": "gas",
            "mpg": 28,
            "gas_price": 3.25,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["natural_route"]["route_path_label"] == "DNT -> SH-121"
    assert all(option["route_path_label"] == "DNT -> SH-121" for option in body["all_candidates"])


def test_pgbt_to_sh121_uses_valid_connection_path_when_available():
    response = client.post(
        "/api/v1/optimize/entry-exit",
        json={
            "from_road": "PGBT",
            "from_exit": "DNT",
            "to_road": "SH-121",
            "to_exit": "Coit",
            "payment": "tolltag",
            "traffic_mode": "offpeak",
            "vehicle_type": "gas",
            "mpg": 28,
            "gas_price": 3.25,
        },
    )

    assert response.status_code == 200
    assert response.json()["natural_route"]["route_path_label"] == "PGBT -> DNT -> SH-121"


def test_cheapest_route_is_constrained_to_selected_same_road_trip():
    body = client.post(
        "/api/v1/optimize/entry-exit",
        json={
            "from_road": "DNT",
            "from_exit": "Walnut Hill/Royal",
            "to_road": "DNT",
            "to_exit": "Trinity Mills/Frankford",
            "payment": "tolltag",
            "traffic_mode": "offpeak",
            "vehicle_type": "gas",
            "mpg": 28,
            "gas_price": 3.25,
        },
    ).json()
    dnt = find_road("DNT")
    start = find_exit_index(dnt, "Walnut Hill/Royal")
    end = find_exit_index(dnt, "Trinity Mills/Frankford")
    cheapest = next(option for option in body["all_candidates"] if option["label"] == "Cheapest Route")

    entry_index = find_exit_index(dnt, cheapest["entry"])
    exit_index = find_exit_index(dnt, cheapest["exit"])
    assert start <= entry_index < exit_index <= end
    assert cheapest["route_path_label"] == "DNT"


def test_cross_road_candidates_do_not_use_unrelated_entries_or_exits():
    body = client.post(
        "/api/v1/optimize/entry-exit",
        json={
            "from_road": "DNT",
            "from_exit": "Walnut Hill/Royal",
            "to_road": "SH-121",
            "to_exit": "Coit",
            "payment": "tolltag",
            "traffic_mode": "offpeak",
            "vehicle_type": "gas",
            "mpg": 28,
            "gas_price": 3.25,
        },
    ).json()
    dnt = find_road("DNT")
    sh121 = find_road("SH-121")
    start = find_exit_index(dnt, "Walnut Hill/Royal")
    connector_exit = find_exit_index(dnt, "SRT")
    connector_entry = find_exit_index(sh121, "DNT")
    destination = find_exit_index(sh121, "Coit")

    for option in body["all_candidates"]:
        entry_index = find_exit_index(dnt, option["entry"])
        exit_index = find_exit_index(sh121, option["exit"])
        assert start <= entry_index <= connector_exit
        assert connector_entry <= exit_index <= destination


def test_explanation_does_not_claim_value_improved_when_score_drops():
    body = client.post(
        "/api/v1/optimize/entry-exit",
        json={
            "from_road": "DNT",
            "from_exit": "Walnut Hill/Royal",
            "to_road": "SH-121",
            "to_exit": "Coit",
            "payment": "tolltag",
            "traffic_mode": "offpeak",
            "vehicle_type": "gas",
            "mpg": 28,
            "gas_price": 3.25,
        },
    ).json()

    for option in body["all_candidates"]:
        explanation = option["explanation"].lower()
        if option["metrics"]["value_score"] < option["metrics"]["natural_value_score"]:
            assert "improves entry utilization" not in explanation
            assert "improves the entry value score" not in explanation
            assert "reduces unused paid distance ahead" not in explanation
            assert "improves the exit value score" not in explanation
            assert "even though utilization score is lower" in explanation
