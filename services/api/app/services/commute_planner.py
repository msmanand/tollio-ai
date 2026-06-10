from app.adapters.google_routes_adapter import NormalizedRouteOption, get_route_options
from app.models import (
    BudgetPeriod,
    CommutePlanRequest,
    CommutePlanResponse,
    GantryDecision,
    MapMarker,
    RouteCharge,
    RouteSegment,
)
from app.services.budget_engine import BudgetIntelligenceResult, evaluate_budget
from app.services.explanation_service import generate_explanation
from app.services.gantry_engine import RouteChargeSummary, optimize_route_value, score_gantry_decisions


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
    estimated_savings = round(
        natural_route.estimated_toll_cost - optimized_route.estimated_toll_cost,
        2,
    )
    budget_result = _evaluate_request_budget(
        request=request,
        planned_trip_toll_cost=optimized_route.estimated_toll_cost,
        savings_to_date=estimated_savings,
    )
    gantry_decisions = score_gantry_decisions(
        route_option=optimized_route,
        urgency_mode=request.urgency_mode,
        budget_period=request.budget_period,
        daily_budget=request.daily_budget,
        weekly_budget=request.weekly_budget,
        monthly_budget=request.monthly_budget,
        current_period_spend=request.current_period_spend,
        avoid_excessive_signals=request.avoid_excessive_signals,
    )
    route_value = optimize_route_value(
        route_option=optimized_route,
        urgency_mode=request.urgency_mode,
        budget_period=request.budget_period,
        daily_budget=request.daily_budget,
        weekly_budget=request.weekly_budget,
        monthly_budget=request.monthly_budget,
        current_period_spend=request.current_period_spend,
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
        estimated_savings=estimated_savings,
        added_minutes=max(optimized_route.total_minutes - natural_route.total_minutes, 0),
        budget_impact=_budget_impact_text(budget_result),
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
            "ntta_static_toll_tier_data" if route_value.ntta_data_used else "ntta_static_toll_tier_data_unmatched",
        ],
        map_route_polyline=optimized_route.polyline,
        natural_route_polyline=natural_route.polyline,
        optimized_route_polyline=optimized_route.polyline,
        route_segments=optimized_segments,
        map_markers=optimized_markers,
        budget_summary=budget_result.dashboard_summary,
        recommended_strategy=route_value.recommended_strategy,
        route_value_score=route_value.route_value_score,
        toll_minutes_used=route_value.toll_minutes_used,
        service_road_minutes=route_value.service_road_minutes,
        avoided_charges=_to_route_charges(route_value.avoided_charges),
        paid_charges=_to_route_charges(route_value.paid_charges),
        value_score_breakdown=route_value.value_score_breakdown,
        entry_value_score=route_value.entry_value_score,
        exit_value_score=route_value.exit_value_score,
        combined_value_score=route_value.combined_value_score,
        paid_but_unused_reason=route_value.paid_but_unused_reason,
        value_loss_reason=route_value.value_loss_reason,
        ntta_data_used=route_value.ntta_data_used,
        google_routes_data_used=route_value.google_routes_data_used,
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
    budget_result = _evaluate_request_budget(
        request=request,
        planned_trip_toll_cost=route.estimated_toll_cost,
        savings_to_date=0.0,
    )
    gantry_decisions = score_gantry_decisions(
        route_option=route,
        urgency_mode=request.urgency_mode,
        budget_period=request.budget_period,
        daily_budget=request.daily_budget,
        weekly_budget=request.weekly_budget,
        monthly_budget=request.monthly_budget,
        current_period_spend=request.current_period_spend,
        avoid_excessive_signals=request.avoid_excessive_signals,
    )
    route_value = optimize_route_value(
        route_option=route,
        urgency_mode=request.urgency_mode,
        budget_period=request.budget_period,
        daily_budget=request.daily_budget,
        weekly_budget=request.weekly_budget,
        monthly_budget=request.monthly_budget,
        current_period_spend=request.current_period_spend,
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
        budget_impact=_budget_impact_text(budget_result),
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
        budget_summary=budget_result.dashboard_summary,
        recommended_strategy=route_value.recommended_strategy,
        route_value_score=route_value.route_value_score,
        toll_minutes_used=route_value.toll_minutes_used,
        service_road_minutes=route_value.service_road_minutes,
        avoided_charges=_to_route_charges(route_value.avoided_charges),
        paid_charges=_to_route_charges(route_value.paid_charges),
        value_score_breakdown=route_value.value_score_breakdown,
        entry_value_score=route_value.entry_value_score,
        exit_value_score=route_value.exit_value_score,
        combined_value_score=route_value.combined_value_score,
        paid_but_unused_reason=route_value.paid_but_unused_reason,
        value_loss_reason=route_value.value_loss_reason,
        ntta_data_used=route_value.ntta_data_used,
        google_routes_data_used=route_value.google_routes_data_used,
    )
    explanation = generate_explanation(response)
    return response.model_copy(update={"explanation": explanation.detailed_explanation})


def _evaluate_request_budget(
    request: CommutePlanRequest,
    planned_trip_toll_cost: float,
    savings_to_date: float,
) -> BudgetIntelligenceResult:
    return evaluate_budget(
        budget_amount=_selected_budget_amount(request),
        budget_period=request.budget_period,
        current_period_spend=request.current_period_spend,
        commute_days_per_week=request.commute_days_per_week,
        trips_per_commute_day=request.trips_per_commute_day,
        include_weekends=request.include_weekends,
        remaining_days_in_period=request.remaining_days_in_period,
        planned_trip_toll_cost=planned_trip_toll_cost,
        urgency_mode=request.urgency_mode,
        savings_to_date=savings_to_date,
    )


def _selected_budget_amount(request: CommutePlanRequest) -> float:
    if request.budget_amount is not None:
        return request.budget_amount
    if request.budget_period == BudgetPeriod.daily:
        return request.daily_budget
    if request.budget_period == BudgetPeriod.weekly:
        return request.weekly_budget
    if request.budget_period == BudgetPeriod.monthly:
        return request.monthly_budget
    return request.monthly_budget * 12


def _budget_impact_text(budget_result: BudgetIntelligenceResult) -> str:
    return (
        f"Planned toll spend is ${budget_result.planned_trip_toll_cost:.2f}; "
        f"${budget_result.after_trip_remaining_budget:.2f} remains after this trip. "
        f"Recommended per-trip allowance is "
        f"${budget_result.recommended_per_trip_allowance:.2f}. "
        f"{budget_result.recommendation}"
    )


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


def _to_route_charges(charges: list[RouteChargeSummary]) -> list[RouteCharge]:
    return [
        RouteCharge(
            label=charge.label,
            amount=charge.amount,
            reason=charge.reason,
        )
        for charge in charges
    ]
