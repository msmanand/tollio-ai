import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.models import AgentRequest
from app.tools.budget_status_tool import budget_status_tool
from app.tools.gantry_intelligence_tool import gantry_intelligence_tool
from app.tools.gemini_explanation_tool import gemini_explanation_tool
from app.tools.mongodb_memory_tool import (
    get_recent_commutes_tool,
    save_trip_decision_tool,
    update_savings_summary_tool,
)
from app.tools.route_options_tool import route_options_tool
from app.tools.toll_estimate_tool import toll_estimate_tool


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


def run_agent_runtime(request: Optional[AgentRequest] = None) -> Dict[str, Any]:
    active_request = request or sample_request()
    route_options = route_options_tool(active_request)
    toll_estimates = toll_estimate_tool(active_request, route_options)
    gantry_decisions = gantry_intelligence_tool(active_request, route_options, toll_estimates)
    optimized_cost = _optimized_toll_cost(toll_estimates[0].total_toll_cost, gantry_decisions)
    budget_status = budget_status_tool(active_request, optimized_cost)
    memory_trace = _memory_trace(active_request, optimized_cost)
    explanation = gemini_explanation_tool(
        {
            "origin": active_request.origin,
            "destination": active_request.destination,
            "optimized_cost": optimized_cost,
            "budget_status": budget_status.model_dump(mode="json"),
            "gantry_decisions": [decision.model_dump(mode="json") for decision in gantry_decisions],
        }
    )
    return {
        "runtime": "Agent Builder / ADK-compatible Tollio runtime",
        "entry_point": "python -m app.tollio_agent_runtime",
        "intent": "budget_aware_commute_plan",
        "route_toll_optimization": {
            "route_options_tool_called": True,
            "toll_estimate_tool_called": True,
            "gantry_intelligence_tool_called": True,
            "route_options_count": len(route_options),
            "optimized_toll_cost": optimized_cost,
        },
        "budget": budget_status.model_dump(mode="json"),
        "memory_trace": memory_trace,
        "gemini_explanation": explanation,
    }


def _memory_trace(request: AgentRequest, optimized_cost: float) -> list[dict]:
    mcp_config = Path(__file__).resolve().parents[1] / "mcp.mongodb.json"
    estimated_savings = round(max(request.daily_budget - optimized_cost, 0.0), 2)
    calls = [
        (
            "save_trip_decision_tool",
            "save_trip_decision",
            {
                "commute_plan_id": f"{request.origin}-{request.destination}",
                "user_label": f"{request.origin} to {request.destination}",
                "estimated_savings": estimated_savings,
            },
            lambda tool_input: save_trip_decision_tool(**tool_input),
        ),
        (
            "get_recent_commutes_tool",
            "get_recent_commutes",
            {"limit": 3},
            lambda tool_input: get_recent_commutes_tool(**tool_input),
        ),
        (
            "update_savings_summary_tool",
            "update_savings_summary",
            {"additional_savings": estimated_savings},
            lambda tool_input: update_savings_summary_tool(**tool_input),
        ),
    ]
    trace = []
    for tool_name, action, tool_input, caller in calls:
        trace.append(
            {
                "tool_name": tool_name,
                "action": action,
                "input": tool_input,
                "output": caller(tool_input),
                "mcp_config_present": mcp_config.exists(),
            }
        )
    return trace


def _optimized_toll_cost(natural_cost: float, gantry_decisions) -> float:
    avoided = sum(decision.toll_cost_avoided for decision in gantry_decisions)
    return round(max(natural_cost - avoided, 0.0), 2)


if __name__ == "__main__":
    print(json.dumps(run_agent_runtime(), indent=2))
