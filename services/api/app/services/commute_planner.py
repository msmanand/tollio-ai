from app.adapters.google_routes_adapter import NormalizedRouteOption, get_route_options
from app.models import (
    CommutePlanRequest,
    CommutePlanResponse,
    GantryDecision,
    MapMarker,
    RouteSegment,
)
from app.services.explanation_service import generate_explanation
from app.services.gantry_engine import score_gantry_decisions


def build_commute_plan(request: CommutePlanRequest) -> CommutePlanResponse:
    """Return deterministic contract data until routing providers are integrated."""
    if _is_frisco_to_downtown_dallas(request):
        return _frisco_to_downtown_dallas_plan(request)

    return _generic_placeholder_plan(request)


def _is_frisco_to_downtown_dallas(request: CommutePlanRequest) -> bool:
    return (
        request.origin.strip().lower() == "frisco"
        and request.destination.strip().lower() == "downtown dallas"
    )


def _frisco_to_downtown_dallas_plan(
    request: CommutePlanRequest,
) -> CommutePlanResponse:
    route_options = get_route_options(
        request.origin,
        request.destination,
        request.arrival_time,
        request.urgency_mode.value,
    )
    natural_route = _find_route(route_options, "natural_full_toll")
    optimized_route = _find_route(route_options, "optimized_gantry_plan")
    optimized_segments = _to_route_segments(optimized_route)
    optimized_markers = _to_map_markers(optimized_route)
    gantry_decisions = score_gantry_decisions(
        route_option=optimized_route,
        urgency_mode=request.urgency_mode,
        budget_period=request.budget_period,
        daily_budget=request.daily_budget,
        weekly_budget=request.weekly_budget,
        monthly_budget=request.monthly_budget,
        avoid_excessive_signals=request.avoid_excessive_signals,
    )

    response = CommutePlanResponse(
        recommended_route_summary=(
            "Use the high-value Dallas North Tollway segments from Frisco, "
            "exit before the low-value Legacy-area scanner, then reenter "
            "after the congestion pinch point toward Downtown Dallas."
        ),
        natural_route_cost=natural_route.estimated_toll_cost,
        optimized_route_cost=optimized_route.estimated_toll_cost,
        estimated_savings=round(natural_route.estimated_toll_cost - optimized_route.estimated_toll_cost, 2),
        added_minutes=max(optimized_route.total_minutes - natural_route.total_minutes, 0),
        budget_impact=(
            f"Optimized toll spend is ${optimized_route.estimated_toll_cost:.2f}, leaving ${request.daily_budget - optimized_route.estimated_toll_cost:.2f} "
            f"of the ${request.daily_budget:.2f} daily budget."
        ),
        gantry_decisions=gantry_decisions,
        explanation=(
            "The deterministic Gantry Intelligence Engine scores each gantry or segment "
            "as a separate value decision. It compares toll avoided, added minutes, "
            "signal penalty, budget remaining, and urgency mode before future Gemini, "
            "MCP, MongoDB, or live toll integrations are connected."
        ),
        confidence_level="contract_placeholder",
        data_sources_used=[
            "deterministic_placeholder_contract",
            "founder_defined_sample_scenario",
            optimized_route.data_source,
        ],
        map_route_polyline=optimized_route.polyline,
        natural_route_polyline=natural_route.polyline,
        optimized_route_polyline=optimized_route.polyline,
        route_segments=optimized_segments,
        map_markers=optimized_markers,
    )
    explanation = generate_explanation(response)
    return response.model_copy(update={"explanation": explanation.detailed_explanation})


def _generic_placeholder_plan(request: CommutePlanRequest) -> CommutePlanResponse:
    route_options = get_route_options(
        request.origin,
        request.destination,
        request.arrival_time,
        request.urgency_mode.value,
    )
    route = route_options[0]
    gantry_decisions = score_gantry_decisions(
        route_option=route,
        urgency_mode=request.urgency_mode,
        budget_period=request.budget_period,
        daily_budget=request.daily_budget,
        weekly_budget=request.weekly_budget,
        monthly_budget=request.monthly_budget,
        avoid_excessive_signals=request.avoid_excessive_signals,
    )

    response = CommutePlanResponse(
        recommended_route_summary=(
            "Placeholder contract response. Gantry-level optimization will be "
            "computed after route provider integration."
        ),
        natural_route_cost=0.0,
        optimized_route_cost=0.0,
        estimated_savings=0.0,
        added_minutes=0,
        budget_impact=(
            f"No toll impact estimated yet for the {request.budget_period.value} budget."
        ),
        gantry_decisions=gantry_decisions,
        explanation=(
            "This deterministic placeholder preserves the response shape for future "
            "Gemini, Google Routes API, MCP, and MongoDB integrations."
        ),
        confidence_level="contract_placeholder",
        data_sources_used=["deterministic_placeholder_contract"],
        map_route_polyline=route.polyline,
        natural_route_polyline=route.polyline,
        optimized_route_polyline=route.polyline,
        route_segments=_to_route_segments(route),
        map_markers=_to_map_markers(route),
    )
    explanation = generate_explanation(response)
    return response.model_copy(update={"explanation": explanation.detailed_explanation})


def _find_route(
    route_options: list[NormalizedRouteOption],
    route_id: str,
) -> NormalizedRouteOption:
    for route in route_options:
        if route.route_id == route_id:
            return route
    return route_options[0]


def _to_route_segments(route: NormalizedRouteOption) -> list[RouteSegment]:
    return [
        RouteSegment(
            segment_label=segment.segment_label,
            road_name=segment.road_name,
            start_location=segment.start_location,
            end_location=segment.end_location,
            segment_type=segment.segment_type,
            estimated_minutes=segment.estimated_minutes,
            estimated_cost=segment.estimated_cost,
            distance_miles=segment.distance_miles,
        )
        for segment in route.segments
    ]


def _to_map_markers(route: NormalizedRouteOption) -> list[MapMarker]:
    return [
        MapMarker(
            marker_type=marker.marker_type,
            label=marker.label,
            latitude=marker.latitude,
            longitude=marker.longitude,
            description=marker.description,
        )
        for marker in route.map_markers
    ]
