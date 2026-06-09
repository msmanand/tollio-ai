import os
from typing import List

from app.models import AgentRequest, AgentResponse, RouteOption
from app.tools.budget_status_tool import budget_status_tool
from app.tools.gantry_intelligence_tool import gantry_intelligence_tool
from app.tools.route_options_tool import route_options_tool
from app.tools.save_trip_tool import save_trip_tool
from app.tools.toll_estimate_tool import toll_estimate_tool


AGENT_NAME = "tollio_commute_agent"


def tollio_commute_agent(request: AgentRequest) -> AgentResponse:
    route_options = route_options_tool(request)
    toll_estimates = toll_estimate_tool(request, route_options)
    gantry_decisions = gantry_intelligence_tool(request, route_options, toll_estimates)
    optimized_cost = _optimized_toll_cost(toll_estimates[0].total_toll_cost, gantry_decisions)
    budget_status = budget_status_tool(request, optimized_cost)
    chosen_route = _choose_route(route_options)
    saved_trip = save_trip_tool(request, chosen_route, gantry_decisions)

    return AgentResponse(
        intent="budget_aware_commute_plan",
        chosen_route=chosen_route,
        route_options_considered=route_options,
        gantry_decisions=gantry_decisions,
        budget_status=budget_status,
        user_explanation=_build_user_explanation(request, optimized_cost, budget_status.is_budget_preserved),
        next_actions=[
            "Review skipped gantry before departure.",
            "Use the optimized toll plan if arrival reliability matters.",
            "Save this commute pattern for future budget comparisons.",
        ],
        saved_trip_id=saved_trip.saved_trip_id,
        confidence_level="mock_contract",
        data_sources_used=_data_sources_used(),
    )


def _choose_route(route_options: List[RouteOption]) -> RouteOption:
    for option in route_options:
        if option.route_id == "optimized_gantry_plan":
            return option
    return route_options[0]


def _optimized_toll_cost(natural_cost: float, gantry_decisions) -> float:
    avoided = sum(decision.toll_cost_avoided for decision in gantry_decisions)
    return round(max(natural_cost - avoided, 0.0), 2)


def _build_user_explanation(
    request: AgentRequest, optimized_cost: float, is_budget_preserved: bool
) -> str:
    budget_phrase = "keeps you under" if is_budget_preserved else "exceeds"
    return (
        f"Tollio mock mode recommends selective toll use from {request.origin} to "
        f"{request.destination}. The plan pays for high-value toll segments, skips "
        f"one low-value gantry, and projects ${optimized_cost:.2f} in tolls, which "
        f"{budget_phrase} your {request.budget_period.value} toll budget."
    )


def _data_sources_used() -> List[str]:
    mode = os.getenv("TOLLIO_AGENT_MODE", "mock").lower()
    has_gemini_credentials = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    if mode == "mock" or not has_gemini_credentials:
        return ["mock_tools"]
    return ["mock_tools", "gemini_ready_not_called"]
