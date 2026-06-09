from typing import List

from app.models import AgentRequest, RouteOption


def route_options_tool(request: AgentRequest) -> List[RouteOption]:
    """Return Google Routes-compatible placeholder route options."""
    if request.origin.lower() == "frisco" and request.destination.lower() == "downtown dallas":
        return [
            RouteOption(
                route_id="natural_full_toll",
                summary="Full Dallas North Tollway route with all gantries paid.",
                estimated_minutes=41,
                estimated_toll_cost=10.75,
                map_polyline="placeholder_natural_dnt_full_toll_route",
            ),
            RouteOption(
                route_id="optimized_gantry_plan",
                summary="Use high-value toll segments, exit before a low-value gantry, then reenter.",
                estimated_minutes=46,
                estimated_toll_cost=6.25,
                map_polyline="placeholder_exit_legacy_reenter_north_dallas",
            ),
        ]

    return [
        RouteOption(
            route_id="placeholder_route",
            summary="Placeholder route option pending Google Routes integration.",
            estimated_minutes=0,
            estimated_toll_cost=0.0,
            map_polyline="placeholder_generic_route",
        )
    ]
