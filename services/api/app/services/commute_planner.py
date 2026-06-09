from app.models import (
    CommutePlanRequest,
    CommutePlanResponse,
    GantryAction,
    GantryDecision,
    MapMarker,
    MarkerType,
    RouteSegment,
    SegmentType,
)


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
    return CommutePlanResponse(
        recommended_route_summary=(
            "Use the high-value Dallas North Tollway segments from Frisco, "
            "exit before the low-value Legacy-area scanner, then reenter "
            "after the congestion pinch point toward Downtown Dallas."
        ),
        natural_route_cost=10.75,
        optimized_route_cost=6.25,
        estimated_savings=4.50,
        added_minutes=5,
        budget_impact=(
            f"Optimized toll spend is $6.25, leaving ${request.daily_budget - 6.25:.2f} "
            f"of the ${request.daily_budget:.2f} daily budget."
        ),
        gantry_decisions=[
            GantryDecision(
                gantry_name_or_segment="DNT Frisco Mainline Segment",
                action=GantryAction.stay_on_toll,
                toll_cost_avoided=0.0,
                added_minutes=0,
                budget_effect="Worth paying because it saves meaningful commute time.",
                value_score=0.91,
                reason="This segment avoids slow arterial traffic with strong minutes-per-dollar value.",
            ),
            GantryDecision(
                gantry_name_or_segment="Legacy Drive Low-Value Gantry",
                action=GantryAction.exit_before_gantry,
                toll_cost_avoided=3.10,
                added_minutes=3,
                budget_effect="Avoids an unnecessary scanner and keeps the trip under the daily budget.",
                value_score=0.28,
                reason="The toll is high relative to the small time savings for this segment.",
            ),
            GantryDecision(
                gantry_name_or_segment="North Dallas Reentry Segment",
                action=GantryAction.reenter_after_gantry,
                toll_cost_avoided=1.40,
                added_minutes=2,
                budget_effect="Preserves budget while still using the faster downtown approach.",
                value_score=0.72,
                reason="Reentering after the skipped scanner balances cost and arrival reliability.",
            ),
        ],
        explanation=(
            "The placeholder Gantry Intelligence Engine treats each gantry or segment "
            "as a separate value decision. It pays for the segments with strong time "
            "savings, skips one low-value scanner, and shows the budget impact before "
            "future Google Routes, Gemini, MCP, or MongoDB integrations are connected."
        ),
        confidence_level="contract_placeholder",
        data_sources_used=[
            "deterministic_placeholder_contract",
            "founder_defined_sample_scenario",
        ],
        map_route_polyline="placeholder_optimized_frisco_to_downtown_dallas",
        natural_route_polyline="placeholder_natural_dnt_full_toll_route",
        optimized_route_polyline="placeholder_exit_legacy_reenter_north_dallas",
        route_segments=[
            RouteSegment(
                segment_label="Segment A",
                road_name="Dallas North Tollway",
                start_location="Frisco",
                end_location="Legacy Drive",
                segment_type=SegmentType.toll,
                estimated_minutes=18,
                estimated_cost=4.25,
            ),
            RouteSegment(
                segment_label="Segment B",
                road_name="Legacy Drive Service Road",
                start_location="Legacy Drive Exit",
                end_location="North Dallas Reentry",
                segment_type=SegmentType.service_road,
                estimated_minutes=8,
                estimated_cost=0.0,
            ),
            RouteSegment(
                segment_label="Segment C",
                road_name="Dallas North Tollway",
                start_location="North Dallas Reentry",
                end_location="Downtown Dallas",
                segment_type=SegmentType.toll,
                estimated_minutes=20,
                estimated_cost=2.0,
            ),
        ],
        map_markers=[
            MapMarker(
                marker_type=MarkerType.origin,
                label="Frisco",
                latitude=33.1507,
                longitude=-96.8236,
                description="Placeholder origin for the sample commute.",
            ),
            MapMarker(
                marker_type=MarkerType.gantry,
                label="DNT Frisco Mainline",
                latitude=33.0931,
                longitude=-96.8211,
                description="High-value toll segment recommended to keep.",
            ),
            MapMarker(
                marker_type=MarkerType.exit,
                label="Exit before Legacy scanner",
                latitude=33.0735,
                longitude=-96.8218,
                description="Skip the low-value gantry with small time impact.",
            ),
            MapMarker(
                marker_type=MarkerType.reentry,
                label="Reenter North Dallas",
                latitude=32.9541,
                longitude=-96.8204,
                description="Rejoin toll route after the low-value scanner.",
            ),
            MapMarker(
                marker_type=MarkerType.destination,
                label="Downtown Dallas",
                latitude=32.7767,
                longitude=-96.7970,
                description="Placeholder destination for the sample commute.",
            ),
        ],
    )


def _generic_placeholder_plan(request: CommutePlanRequest) -> CommutePlanResponse:
    return CommutePlanResponse(
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
        gantry_decisions=[
            GantryDecision(
                gantry_name_or_segment="Placeholder segment",
                action=GantryAction.avoid_toll,
                toll_cost_avoided=0.0,
                added_minutes=0,
                budget_effect="No budget impact in placeholder mode.",
                value_score=0.0,
                reason="External route and toll data are intentionally not connected yet.",
            )
        ],
        explanation=(
            "This deterministic placeholder preserves the response shape for future "
            "Gemini, Google Routes API, MCP, and MongoDB integrations."
        ),
        confidence_level="contract_placeholder",
        data_sources_used=["deterministic_placeholder_contract"],
        map_route_polyline="placeholder_generic_route",
        natural_route_polyline="placeholder_generic_natural_route",
        optimized_route_polyline="placeholder_generic_optimized_route",
        route_segments=[
            RouteSegment(
                segment_label="Placeholder segment",
                road_name="Unknown",
                start_location=request.origin,
                end_location=request.destination,
                segment_type=SegmentType.local_road,
                estimated_minutes=0,
                estimated_cost=0.0,
            )
        ],
        map_markers=[
            MapMarker(
                marker_type=MarkerType.origin,
                label=request.origin,
                latitude=0.0,
                longitude=0.0,
                description="Placeholder origin marker.",
            ),
            MapMarker(
                marker_type=MarkerType.destination,
                label=request.destination,
                latitude=0.0,
                longitude=0.0,
                description="Placeholder destination marker.",
            ),
        ],
    )
