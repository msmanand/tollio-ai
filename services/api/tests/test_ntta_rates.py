import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.data.ntta_rates import load_ntta_rates
from main import app


client = TestClient(app)
RATES_PATH = Path(__file__).parents[1] / "app" / "data" / "ntta_rates_2025_2027.json"


def test_extracted_ntta_json_exists():
    assert RATES_PATH.exists()
    entries = json.loads(RATES_PATH.read_text())
    assert entries
    assert {
        "road_name",
        "toll_point_name",
        "toll_point_code",
        "vehicle_class",
        "tolltag_rate",
        "zipcash_rate",
        "source_url",
        "effective_start",
        "effective_end",
        "confidence",
    }.issubset(entries[0])


def test_coit_road_exists_with_official_rate():
    matches = [
        entry
        for entry in load_ntta_rates()
        if entry.toll_point_name == "Coit Road"
        and entry.vehicle_class == "two_axle_passenger"
    ]

    assert matches
    assert any(match.tolltag_rate == 0.78 for match in matches)
    assert any(match.zipcash_rate == 1.56 for match in matches)
    assert all(match.confidence == "exact" for match in matches)


def test_coit_main_lane_gantry_exists_with_official_rate():
    match = next(
        entry
        for entry in load_ntta_rates()
        if entry.toll_point_name == "Coit Main Lane Gantry"
        and entry.vehicle_class == "two_axle_passenger"
    )

    assert match.tolltag_rate == 1.65
    assert match.zipcash_rate == 3.30
    assert match.confidence == "exact"


def test_toll_point_dropdown_endpoint_returns_data():
    response = client.get("/api/v1/ntta/toll-points")

    assert response.status_code == 200
    body = response.json()
    assert body
    assert any(point["toll_point_name"] == "Coit Road" for point in body)
    assert all(point["vehicle_class"] == "two_axle_passenger" for point in body)


def test_missing_rates_are_unknown_not_invented():
    response = client.get("/api/v1/ntta/rates", params={"entry": "Not A Toll Point", "exit": "Coit Road"})

    assert response.status_code == 200
    body = response.json()
    assert body["exact_route_pricing_available"] is False
    assert body["entry_matches"][0]["confidence"] == "unknown"
    assert body["entry_matches"][0]["tolltag_rate"] is None
    assert body["entry_matches"][0]["zipcash_rate"] is None
    assert any(match["confidence"] == "exact" for match in body["exit_matches"])
