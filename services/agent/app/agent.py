import os
from typing import List

from app.models import AgentRequest, AgentResponse, RouteOption
from app.tools.budget_status_tool import budget_status_tool
from app.tools.gantry_intelligence_tool import gantry_intelligence_tool
from app.tools.mongodb_memory_tool import (
    get_budget_profile_tool,
    get_recent_commutes_tool,
    save_trip_decision_tool,
    update_savings_summary_tool,
)
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
    memory = _call_mongodb_memory_tools(request, saved_trip.saved_trip_id, optimized_cost)

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
        saved_trip_id=memory["saved_trip_id"],
        confidence_level="mock_contract",
        data_sources_used=_data_sources_used(memory["data_source"]),
        memory_trace=memory["trace"],
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


def _call_mongodb_memory_tools(request: AgentRequest, commute_plan_id: str, optimized_cost: float) -> dict:
    estimated_savings = round(max(request.daily_budget - optimized_cost, 0.0), 2)
    saved = save_trip_decision_tool(
        commute_plan_id=commute_plan_id,
        user_label=f"{request.origin} to {request.destination}",
        estimated_savings=estimated_savings,
    )
    budget_profile = get_budget_profile_tool()
    recent_commutes = get_recent_commutes_tool(limit=3)
    savings_summary = update_savings_summary_tool(additional_savings=estimated_savings)
    return {
        "saved_trip_id": str(saved["saved_trip_id"]),
        "data_source": str(saved["data_source"]),
        "trace": [
            f"save_trip_decision_tool:{saved['data_source']}",
            f"get_budget_profile_tool:{budget_profile['data_source']}",
            f"get_recent_commutes_tool:{recent_commutes['data_source']}",
            f"update_savings_summary_tool:{savings_summary['data_source']}",
        ],
    }


def _data_sources_used(memory_source: str) -> List[str]:
    mode = os.getenv("TOLLIO_AGENT_MODE", "mock").lower()
    has_gemini_credentials = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    sources = ["mock_tools", memory_source]
    if mode == "mock" or not has_gemini_credentials:
        return sources
    return sources + ["gemini_ready_not_called"]
