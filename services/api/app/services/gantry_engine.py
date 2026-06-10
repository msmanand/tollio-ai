from dataclasses import dataclass
from typing import List

from app.adapters.google_routes_adapter import NormalizedRouteOption, NormalizedRouteSegment
from app.models import BudgetPeriod, GantryAction, GantryDecision, UrgencyMode


@dataclass(frozen=True)
class GantryCandidate:
    action: GantryAction
    toll_cost_avoided: float
    added_minutes: int
    signal_penalty: int
    strategy_label: str
    estimated_minutes_saved: int
    cost_per_minute_saved: float


MODE_THRESHOLDS = {
    UrgencyMode.saver: 10,
    UrgencyMode.balanced: 5,
    UrgencyMode.urgent: 2,
}


def score_gantry_decisions(
    route_option: NormalizedRouteOption,
    urgency_mode: UrgencyMode,
    budget_period: BudgetPeriod,
    daily_budget: float,
    weekly_budget: float,
    monthly_budget: float,
    current_period_spend: float = 0.0,
    avoid_excessive_signals: bool = True,
) -> List[GantryDecision]:
    budget_limit = _budget_limit(
        budget_period,
        daily_budget=daily_budget,
        weekly_budget=weekly_budget,
        monthly_budget=monthly_budget,
    )
    remaining_budget = budget_limit - current_period_spend
    route_cost = route_option.estimated_toll_cost
    budget_pressure = _budget_pressure(remaining_budget, route_cost, budget_limit)
    decisions = []

    for index, segment in enumerate(route_option.segments):
        if segment.segment_type == "toll" and segment.estimated_cost > 0:
            candidate = _choose_toll_segment_candidate(
                segment=segment,
                segment_index=index,
                urgency_mode=urgency_mode,
                budget_pressure=budget_pressure,
                avoid_excessive_signals=avoid_excessive_signals,
            )
            decisions.append(
                _to_decision(
                    segment=segment,
                    candidate=candidate,
                    value_score=_value_score(segment, candidate, urgency_mode, budget_pressure),
                    budget_effect=_budget_effect(
                        candidate,
                        remaining_budget=remaining_budget,
                        route_cost=route_cost,
                    ),
                    urgency_mode=urgency_mode,
                    budget_pressure=budget_pressure,
                )
            )
        elif segment.segment_type == "service_road":
            decisions.append(_service_road_decision(segment, urgency_mode))

    if not decisions:
        decisions.append(
            GantryDecision(
                gantry_name_or_segment=route_option.route_label,
                action=GantryAction.avoid_toll,
                toll_cost_avoided=0.0,
                added_minutes=0,
                budget_effect="No toll gantries found in this route option.",
                value_score=0.0,
                reason="Route adapter data has no toll segment to score.",
            )
        )

    return decisions


def _choose_toll_segment_candidate(
    segment: NormalizedRouteSegment,
    segment_index: int,
    urgency_mode: UrgencyMode,
    budget_pressure: str,
    avoid_excessive_signals: bool,
) -> GantryCandidate:
    candidates = _candidate_strategies(segment, segment_index, avoid_excessive_signals)
    threshold = MODE_THRESHOLDS[urgency_mode]
    if budget_pressure == "over_budget":
        threshold = MODE_THRESHOLDS[UrgencyMode.saver]

    eligible = [candidate for candidate in candidates if candidate.added_minutes <= threshold]
    if not eligible:
        return candidates[0]

    scored = [
        (
            _candidate_score(
                segment=segment,
                candidate=candidate,
                urgency_mode=urgency_mode,
                budget_pressure=budget_pressure,
            ),
            candidate,
        )
        for candidate in eligible
    ]
    return max(scored, key=lambda item: item[0])[1]


