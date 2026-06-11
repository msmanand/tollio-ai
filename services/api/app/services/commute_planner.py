from app.adapters.google_routes_adapter import NormalizedRouteOption, get_route_options
from app.models import (
    BudgetPeriod,
    CommutePlanRequest,
    CommutePlanResponse,
    GantryDecision,
    MapMarker,
    RouteCharge,
    RouteSegment,
    TollioBrainOption,
    TollioBrainRecommendation,
)
from app.services.budget_engine import BudgetIntelligenceResult, evaluate_budget
from app.services.explanation_service import generate_explanation
from app.services.gantry_engine import RouteChargeSummary, optimize_route_value, score_gantry_decisions
from app.services.tollio_brain import (
    BrainProfile,
    OptimizationResult,
    projectAnnualSaving,
    optimize_trip_by_names,
)


def build_commute_plan(request: CommutePlanRequest) -> CommutePlanResponse:
    """Return deterministic contract data until routing providers are integrated."""
    brain_results = optimize_trip_by_names(
        request.origin,
        request.destination,
        _brain_profile(request),
    )
    if brain_results:
        return _brain_plan(request, brain_results)
    if _is_frisco_to_downtown_dallas(request):
        return _frisco_to_downtown_dallas_plan(request)

    return _generic_placeholder_plan(request)


def _brain_profile(request: CommutePlanRequest) -> BrainProfile:
    return BrainProfile(
        toll_payment="zipcash" if "zip" in request.toll_pass_type.lower() else "tolltag",
        mpg=request.vehicle_mpg,
        vehicle_type="ev" if request.vehicle_mpg >= 999 else "gas",
        gas_price=request.gas_price,
        traffic_mode=_traffic_mode(request.urgency_mode.value),
    )


def _traffic_mode(urgency_mode: str) -> str:
    if urgency_mode == "urgent":
        return "rush"
    if urgency_mode == "saver":
        return "offpeak"
    return "offpeak"


def _brain_plan(
    request: CommutePlanRequest,
    brain_results: list[OptimizationResult],
) -> CommutePlanResponse:
    best = brain_results[0]
    first_segment = best.segments[0]
    last_segment = best.segments[-1]
    budget_result = _evaluate_request_budget(
        request=request,
        planned_trip_toll_cost=best.total_price,
        savings_to_date=best.net_saving,
    )
    recommendation = _brain_recommendation(best)
    route_segments = _brain_route_segments(best)
    response = CommutePlanResponse(
        recommended_route_summary=(
            f"Enter at {recommendation.better_entry or recommendation.natural_entry} "
            f"and exit at {recommendation.better_exit or recommendation.natural_exit} "
            f"to save ${best.net_saving:.2f} net."
        ),
        natural_route_cost=best.natural_total,
        optimized_route_cost=best.total_price,
        estimated_savings=best.net_saving,
        added_minutes=best.total_svc_mins,
        budget_impact=_budget_impact_text(budget_result),
        gantry_decisions=[
            GantryDecision(
                gantry_name_or_segment=best.label,
                action="exit_before_gantry" if best.toll_saved > 0 else "stay_on_toll",
                toll_cost_avoided=best.toll_saved,
                added_minutes=best.total_svc_mins,
                budget_effect=_budget_impact_text(budget_result),
                value_score=best.avg_value_score / 100,
                reason=recommendation.why,
            )
        ],
        explanation=recommendation.why,
        confidence_level="official_ntta_rate_brain",
        data_sources_used=[
            "brain_md_optimizer",
            "official_ntta_2025_2027_toll_point_rates",
        ],
        map_route_polyline="brain_optimizer_no_map_polyline",
        natural_route_polyline="brain_optimizer_natural_route",
        optimized_route_polyline="brain_optimizer_optimized_route",
        route_segments=route_segments,
        map_markers=[
            MapMarker(
                marker_type="origin",
                label=first_segment.used_entry.exit_name,
                latitude=0.0,
                longitude=0.0,
                description="Natural or optimized entry selected by the Tollio brain.",
            ),
            MapMarker(
                marker_type="destination",
                label=last_segment.used_exit.exit_name,
                latitude=0.0,
                longitude=0.0,
                description="Natural or optimized exit selected by the Tollio brain.",
            ),
        ],
        budget_summary=budget_result.dashboard_summary,
        recommended_strategy=None,
        route_value_score=None,
        toll_minutes_used=sum(segment.toll_mins for segment in best.segments),
        service_road_minutes=best.total_svc_mins,
        avoided_charges=[
            RouteCharge(
                label="Toll saved",
                amount=best.toll_saved,
                reason=recommendation.why,
            )
        ] if best.toll_saved > 0 else [],
        paid_charges=[
            RouteCharge(
                label=segment.road_short,
                amount=segment.price,
                reason=f"Official NTTA rate-derived toll from {segment.used_entry.exit_name} to {segment.used_exit.exit_name}.",
            )
            for segment in best.segments
        ],
        value_score_breakdown=[],
        entry_value_score=first_segment.used_entry.score,
        exit_value_score=last_segment.used_exit.score,
        combined_value_score=best.avg_value_score,
        paid_but_unused_reason=_paid_unused_reason(best),
        value_loss_reason=recommendation.why,
        ntta_data_used=True,
        google_routes_data_used=False,
        brain_recommendation=recommendation,
        brain_options=_brain_options(brain_results[:3]),
    )
    return response


