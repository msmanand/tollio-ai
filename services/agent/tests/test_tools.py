from app.models import AgentRequest
from app.tools.budget_status_tool import budget_status_tool
from app.tools.gantry_intelligence_tool import gantry_intelligence_tool
from app.tools.route_options_tool import route_options_tool
from app.tools.save_trip_tool import save_trip_tool
from app.tools.toll_estimate_tool import toll_estimate_tool


def sample_request() -> AgentRequest:
    return AgentRequest(
        user_message="Plan my toll commute.",
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


def test_all_tools_can_be_called_independently():
    request = sample_request()
    routes = route_options_tool(request)
    tolls = toll_estimate_tool(request, routes)
    gantry_decisions = gantry_intelligence_tool(request, routes, tolls)
    budget = budget_status_tool(request, projected_toll_spend=6.25)
    saved = save_trip_tool(request, routes[1], gantry_decisions)

    assert routes
    assert tolls
    assert gantry_decisions
    assert budget.status == "budget_preserved"
    assert saved.saved_trip_id == "mock-trip-frisco-to-downtown-dallas"


def test_gantry_intelligence_recommends_exit_before_gantry():
    request = sample_request()
    routes = route_options_tool(request)
    tolls = toll_estimate_tool(request, routes)

    decisions = gantry_intelligence_tool(request, routes, tolls)

    assert any(decision.action == "exit_before_gantry" for decision in decisions)


def test_budget_status_identifies_preserved_and_exceeded_daily_budget():
    request = sample_request()

    preserved = budget_status_tool(request, projected_toll_spend=6.25)
    exceeded = budget_status_tool(request, projected_toll_spend=10.75)

    assert preserved.is_budget_preserved is True
    assert preserved.status == "budget_preserved"
    assert exceeded.is_budget_preserved is False
    assert exceeded.status == "budget_exceeded"
