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


def test_live_mode_with_key_invokes_gemini_runtime_path(monkeypatch):
    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return (
                b'{"candidates":[{"content":{"parts":[{"text":"'
                b'{\\"short_explanation\\":\\"live short\\",'
                b'\\"detailed_explanation\\":\\"live detailed\\",'
                b'\\"driver_friendly_summary\\":\\"live summary\\",'
                b'\\"caution_notes\\":[\\"do not change decisions\\"]}'
                b'"}]}}]}'
            )

    def fake_urlopen(req, timeout):
        calls.append((req.full_url, timeout))
        return FakeResponse()

    monkeypatch.setenv("TOLLIO_AGENT_MODE", "live")
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    monkeypatch.setattr("app.services.explanation_service.urllib_request.urlopen", fake_urlopen)

    explanation = generate_explanation(build_commute_plan(_sample_request()))

    assert explanation.data_source == "live_gemini"
    assert explanation.short_explanation == "live short"
    assert calls
    assert "generativelanguage.googleapis.com" in calls[0][0]


def test_demo_gemini_invocation_endpoint_is_safe_without_credentials(monkeypatch):
    monkeypatch.setenv("TOLLIO_AGENT_MODE", "mock")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    response = client.get("/api/v1/demo/gemini-invocation")

    assert response.status_code == 200
    body = response.json()
    assert body["gemini_ready"] is False
    assert body["gemini_invoked"] is False
    assert body["explanation_data_source"] == "mock_explanation_service"


def test_demo_gemini_invocation_endpoint_uses_live_path_when_gated(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return (
                b'{"candidates":[{"content":{"parts":[{"text":"'
                b'{\\"short_explanation\\":\\"endpoint live\\",'
                b'\\"detailed_explanation\\":\\"endpoint detailed\\",'
                b'\\"driver_friendly_summary\\":\\"endpoint summary\\",'
                b'\\"caution_notes\\":[]}'
                b'"}]}}]}'
            )

    monkeypatch.setenv("TOLLIO_AGENT_MODE", "live")
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    monkeypatch.setattr(
        "app.services.explanation_service.urllib_request.urlopen",
        lambda req, timeout: FakeResponse(),
    )

    response = client.get("/api/v1/demo/gemini-invocation")

    assert response.status_code == 200
    body = response.json()
    assert body["gemini_ready"] is True
    assert body["gemini_invoked"] is True
    assert body["explanation_data_source"] == "live_gemini"
