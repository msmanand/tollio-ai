from app.adapters.google_routes_adapter import (
    NormalizedMapMarker,
    NormalizedRouteOption,
    NormalizedRouteSegment,
)
from app.models import BudgetPeriod, GantryAction, UrgencyMode
from app.services.gantry_engine import score_gantry_decisions


def _route(
    segments,
    estimated_toll_cost=None,
):
    total_cost = (
        estimated_toll_cost
        if estimated_toll_cost is not None
        else sum(segment.estimated_cost for segment in segments)
    )
    return NormalizedRouteOption(
        route_id="test_route",
        route_label="Test Route",
        total_minutes=sum(segment.estimated_minutes for segment in segments),
        total_distance_miles=sum(segment.distance_miles for segment in segments),
        estimated_toll_cost=total_cost,
        polyline="placeholder_test_polyline",
        segments=segments,
        map_markers=[
            NormalizedMapMarker(
                marker_type="origin",
                label="A",
                latitude=0.0,
                longitude=0.0,
                description="test",
            )
        ],
        data_source="test",
    )


def _segment(
    label="Low-value toll",
    cost=4.5,
    minutes=7,
    distance=5.8,
):
    return NormalizedRouteSegment(
        segment_label=label,
        road_name="Test Tollway",
        start_location="A",
        end_location="B",
        segment_type="toll",
        estimated_minutes=minutes,
        estimated_cost=cost,
        distance_miles=distance,
    )


def _decisions(
    route,
    urgency_mode,
    daily_budget=8.0,
    current_period_spend=0.0,
):
    return score_gantry_decisions(
        route_option=route,
        urgency_mode=urgency_mode,
        budget_period=BudgetPeriod.daily,
        daily_budget=daily_budget,
        weekly_budget=40.0,
        monthly_budget=160.0,
        current_period_spend=current_period_spend,
        avoid_excessive_signals=True,
    )


def test_saver_mode_returns_exit_before_gantry_for_low_value_segment():
    decisions = _decisions(_route([_segment()]), UrgencyMode.saver)

    assert decisions[0].action == GantryAction.exit_before_gantry


def test_balanced_mode_may_stay_on_toll_when_value_score_is_high():
    high_value_route = _route([_segment(label="High-value toll", cost=1.0, minutes=14, distance=12.0)])

    decisions = _decisions(high_value_route, UrgencyMode.balanced, daily_budget=20.0)

    assert decisions[0].action == GantryAction.stay_on_toll
    assert decisions[0].value_score == _decisions(high_value_route, UrgencyMode.balanced, daily_budget=20.0)[0].value_score


def test_urgent_mode_prioritizes_time_and_warns_about_budget_overage():
    route = _route(
        [
            _segment(label="First gantry", cost=10.0, minutes=5, distance=12.0),
            _segment(label="Second gantry", cost=10.0, minutes=5, distance=12.0),
        ],
        estimated_toll_cost=20.0,
    )

    decisions = _decisions(
        route,
        UrgencyMode.urgent,
        daily_budget=4.0,
        current_period_spend=4.0,
    )

    assert all("over the selected budget" in decision.budget_effect for decision in decisions)
    assert all(decision.added_minutes <= 10 for decision in decisions)


def test_value_score_is_deterministic():
    route = _route([_segment()])

    first = _decisions(route, UrgencyMode.saver)[0].value_score
    second = _decisions(route, UrgencyMode.saver)[0].value_score

    assert first == second


def test_saver_mode_can_recommend_exiting_two_or_more_exits_before_gantry():
    route = _route([_segment(label="Long low-value gantry", cost=8.0, minutes=6, distance=7.0)])

    decisions = _decisions(route, UrgencyMode.saver)

    assert decisions[0].action == GantryAction.exit_before_gantry
    assert decisions[0].added_minutes > 5
    assert "multi-exit detour" in decisions[0].reason


def test_over_budget_user_gets_more_aggressive_toll_avoidance():
    route = _route([_segment(label="Budget pressure gantry", cost=8.0, minutes=6, distance=7.0)])

    comfortable = _decisions(route, UrgencyMode.balanced, daily_budget=30.0)[0]
    over_budget = _decisions(
        route,
        UrgencyMode.balanced,
        daily_budget=4.0,
        current_period_spend=4.0,
    )[0]

    assert over_budget.toll_cost_avoided > comfortable.toll_cost_avoided
    assert over_budget.added_minutes >= comfortable.added_minutes


def test_balanced_mode_avoids_multi_exit_detour_if_savings_are_too_small():
    route = _route([_segment(label="Small savings gantry", cost=1.5, minutes=8, distance=7.0)])

    decisions = _decisions(route, UrgencyMode.balanced, daily_budget=30.0)

    assert decisions[0].added_minutes <= 5
    assert "multi-exit detour" not in decisions[0].reason


def test_urgent_mode_avoids_multi_exit_detour_unless_budget_is_exceeded():
    route = _route([_segment(label="Urgent gantry", cost=8.0, minutes=6, distance=7.0)])

    within_budget = _decisions(route, UrgencyMode.urgent, daily_budget=30.0)[0]
    over_budget = _decisions(
        route,
        UrgencyMode.urgent,
        daily_budget=4.0,
        current_period_spend=4.0,
    )[0]

    assert within_budget.added_minutes <= 2
    assert over_budget.added_minutes > 2
