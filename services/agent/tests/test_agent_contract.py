from app.agent import AGENT_NAME, tollio_commute_agent
from app.models import AgentRequest


def sample_request() -> AgentRequest:
    return AgentRequest(
        user_message="Get me from Frisco to downtown Dallas by 8:30, but keep me under my $8 daily toll budget.",
        origin="Frisco",
        destination="Downtown Dallas",
        arrival_time="08:30",
        urgency_mode="balanced",
        daily_budget=8.0,
        weekly_budget=40.0,
        monthly_budget=160.0,
        budget_period="daily",
        toll_pass_type="NTTA TollTag",
        vehicle_mpg=28.0,
        gas_price=3.25,
        avoid_excessive_signals=True,
    )


def test_agent_returns_required_structured_fields(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.setenv("TOLLIO_AGENT_MODE", "mock")

    response = tollio_commute_agent(sample_request())
    body = response.model_dump()

    assert AGENT_NAME == "tollio_commute_agent"
    assert {
        "intent",
        "chosen_route",
        "route_options_considered",
        "gantry_decisions",
        "budget_status",
        "user_explanation",
        "next_actions",
        "saved_trip_id",
        "confidence_level",
        "data_sources_used",
    }.issubset(body.keys())
    assert response.data_sources_used == ["mock_tools"]
    assert response.saved_trip_id.startswith("mock-trip-")


def test_agent_output_includes_gantry_intelligence():
    response = tollio_commute_agent(sample_request())

    assert any(
        decision.action == "exit_before_gantry"
        for decision in response.gantry_decisions
    )
    assert response.budget_status.is_budget_preserved is True