def _candidate_strategies(
    segment: NormalizedRouteSegment,
    segment_index: int,
    avoid_excessive_signals: bool,
) -> List[GantryCandidate]:
    distance_factor = max(segment.distance_miles, 1.0)
    one_exit_added = max(1, min(5, round(distance_factor / 2)))
    multi_exit_added = max(one_exit_added + 2, min(10, round(distance_factor + 2)))
    reentry_added = max(1, min(4, round(distance_factor / 3)))
    service_road_added = max(multi_exit_added, min(10, round(distance_factor + 1)))
    full_avoid_added = max(service_road_added, min(12, round(distance_factor + 4)))
    signal_penalty = 2 if avoid_excessive_signals else 0
    minutes_saved_by_staying = max(segment.estimated_minutes - 1, 1)
    cost_per_minute_saved = round(segment.estimated_cost / minutes_saved_by_staying, 2)

    return [
        GantryCandidate(
            action=GantryAction.stay_on_toll,
            toll_cost_avoided=0.0,
            added_minutes=0,
            signal_penalty=0,
            strategy_label="stay on toll through the gantry",
            estimated_minutes_saved=minutes_saved_by_staying,
            cost_per_minute_saved=cost_per_minute_saved,
        ),
        GantryCandidate(
            action=GantryAction.exit_before_gantry,
            toll_cost_avoided=round(segment.estimated_cost * 0.7, 2),
            added_minutes=one_exit_added,
            signal_penalty=signal_penalty,
            strategy_label="exit one exit before the gantry",
            estimated_minutes_saved=max(segment.estimated_minutes - one_exit_added, 0),
            cost_per_minute_saved=cost_per_minute_saved,
        ),
        GantryCandidate(
            action=GantryAction.exit_before_gantry,
            toll_cost_avoided=round(segment.estimated_cost, 2),
            added_minutes=multi_exit_added,
            signal_penalty=signal_penalty + 1,
            strategy_label="exit_two_or_more_exits_before_gantry",
            estimated_minutes_saved=max(segment.estimated_minutes - multi_exit_added, 0),
            cost_per_minute_saved=cost_per_minute_saved,
        ),
        GantryCandidate(
            action=GantryAction.reenter_after_gantry,
            toll_cost_avoided=round(segment.estimated_cost * 0.55, 2),
            added_minutes=reentry_added,
            signal_penalty=signal_penalty,
            strategy_label="reenter after the next practical ramp",
            estimated_minutes_saved=max(segment.estimated_minutes - reentry_added, 0),
            cost_per_minute_saved=cost_per_minute_saved,
        ),
        GantryCandidate(
            action=GantryAction.reenter_after_gantry,
            toll_cost_avoided=round(segment.estimated_cost, 2),
            added_minutes=service_road_added,
            signal_penalty=signal_penalty + 2,
            strategy_label="stay_on_service_road_longer",
            estimated_minutes_saved=max(segment.estimated_minutes - service_road_added, 0),
            cost_per_minute_saved=cost_per_minute_saved,
        ),
        GantryCandidate(
            action=GantryAction.avoid_toll,
            toll_cost_avoided=round(segment.estimated_cost, 2),
            added_minutes=full_avoid_added,
            signal_penalty=signal_penalty + segment_index + 1,
            strategy_label="avoid the entire toll segment",
            estimated_minutes_saved=0,
            cost_per_minute_saved=cost_per_minute_saved,
        ),
    ]


def _candidate_score(
    segment: NormalizedRouteSegment,
    candidate: GantryCandidate,
    urgency_mode: UrgencyMode,
    budget_pressure: str,
) -> float:
    savings_weight = {
        UrgencyMode.saver: 1.35,
        UrgencyMode.balanced: 1.0,
        UrgencyMode.urgent: 0.55,
    }[urgency_mode]
    time_weight = {
        UrgencyMode.saver: 0.22,
        UrgencyMode.balanced: 0.38,
        UrgencyMode.urgent: 0.9,
    }[urgency_mode]
    if budget_pressure == "over_budget":
        savings_weight += 1.1
        time_weight *= 0.65
    elif budget_pressure == "close_to_budget":
        savings_weight += 0.45

    low_value_penalty = max(candidate.cost_per_minute_saved - 1.0, 0) * 0.55
    high_value_stay_bonus = max(1.25 - candidate.cost_per_minute_saved, 0) * 1.4
    toll_value = candidate.toll_cost_avoided * savings_weight
    time_cost = candidate.added_minutes * time_weight
    signal_cost = candidate.signal_penalty * _signal_weight(urgency_mode)
    stay_bonus = _stay_on_toll_bonus(
        segment,
        urgency_mode,
        budget_pressure,
        candidate,
        high_value_stay_bonus,
    )
    if candidate.action == GantryAction.stay_on_toll:
        return round(stay_bonus - low_value_penalty, 4)
    return round(toll_value - time_cost - signal_cost + low_value_penalty, 4)


def _stay_on_toll_bonus(
    segment: NormalizedRouteSegment,
    urgency_mode: UrgencyMode,
    budget_pressure: str,
    candidate: GantryCandidate,
    high_value_stay_bonus: float,
) -> float:
    if candidate.action != GantryAction.stay_on_toll:
        return 0.0
    if budget_pressure == "over_budget":
        return -1.5
    base = segment.estimated_minutes / max(segment.estimated_cost, 0.01)
    if urgency_mode == UrgencyMode.urgent:
        return min(base * 0.8, 2.8) + high_value_stay_bonus
    if urgency_mode == UrgencyMode.balanced:
        return min(base * 0.55, 2.0) + high_value_stay_bonus
    return min(base * 0.22, 0.8) + high_value_stay_bonus * 0.35


def _value_score(
    segment: NormalizedRouteSegment,
    candidate: GantryCandidate,
    urgency_mode: UrgencyMode,
    budget_pressure: str,
) -> float:
    raw_score = _candidate_score(segment, candidate, urgency_mode, budget_pressure)
    normalized = (raw_score + 4.0) / 8.0
    return round(max(0.0, min(normalized, 1.0)), 2)


