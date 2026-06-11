from fastapi.testclient import TestClient

from app.data.ntta_matrix import find_road, get_matrix_price, load_matrix_roads
from app.services.tollio_brain import (
    BrainProfile,
    analyzeEntry,
    analyzeExit,
    entryVScore,
    exitVScore,
    matrix_brain_roads,
    optimizeTrip,
    unusedAhead,
    wastedBehind,
)
from main import app


client = TestClient(app)


def test_roads_endpoint_returns_loaded_roads():
    response = client.get("/api/v1/ntta/roads")

    assert response.status_code == 200
    roads = response.json()["roads"]
    assert any(road["road_short"] == "DNT" for road in roads)
    assert any(road["road_short"] == "PGBT" for road in roads)


def test_dnt_exits_load_from_pdf_matrix():
    response = client.get("/api/v1/ntta/exits", params={"road": "DNT"})

    assert response.status_code == 200
    exit_names = [item["exit_name"] for item in response.json()["exits"]]
    assert "Walnut Hill/Royal" in exit_names
    assert "Legacy" in exit_names
    assert "Trinity Mills/Frankford" in exit_names
    assert "IH 35E/Oaklawn/Wycliff" in exit_names


def test_get_price_returns_exact_known_dnt_pair_from_matrix():
    response = client.get(
        "/api/v1/ntta/price",
        params={
            "road": "DNT",
            "from_exit": "Walnut Hill/Royal",
            "to_exit": "Trinity Mills/Frankford",
            "payment": "tolltag",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["price"] == 1.38
    assert body["exact_matrix_match"] is True
    assert body["source_metadata"]["source_file"] == "NTTAS Toll Calculator_April 2025.pdf"


def test_zipcash_is_different_from_tolltag():
    road = find_road("DNT")

    tolltag = get_matrix_price(road, "Walnut Hill/Royal", "Trinity Mills/Frankford", "tolltag")
    zipcash = get_matrix_price(road, "Walnut Hill/Royal", "Trinity Mills/Frankford", "zipcash")

    assert tolltag.price == 1.38
    assert zipcash.price == 2.12
    assert zipcash.price != tolltag.price


def test_value_score_functions_work_from_matrix():
    road = next(item for item in matrix_brain_roads() if item.short == "DNT")

    assert entryVScore(road, 3, 11, "tolltag") > 0
    assert exitVScore(road, 3, 11, "tolltag") > 0
    assert wastedBehind(road, 3, 11, "tolltag") >= 0
    assert unusedAhead(road, 3, 11, "tolltag") >= 0


def test_analyze_entry_and_exit_find_matrix_improvements():
    road = next(item for item in matrix_brain_roads() if item.short == "DNT")
    profile = BrainProfile(toll_payment="tolltag", mpg=28, gas_price=3.25, traffic_mode="offpeak")

    entry = analyzeEntry(road.id, 3, 11, profile, matrix_brain_roads())
    exit_analysis = analyzeExit(road.id, 3, 11, profile, matrix_brain_roads())

    assert entry.suggestion is not None
    assert entry.suggestion.exit_idx > entry.natural.exit_idx
    assert exit_analysis.suggestion is not None
    assert exit_analysis.suggestion.exit_idx < exit_analysis.natural.exit_idx


def test_optimize_trip_returns_natural_and_optimized_route():
    road = next(item for item in matrix_brain_roads() if item.short == "DNT")
    profile = BrainProfile(toll_payment="tolltag", mpg=28, gas_price=3.25, traffic_mode="offpeak")

    result = optimizeTrip(road.id, 3, road.id, 11, profile, matrix_brain_roads())[0]

    assert result.natural_total == 1.38
    assert result.total_price < result.natural_total
    assert result.net_saving > 0
    assert result.segments[0].used_entry.exit_name != result.segments[0].entry_analysis.natural.exit_name


def test_missing_rates_are_unknown_not_invented():
    road = find_road("DNT")
    lookup = get_matrix_price(road, "Not A Real Entry", "Trinity Mills/Frankford", "tolltag")

    assert lookup.price is None
    assert lookup.confidence == "unknown"
    assert lookup.exact_matrix_match is False


def test_optimize_entry_exit_endpoint_returns_brain_shape():
    response = client.post(
        "/api/v1/optimize/entry-exit",
        json={
            "road": "DNT",
            "from_exit": "Walnut Hill/Royal",
            "to_exit": "Trinity Mills/Frankford",
            "payment": "tolltag",
            "mpg": 28,
            "gas_price": 3.25,
            "vehicle_type": "gas",
            "traffic_mode": "offpeak",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["natural_route"]["toll_price"] == 1.38
    assert body["optimized_route"]["net_saving"] > 0
    assert len(body["ranked_options"]) >= 3
    assert body["explanation"]


def test_matrix_json_contains_multiple_roads():
    roads = load_matrix_roads()

    assert len(roads) >= 2
    assert any(road.road_short == "PGBT" for road in roads)