def _is_frisco_to_downtown_dallas(request: CommutePlanRequest) -> bool:
    return (
        request.origin.strip().lower() == "frisco"
        and request.destination.strip().lower() == "downtown dallas"
    )


def _brain_recommendation(result: OptimizationResult) -> TollioBrainRecommendation:
    first = result.segments[0]
    last = result.segments[-1]
    better_entry = None if first.used_entry.is_natural else first.used_entry.exit_name
    better_exit = None if last.used_exit.is_natural else last.used_exit.exit_name
    return TollioBrainRecommendation(
        natural_entry=first.entry_analysis.natural.exit_name,
        better_entry=better_entry,
        natural_exit=last.exit_analysis.natural.exit_name,
        better_exit=better_exit,
        toll_saved=result.toll_saved,
        gas_cost=result.gas_cost,
        net_saving=result.net_saving,
        extra_time_minutes=result.total_svc_mins,
        value_score=result.avg_value_score,
        why=_brain_why(result),
        annual_saving_projection=projectAnnualSaving(result.net_saving),
    )


def _brain_why(result: OptimizationResult) -> str:
    first = result.segments[0]
    last = result.segments[-1]
    reasons = []
    if not first.used_entry.is_natural:
        reasons.append(
            f"Entering at {first.used_entry.exit_name} instead of "
            f"{first.entry_analysis.natural.exit_name} avoids paying for part of a toll tier "
            "you would not fully use."
        )
    if not last.used_exit.is_natural:
        reasons.append(
            f"Exiting at {last.used_exit.exit_name} instead of "
            f"{last.exit_analysis.natural.exit_name} avoids an additional toll while adding "
            f"{last.used_exit.svc_mins} minutes on the service road."
        )
    if not reasons:
        reasons.append(
            "Remaining on the natural toll path is justified because the available NTTA rates do not show a closer cheaper tier."
        )
    reasons.append(
        f"That saves ${result.toll_saved:.2f} in tolls, costs ${result.gas_cost:.2f} in gas, "
        f"and keeps ${result.net_saving:.2f} net."
    )
    return " ".join(reasons)


def _paid_unused_reason(result: OptimizationResult) -> str:
    first = result.segments[0]
    last = result.segments[-1]
    return (
        f"Wasted behind: {first.used_entry.wasted} exit(s). "
        f"Unused ahead: {last.used_exit.unused} exit(s)."
    )


def _brain_options(results: list[OptimizationResult]) -> list[TollioBrainOption]:
    if not results:
        return []
    best = results[0]
    options = [
        TollioBrainOption(
            label="Natural Route",
            total_price=best.natural_total,
            natural_total=best.natural_total,
            toll_saved=0.0,
            gas_cost=0.0,
            net_saving=0.0,
            extra_time_minutes=0,
            value_score=_natural_value_score(best),
            is_best=False,
            why="Use the natural entry and natural exit without a service-road detour.",
        ),
        TollioBrainOption(
            label="Optimized Route",
            total_price=best.total_price,
            natural_total=best.natural_total,
            toll_saved=best.toll_saved,
            gas_cost=best.gas_cost,
            net_saving=best.net_saving,
            extra_time_minutes=best.total_svc_mins,
            value_score=best.avg_value_score,
            is_best=True,
            why=_brain_why(best),
        ),
    ]
    for result in results[1:2]:
        options.append(
            TollioBrainOption(
                label="Alternative Route",
                total_price=result.total_price,
                natural_total=result.natural_total,
                toll_saved=result.toll_saved,
                gas_cost=result.gas_cost,
                net_saving=result.net_saving,
                extra_time_minutes=result.total_svc_mins,
                value_score=result.avg_value_score,
                is_best=False,
                why=_brain_why(result),
            )
        )
    return options


def _natural_value_score(result: OptimizationResult) -> int:
    natural_scores = [
        min(segment.entry_analysis.natural.score, segment.exit_analysis.natural.score)
        for segment in result.segments
    ]
    return round(sum(natural_scores) / max(len(natural_scores), 1))


def _brain_route_segments(result: OptimizationResult) -> list[RouteSegment]:
    return [
        RouteSegment(
            segment_label=f"{segment.used_entry.exit_name} to {segment.used_exit.exit_name}",
            road_name=segment.road_name,
            start_location=segment.used_entry.exit_name,
            end_location=segment.used_exit.exit_name,
            segment_type="toll",
            estimated_minutes=segment.toll_mins,
            estimated_cost=segment.price,
            distance_miles=round(abs(segment.used_exit.exit_idx - segment.used_entry.exit_idx) * 0.9, 2),
            rate_confidence="mapped",
            rate_source="official_ntta_2025_2027_toll_point_rates",
        )
        for segment in result.segments
    ]


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
            tolltag_rate=segment.tolltag_rate,
            zipcash_rate=segment.zipcash_rate,
            rate_confidence=segment.rate_confidence,
            rate_source=segment.rate_source,
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
            tolltag_rate=charge.tolltag_rate,
            zipcash_rate=charge.zipcash_rate,
            confidence=charge.confidence,
            source=charge.source,
        )
        for charge in charges
    ]