def _budget_effect(
    candidate: GantryCandidate,
    remaining_budget: float,
    route_cost: float,
) -> str:
    projected_cost = route_cost - candidate.toll_cost_avoided
    projected_remaining = remaining_budget - projected_cost
    if projected_remaining < 0:
        return (
            f"Projected route toll spend remains ${abs(projected_remaining):.2f} over the selected budget."
        )
    return (
        f"Projected route toll spend preserves ${projected_remaining:.2f} of the selected budget."
    )


def _to_decision(
    segment: NormalizedRouteSegment,
    candidate: GantryCandidate,
    value_score: float,
    budget_effect: str,
    urgency_mode: UrgencyMode,
    budget_pressure: str,
) -> GantryDecision:
    return GantryDecision(
        gantry_name_or_segment=segment.segment_label,
        action=candidate.action,
        toll_cost_avoided=candidate.toll_cost_avoided,
        added_minutes=candidate.added_minutes,
        budget_effect=budget_effect,
        value_score=value_score,
        reason=_reason(segment, candidate, urgency_mode, budget_pressure),
    )


def _reason(
    segment: NormalizedRouteSegment,
    candidate: GantryCandidate,
    urgency_mode: UrgencyMode,
    budget_pressure: str,
) -> str:
    if budget_pressure == "over_budget" and "exit_two_or_more" in candidate.strategy_label:
        return "Exit two exits earlier because you are over today's toll budget."
    if budget_pressure == "over_budget" and candidate.action == GantryAction.avoid_toll:
        return "Avoid this toll segment because the selected toll budget is already exceeded."
    if (
        segment.estimated_minutes <= 2
        and candidate.estimated_minutes_saved <= 1
        and candidate.action != GantryAction.stay_on_toll
    ):
        return (
            f"Skip this gantry because it saves only {max(candidate.estimated_minutes_saved, 1)} "
            f"minute but costs ${segment.estimated_cost:.2f}."
        )
    if candidate.action == GantryAction.stay_on_toll:
        if budget_pressure == "over_budget":
            return "Urgent mode keeps this toll segment despite budget overage because the detour costs too much time."
        return (
            f"Stay on toll because this segment saves about {candidate.estimated_minutes_saved} "
            f"minutes at ${candidate.cost_per_minute_saved:.2f} per minute saved."
        )
    if "exit_two_or_more" in candidate.strategy_label:
        return (
            f"Exit two or more exits earlier because it avoids ${candidate.toll_cost_avoided:.2f} "
            f"and adds only {candidate.added_minutes} minutes."
        )
    if "stay_on_service_road_longer" in candidate.strategy_label:
        return (
            f"Stay on the service road longer because the toll savings of "
            f"${candidate.toll_cost_avoided:.2f} are worth the added time."
        )
    if candidate.action == GantryAction.reenter_after_gantry:
        return (
            f"Re-enter after the gantry to avoid ${candidate.toll_cost_avoided:.2f} "
            f"without giving up the rest of the toll-road time savings."
        )
    if candidate.action == GantryAction.avoid_toll:
        return "Budget pressure is high enough to avoid the entire toll segment."
    return (
        f"Exit one exit before the gantry to avoid ${candidate.toll_cost_avoided:.2f} "
        f"with {candidate.added_minutes} added minutes."
    )


def _signal_weight(urgency_mode: UrgencyMode) -> float:
    if urgency_mode == UrgencyMode.saver:
        return 0.18
    if urgency_mode == UrgencyMode.balanced:
        return 0.45
    return 0.8


def _service_road_decision(
    segment: NormalizedRouteSegment,
    urgency_mode: UrgencyMode,
) -> GantryDecision:
    acceptable_service_road_minutes = MODE_THRESHOLDS[urgency_mode]
    if urgency_mode in {UrgencyMode.saver, UrgencyMode.balanced}:
        acceptable_service_road_minutes = max(acceptable_service_road_minutes, 10)
    action = (
        GantryAction.exit_before_gantry
        if segment.estimated_minutes <= acceptable_service_road_minutes
        else GantryAction.stay_on_toll
    )
    return GantryDecision(
        gantry_name_or_segment=segment.segment_label,
        action=action,
        toll_cost_avoided=0.0,
        added_minutes=segment.estimated_minutes,
        budget_effect="Service-road segment has no direct toll charge.",
        value_score=0.62 if action == GantryAction.exit_before_gantry else 0.75,
        reason=(
            "Exit before this gantry and stay on the service road longer because the time impact is acceptable."
            if action == GantryAction.exit_before_gantry
            else "Service-road alternative adds too much time, so staying on toll is preferred."
        ),
    )


def _budget_limit(
    budget_period: BudgetPeriod,
    daily_budget: float,
    weekly_budget: float,
    monthly_budget: float,
) -> float:
    if budget_period == BudgetPeriod.daily:
        return daily_budget
    if budget_period == BudgetPeriod.weekly:
        return weekly_budget
    return monthly_budget


def _budget_pressure(remaining_budget: float, route_cost: float, budget_limit: float) -> str:
    if remaining_budget <= 0 or route_cost > remaining_budget:
        return "over_budget"
    if remaining_budget - route_cost <= max(2.0, budget_limit * 0.15):
        return "close_to_budget"
    return "comfortable"
