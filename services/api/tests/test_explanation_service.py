from fastapi.testclient import TestClient

from app.models import (
    BudgetPeriod,
    CommutePlanRequest,
)
from app.services.commute_planner import build_commute_plan
from app.services.explanation_service import (
    _build_gemini_prompt,
    generate_explanation,
)
from main import app


client = TestClient(app)


def _sample_request() -> CommutePlanRequest:
    return CommutePlanRequest(
        origin="Frisco",
        destination="Downtown Dallas",
        arrival_time="08:30",
        urgency_mode="balanced",
        daily_budget=8,
        weekly_budget=40,
        monthly_budget=160,
        budget_period=BudgetPeriod.daily,
        toll_pass_type="NTTA TollTag",
        vehicle_mpg=28,
        gas_price=3.25,
        avoid_excessive_signals=True,
    )


def test_mock_explanation_works_without_credentials(monkeypatch):
    monkeypatch.setenv("TOLLIO_AGENT_MODE", "mock")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    plan = build_commute_plan(_sample_request())
    explanation = generate_explanation(plan)

    assert explanation.data_source == "mock_explanation_service"
    assert explanation.short_explanation
    assert explanation.detailed_explanation
    assert explanation.driver_friendly_summary
    assert explanation.caution_notes


def test_explanation_includes_budget_toll_avoided_added_minutes_and_gantry_decision(monkeypatch):
    monkeypatch.setenv("TOLLIO_AGENT_MODE", "mock")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    plan = build_commute_plan(_sample_request())
    explanation = generate_explanation(plan)
    text = " ".join(
        [
            explanation.short_explanation,
            explanation.detailed_explanation,
            explanation.driver_friendly_summary,
        ]
    ).lower()

    assert "budget" in text
    assert "toll avoided" in text
    assert "added minutes" in text
    assert "gantry decision" in text


def test_live_mode_without_key_does_not_call_gemini(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Gemini should not be called without GEMINI_API_KEY")

    monkeypatch.setenv("TOLLIO_AGENT_MODE", "live")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(
        "app.services.explanation_service._generate_live_gemini_explanation",
        fail_if_called,
    )

    plan = build_commute_plan(_sample_request())
    explanation = generate_explanation(plan)

    assert explanation.data_source == "mock_explanation_service"


def test_commute_plan_preserves_existing_explanation_contract_safely(monkeypatch):
    monkeypatch.setenv("TOLLIO_AGENT_MODE", "mock")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    response = client.post(
        "/api/v1/commute/plan",
        json=_sample_request().model_dump(mode="json"),
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["explanation"], str)
    assert "deterministic gantry engine" in body["explanation"].lower()
    assert "gantry_decisions" in body


def test_gemini_prompt_keeps_deterministic_decisions_as_source_of_truth():
    plan = build_commute_plan(_sample_request())

    prompt = _build_gemini_prompt(plan)

    assert "Do not change toll decisions." in prompt
    assert "Do not invent route data." in prompt
    assert "Explain only the provided deterministic route/gantry/budget output." in prompt
