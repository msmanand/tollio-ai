from fastapi.testclient import TestClient

from app.routes import _candidate_explanation, _reject_candidate
from main import app


client = TestClient(app)


def _sample_body():
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
            "budget_amount": 8,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_api_returns_ranked_options_and_all_candidates():
    body = _sample_body()

    assert "best_recommendation" in body
    assert "ranked_options" in body
    assert "all_candidates" in body
    assert len(body["ranked_options"]) >= 3
    assert len(body["all_candidates"]) >= 3


def test_natural_best_value_and_cheapest_routes_exist():
    labels = {option["label"] for option in _sample_body()["all_candidates"]}

    assert "Natural Route" in labels
    assert "Best Value Route" in labels
    assert "Cheapest Route" in labels


def test_ranking_prefers_meaningful_savings():
    body = _sample_body()
    best = body["best_recommendation"]

    assert best["net_savings"] > 0
    assert best["confidence"] == "high"
    assert best["added_minutes"] <= 6


def test_tiny_savings_with_high_time_penalty_rejected():
    assert _reject_candidate({"label": "Candidate", "net_savings": 0.15, "added_minutes": 12}) is True
    assert _reject_candidate({"label": "Candidate", "net_savings": 1.2, "added_minutes": 2}) is False


def test_explanation_does_not_contradict_wasted_behind():
    for option in _sample_body()["all_candidates"]:
        metrics = option["metrics"]
        explanation = option["explanation"].lower()
        if metrics["wasted_behind"] >= metrics["natural_wasted_behind"]:
            assert "earlier toll tier" not in explanation
            assert "exits behind" not in explanation
            assert "road already passed" not in explanation


def test_explanation_does_not_contradict_unused_ahead():
    for option in _sample_body()["all_candidates"]:
        metrics = option["metrics"]
        explanation = option["explanation"].lower()
        if metrics["unused_ahead"] >= metrics["natural_unused_ahead"]:
            assert "unused paid distance ahead" not in explanation
            assert "unused road ahead" not in explanation
            assert "exits ahead" not in explanation


def test_explanation_does_not_contradict_entry_score():
    for option in _sample_body()["all_candidates"]:
        metrics = option["metrics"]
        explanation = option["explanation"].lower()
        if metrics["entry_value_score"] <= metrics["natural_entry_value_score"]:
            assert "improves entry utilization" not in explanation
            assert "improves the entry value score" not in explanation


def test_explanation_does_not_contradict_exit_score():
    for option in _sample_body()["all_candidates"]:
        metrics = option["metrics"]
        explanation = option["explanation"].lower()
        if metrics["exit_value_score"] <= metrics["natural_exit_value_score"]:
            assert "reduces unused paid distance ahead" not in explanation
            assert "improves the exit value score" not in explanation


def test_savings_without_utilization_explanation_is_handled():
    class Road:
        exits = ["A", "B", "C"]

    explanation = _candidate_explanation(
        Road(),
        natural_entry=0,
        natural_exit=2,
        entry_index=1,
        exit_index=2,
        toll_saved=1.2,
        net_savings=1.0,
        gas_cost=0.2,
        added_minutes=2,
        metrics={
            "wasted_behind": 0,
            "natural_wasted_behind": 0,
            "unused_ahead": 0,
            "natural_unused_ahead": 0,
            "entry_value_score": 80,
            "natural_entry_value_score": 80,
            "exit_value_score": 90,
            "natural_exit_value_score": 90,
        },
    )

    assert "matrix price is lower" in explanation
    assert "do not attribute the savings" in explanation
    assert "earlier toll tier" not in explanation
    assert "unused paid distance ahead" not in explanation
