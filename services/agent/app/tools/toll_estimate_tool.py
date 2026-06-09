from typing import List

from app.models import AgentRequest, RouteOption, TollEstimate


def toll_estimate_tool(
    request: AgentRequest, route_options: List[RouteOption]
) -> List[TollEstimate]:
    """Return tollInfo-compatible placeholder cost estimates."""
    return [
        TollEstimate(
            route_id=route.route_id,
            total_toll_cost=route.estimated_toll_cost,
            toll_pass_type=request.toll_pass_type,
            source="mock_toll_estimate_tool",
        )
        for route in route_options
    ]
