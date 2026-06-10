import json
from pathlib import Path

from app.adapters.google_routes_adapter import NormalizedMapMarker, NormalizedRouteOption, NormalizedRouteSegment
from app.models import BudgetPeriod, UrgencyMode
from app.services.gantry_engine import optimize_route_value


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "route_value_scenarios.json"


def _route(name: str) -> NormalizedRouteOption:
    scenario = json.loads(FIXTURE_PATH.read_text())[name]
    segments = [NormalizedRouteSegment(**segment) for segment in scenario["segments"]]
    return NormalizedRouteOption(
        route_id=scenario["route_id"],
        route_label=scenario["route_label"],
        total_minutes=sum(segment.estimated_minutes for segment in segments),
        total_distance_miles=sum(segment.distance_miles for segment in segments),
        estimated_toll_cost=sum(segment.estimated_cost for segment in segments),
        polyline=f"placeholder_{scenario['route_id']}",
        segments=segments,
        map_markers=[
            NormalizedMapMarker(
                marker_type="origin",
                label="origin",
                latitude=0.0,
                longitude=0.0,
                description="fixture origin",
            )
        ],
        data_source="fixture",
    )


def _optimize(name: str, urgency_mode: UrgencyMode, daily_budget=8.0, current_spend=0.0):
    return optimize_route_value(
        route_option=_route(name),
        urgency_mode=urgency_mode,
        budget_period=BudgetPeriod.daily,
        daily_budget=daily_budget,
        weekly_budget=40.0,
        monthly_budget=160.0,
        current_period_spend=current_spend,
        avoid_excessive_signals=True,
    )


def test_delayed_entry_can_beat_immediate_entry():
    result = _optimize("delayed_entry_better", UrgencyMode.balanced, daily_budget=12.0)
    full_toll = next(candidate for candidate in result.candidates if candidate.strategy == "full_toll_route")
    delayed = next(candidate for candidate in result.candidates if candidate.strategy == "delayed_toll_entry")

    assert delayed.final_value_score > full_toll.final_value_score
    assert result.recommended_strategy == "delayed_toll_entry"
    assert result.avoided_charges[0].label == "Low-value Entry Scanner"


def test_service_road_to_destination_can_beat_reentry():
    result = _optimize("service_road_destination", UrgencyMode.saver, daily_budget=6.0)
    reentry = next(candidate for candidate in result.candidates if candidate.strategy == "max_value_after_paid_gantry")
    service = next(candidate for candidate in result.candidates if candidate.strategy == "service_road_to_destination")

    assert service.final_value_score > reentry.final_value_score
    assert service.paid_charges == []


def test_bridge_or_connector_toll_can_be_avoided_when_low_value():
    result = _optimize("coit_121_to_lewisville", UrgencyMode.balanced, daily_budget=12.0)

    assert result.recommended_strategy == "avoid_connector_or_bridge_toll"
    assert any("Bridge Connector" in charge.label for charge in result.avoided_charges)
    assert result.toll_minutes_used > 0
    assert result.service_road_minutes > 0


def test_full_toll_wins_when_urgent_and_budget_allows():
    result = _optimize("urgent_full_toll", UrgencyMode.urgent, daily_budget=20.0)

    assert result.recommended_strategy == "full_toll_route"
    assert result.avoided_charges == []
    assert len(result.paid_charges) == 2


def test_budget_pressure_changes_recommendation():
    comfortable = _optimize("budget_pressure", UrgencyMode.balanced, daily_budget=20.0)
    pressured = _optimize(
        "budget_pressure",
        UrgencyMode.balanced,
        daily_budget=8.0,
        current_spend=8.0,
    )

    assert comfortable.recommended_strategy != pressured.recommended_strategy
    assert pressured.candidates[0].budget_pressure_score > comfortable.candidates[0].budget_pressure_score


def test_route_value_optimizer_output_is_deterministic():
    first = _optimize("coit_121_to_lewisville", UrgencyMode.balanced).model_dump()
    second = _optimize("coit_121_to_lewisville", UrgencyMode.balanced).model_dump()

    assert first == second
