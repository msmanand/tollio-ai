from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.adapters.google_routes_adapter import NormalizedRouteOption, NormalizedRouteSegment
from app.models import BudgetPeriod, GantryAction, GantryDecision, UrgencyMode, ValueScoreBreakdown
from app.services.value_score import average_combined_score, build_value_score_breakdown
from pydantic import BaseModel


@dataclass(frozen=True)
class GantryCandidate:
    action: GantryAction
    toll_cost_avoided: float
    added_minutes: int
    signal_penalty: int
    strategy_label: str
    estimated_minutes_saved: int
    cost_per_minute_saved: float


class RouteChargeSummary(BaseModel):
    label: str
    amount: float
    reason: str
    tolltag_rate: Optional[float] = None
    zipcash_rate: Optional[float] = None
    confidence: Optional[str] = None
    source: Optional[str] = None


class RouteValueCandidate(BaseModel):
    strategy: str
    total_toll_cost: float
    toll_cost_avoided: float
    total_minutes: int
    added_minutes_vs_fastest: int
    estimated_signal_penalty: int
    toll_minutes_used: int
    service_road_minutes: int
    paid_segment_value_score: float
    cost_per_minute_saved: float
    budget_pressure_score: float
    final_value_score: float
    avoided_charges: List[RouteChargeSummary]
    paid_charges: List[RouteChargeSummary]
    recommendation_reason: str
    enter_guidance: str
    exit_guidance: str
    service_road_guidance: str
    toll_worth_paying: str
    toll_not_worth_paying: str
    budget_impact: str
    entry_value_score: int = 0
    exit_value_score: int = 0
    combined_value_score: int = 0
    wasted_behind: int = 0
    unused_ahead: int = 0
    paid_but_unused_reason: str = "No NTTA toll-tier data matched this candidate."
    value_loss_reason: str = "No NTTA toll-tier data matched this candidate."


class RouteValueOptimization(BaseModel):
    recommended_strategy: str
    route_value_score: float
    toll_minutes_used: int
    service_road_minutes: int
    avoided_charges: List[RouteChargeSummary]
    paid_charges: List[RouteChargeSummary]
    explanation: str
    candidates: List[RouteValueCandidate]
    value_score_breakdown: List[ValueScoreBreakdown] = []
    entry_value_score: int = 0
    exit_value_score: int = 0
    combined_value_score: int = 0
    paid_but_unused_reason: str = "No NTTA toll-tier data matched this route."
    value_loss_reason: str = "No NTTA toll-tier data matched this route."
    ntta_data_used: bool = False
    google_routes_data_used: bool = False


MODE_THRESHOLDS = {
    UrgencyMode.saver: 10,
    UrgencyMode.balanced: 5,
    UrgencyMode.urgent: 2,
}


def optimize_route_value(
    route_option: NormalizedRouteOption,
    urgency_mode: UrgencyMode,
    budget_period: BudgetPeriod,
    daily_budget: float,
    weekly_budget: float,
    monthly_budget: float,
    current_period_spend: float = 0.0,
    avoid_excessive_signals: bool = True,
) -> RouteValueOptimization:
    budget_limit = _budget_limit(
        budget_period,
        daily_budget=daily_budget,
        weekly_budget=weekly_budget,
        monthly_budget=monthly_budget,
    )
    remaining_budget = budget_limit - current_period_spend
    fastest_minutes = _fastest_route_minutes(route_option)
    toll_segments = _toll_segments(route_option)
    all_toll_cost = round(sum(segment.estimated_cost for segment in toll_segments), 2)
    ntta_breakdowns = _ntta_value_breakdowns(route_option)
    ntta_summary = _ntta_value_summary(ntta_breakdowns)
    candidates = [
        _route_candidate(
            strategy="full_toll_route",
            route_option=route_option,
            paid_segments=toll_segments,
            avoided_segments=[],
            fastest_minutes=fastest_minutes,
            added_minutes=0,
            signal_penalty=0,
            remaining_budget=remaining_budget,
            budget_limit=budget_limit,
            urgency_mode=urgency_mode,
            service_road_minutes=0,
            value_breakdowns=ntta_breakdowns,
            guidance=(
                "Enter the toll road at the first practical ramp.",
                "Stay on toll until the destination approach.",
                "Do not continue service road unless traffic changes.",
            ),
        ),
        _route_candidate(
            strategy="delayed_toll_entry",
            route_option=route_option,
            paid_segments=toll_segments[1:],
            avoided_segments=toll_segments[:1],
            fastest_minutes=fastest_minutes,
            added_minutes=3,
            signal_penalty=2 if avoid_excessive_signals else 0,
            remaining_budget=remaining_budget,
            budget_limit=budget_limit,
            urgency_mode=urgency_mode,
            service_road_minutes=_service_minutes(route_option) + 3,
            value_breakdowns=ntta_breakdowns,
            guidance=(
                "Delay toll entry by one or more exits when the first gantry is low value.",
                "Exit only if the remaining paid segment stops producing value.",
                "Use service road for the opening stretch, then enter when time savings improve.",
            ),
        ),
        _route_candidate(
            strategy="early_toll_exit",
            route_option=route_option,
            paid_segments=toll_segments[:-1],
            avoided_segments=toll_segments[-1:],
            fastest_minutes=fastest_minutes,
            added_minutes=4,
            signal_penalty=2 if avoid_excessive_signals else 0,
            remaining_budget=remaining_budget,
            budget_limit=budget_limit,
            urgency_mode=urgency_mode,
            service_road_minutes=_service_minutes(route_option) + 4,
            value_breakdowns=ntta_breakdowns,
            guidance=(
                "Enter toll normally for the high-value middle segment.",
                "Exit before the last low-value charge.",
                "Continue on service road or local road to destination if the time impact stays reasonable.",
            ),
        ),
        _route_candidate(
            strategy="delayed_entry_and_early_exit",
            route_option=route_option,
            paid_segments=toll_segments[1:-1],
            avoided_segments=_unique_segments(toll_segments[:1] + toll_segments[-1:]),
            fastest_minutes=fastest_minutes,
            added_minutes=6,
            signal_penalty=4 if avoid_excessive_signals else 1,
            remaining_budget=remaining_budget,
            budget_limit=budget_limit,
            urgency_mode=urgency_mode,
            service_road_minutes=_service_minutes(route_option) + 6,
            value_breakdowns=ntta_breakdowns,
            guidance=(
                "Delay entry until the paid segment becomes useful.",
                "Exit before the final low-value gantry.",
                "Use service road at both ends and pay only for the route core.",
            ),
        ),
        _route_candidate(
            strategy="service_road_to_destination",
            route_option=route_option,
            paid_segments=[],
            avoided_segments=toll_segments,
            fastest_minutes=fastest_minutes,
            added_minutes=min(14, 5 + len(toll_segments) * 2),
            signal_penalty=6 if avoid_excessive_signals else 2,
            remaining_budget=remaining_budget,
            budget_limit=budget_limit,
            urgency_mode=urgency_mode,
            service_road_minutes=_service_minutes(route_option) + fastest_minutes + 5,
            value_breakdowns=ntta_breakdowns,
            guidance=(
                "Do not enter toll unless urgency changes.",
                "No toll exit needed because the route stays off paid scanners.",
                "Stay on service road or local road to destination.",
            ),
        ),
        _route_candidate(
            strategy="avoid_connector_or_bridge_toll",
            route_option=route_option,
            paid_segments=_without_connector_segment(toll_segments),
            avoided_segments=_connector_segments(toll_segments),
            fastest_minutes=fastest_minutes,
            added_minutes=2,
            signal_penalty=1 if avoid_excessive_signals else 0,
            remaining_budget=remaining_budget,
            budget_limit=budget_limit,
            urgency_mode=urgency_mode,
            service_road_minutes=_service_minutes(route_option) + 2,
            value_breakdowns=ntta_breakdowns,
            guidance=(
                "Enter toll for useful mainline time savings.",
                "Exit or bypass before the bridge, ramp, or connector charge.",
                "Use the parallel service/local connector when the paid connector is low value.",
            ),
        ),
        _route_candidate(
            strategy="max_value_after_paid_gantry",
            route_option=route_option,
            paid_segments=_high_value_segments(toll_segments),
            avoided_segments=_low_value_segments(toll_segments),
            fastest_minutes=fastest_minutes,
            added_minutes=5,
            signal_penalty=3 if avoid_excessive_signals else 1,
            remaining_budget=remaining_budget,
            budget_limit=budget_limit,
            urgency_mode=urgency_mode,
            service_road_minutes=_service_minutes(route_option) + 5,
            value_breakdowns=ntta_breakdowns,
            guidance=(
                "Enter toll at the first high-value segment.",
                "Exit once the remaining paid segment stops beating service-road value.",
                "Continue service road/local road after the useful toll time is extracted.",
            ),
        ),
    ]
    if all_toll_cost == 0:
        candidates = [
            _route_candidate(
                strategy="service_road_to_destination",
                route_option=route_option,
                paid_segments=[],
                avoided_segments=[],
                fastest_minutes=max(route_option.total_minutes, 1),
                added_minutes=0,
                signal_penalty=0,
                remaining_budget=remaining_budget,
                budget_limit=budget_limit,
                urgency_mode=urgency_mode,
                service_road_minutes=_service_minutes(route_option),
                value_breakdowns=[],
                guidance=(
                    "No toll entry is needed.",
                    "No toll exit is needed.",
                    "Continue on the available local/service route.",
                ),
            )
        ]
    winner = max(
        candidates,
        key=lambda candidate: (
            candidate.final_value_score,
            -candidate.total_toll_cost,
            candidate.toll_cost_avoided,
        ),
    )
    return RouteValueOptimization(
        recommended_strategy=winner.strategy,
        route_value_score=winner.final_value_score,
        toll_minutes_used=winner.toll_minutes_used,
        service_road_minutes=winner.service_road_minutes,
        avoided_charges=winner.avoided_charges,
        paid_charges=winner.paid_charges,
        explanation=_route_value_explanation(winner),
        candidates=candidates,
        value_score_breakdown=ntta_breakdowns,
        entry_value_score=ntta_summary["entry_value_score"],
        exit_value_score=ntta_summary["exit_value_score"],
        combined_value_score=ntta_summary["combined_value_score"],
        paid_but_unused_reason=ntta_summary["paid_but_unused_reason"],
        value_loss_reason=ntta_summary["value_loss_reason"],
        ntta_data_used=bool(ntta_breakdowns),
        google_routes_data_used=route_option.data_source.startswith("live_google"),
    )


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


def _route_candidate(
    strategy: str,
    route_option: NormalizedRouteOption,
    paid_segments: List[NormalizedRouteSegment],
    avoided_segments: List[NormalizedRouteSegment],
    fastest_minutes: int,
    added_minutes: int,
    signal_penalty: int,
    remaining_budget: float,
    budget_limit: float,
    urgency_mode: UrgencyMode,
    service_road_minutes: int,
    value_breakdowns: List[ValueScoreBreakdown],
    guidance: tuple[str, str, str],
) -> RouteValueCandidate:
    total_toll_cost = round(sum(segment.estimated_cost for segment in paid_segments), 2)
    toll_cost_avoided = round(sum(segment.estimated_cost for segment in avoided_segments), 2)
    total_minutes = fastest_minutes + added_minutes
    toll_minutes_used = sum(segment.estimated_minutes for segment in paid_segments)
    minutes_saved = max(route_option.total_minutes + 8 - total_minutes, 1)
    cost_per_minute_saved = round(total_toll_cost / minutes_saved, 2) if total_toll_cost else 0.0
    paid_segment_value_score = _paid_segment_value_score(paid_segments, value_breakdowns)
    ntta_summary = _ntta_value_summary(value_breakdowns)
    budget_pressure_score = _budget_pressure_score(
        total_toll_cost=total_toll_cost,
        remaining_budget=remaining_budget,
        budget_limit=budget_limit,
    )
    final_value_score = _route_final_value_score(
        total_toll_cost=total_toll_cost,
        toll_cost_avoided=toll_cost_avoided,
        added_minutes=added_minutes,
        signal_penalty=signal_penalty,
        paid_segment_value_score=paid_segment_value_score,
        cost_per_minute_saved=cost_per_minute_saved,
        budget_pressure_score=budget_pressure_score,
        urgency_mode=urgency_mode,
    )
    avoided_charges = [
        RouteChargeSummary(
            label=segment.segment_label,
            amount=round(segment.estimated_cost, 2),
            reason=_avoided_charge_reason(segment, strategy),
            tolltag_rate=segment.tolltag_rate,
            zipcash_rate=segment.zipcash_rate,
            confidence=segment.rate_confidence,
            source=segment.rate_source,
        )
        for segment in avoided_segments
    ]
    paid_charges = [
        RouteChargeSummary(
            label=segment.segment_label,
            amount=round(segment.estimated_cost, 2),
            reason=_paid_charge_reason(segment),
            tolltag_rate=segment.tolltag_rate,
            zipcash_rate=segment.zipcash_rate,
            confidence=segment.rate_confidence,
            source=segment.rate_source,
        )
        for segment in paid_segments
    ]
    toll_worth_paying = (
        ", ".join(charge.label for charge in paid_charges)
        if paid_charges
        else "No paid toll segment is worth using for this budget and urgency."
    )
    toll_not_worth_paying = (
        ", ".join(charge.label for charge in avoided_charges)
        if avoided_charges
        else "No toll charge is avoided in this strategy."
    )
    budget_impact = _route_budget_impact(total_toll_cost, remaining_budget)

    return RouteValueCandidate(
        strategy=strategy,
        total_toll_cost=total_toll_cost,
        toll_cost_avoided=toll_cost_avoided,
        total_minutes=total_minutes,
        added_minutes_vs_fastest=added_minutes,
        estimated_signal_penalty=signal_penalty,
        toll_minutes_used=toll_minutes_used,
        service_road_minutes=service_road_minutes,
        paid_segment_value_score=paid_segment_value_score,
        cost_per_minute_saved=cost_per_minute_saved,
        budget_pressure_score=budget_pressure_score,
        final_value_score=final_value_score,
        avoided_charges=avoided_charges,
        paid_charges=paid_charges,
        recommendation_reason=(
            f"{strategy} scores {final_value_score:.2f} by balancing "
            f"{total_minutes} minutes, ${total_toll_cost:.2f} toll spend, "
            f"${toll_cost_avoided:.2f} avoided, and budget pressure."
        ),
        enter_guidance=guidance[0],
        exit_guidance=guidance[1],
        service_road_guidance=guidance[2],
        toll_worth_paying=toll_worth_paying,
        toll_not_worth_paying=toll_not_worth_paying,
        budget_impact=budget_impact,
        entry_value_score=ntta_summary["entry_value_score"],
        exit_value_score=ntta_summary["exit_value_score"],
        combined_value_score=ntta_summary["combined_value_score"],
        wasted_behind=ntta_summary["wasted_behind"],
        unused_ahead=ntta_summary["unused_ahead"],
        paid_but_unused_reason=ntta_summary["paid_but_unused_reason"],
        value_loss_reason=ntta_summary["value_loss_reason"],
    )


def _route_final_value_score(
    total_toll_cost: float,
    toll_cost_avoided: float,
    added_minutes: int,
    signal_penalty: int,
    paid_segment_value_score: float,
    cost_per_minute_saved: float,
    budget_pressure_score: float,
    urgency_mode: UrgencyMode,
) -> float:
    time_weight = {
        UrgencyMode.saver: 0.22,
        UrgencyMode.balanced: 0.38,
        UrgencyMode.urgent: 0.85,
    }[urgency_mode]
    savings_weight = {
        UrgencyMode.saver: 0.34,
        UrgencyMode.balanced: 0.45,
        UrgencyMode.urgent: 0.08,
    }[urgency_mode]
    paid_value_weight = {
        UrgencyMode.saver: 0.62,
        UrgencyMode.balanced: 0.9,
        UrgencyMode.urgent: 1.35,
    }[urgency_mode]
    signal_weight = _signal_weight(urgency_mode)
    raw_score = (
        paid_segment_value_score * paid_value_weight
        + toll_cost_avoided * savings_weight
        - added_minutes * time_weight
        - signal_penalty * signal_weight
        - budget_pressure_score * 2.2
        - max(cost_per_minute_saved - 1.5, 0) * 0.45
        - total_toll_cost * 0.03
    )
    normalized = (raw_score + 8.0) / 16.0
    return round(max(0.0, min(normalized, 1.0)), 2)


def _paid_segment_value_score(
    segments: List[NormalizedRouteSegment],
    value_breakdowns: List[ValueScoreBreakdown],
) -> float:
    if not segments:
        return 0.0
    values = [
        min(segment.estimated_minutes / max(segment.estimated_cost, 0.01), 10.0) / 10.0
        for segment in segments
    ]
    if value_breakdowns:
        values.append(average_combined_score(value_breakdowns) / 100)
    return round(sum(values) / len(values), 2)


def _budget_pressure_score(
    total_toll_cost: float,
    remaining_budget: float,
    budget_limit: float,
) -> float:
    if total_toll_cost <= 0:
        if remaining_budget <= 0:
            return -0.6
        return 0.0
    if remaining_budget <= 0:
        return min(1.0, 0.55 + total_toll_cost / max(budget_limit, 1.0))
    if total_toll_cost > remaining_budget:
        return 0.85
    if remaining_budget - total_toll_cost <= max(2.0, budget_limit * 0.15):
        return 0.45
    return 0.0


def _route_budget_impact(total_toll_cost: float, remaining_budget: float) -> str:
    projected_remaining = round(remaining_budget - total_toll_cost, 2)
    if projected_remaining < 0:
        return f"This route is ${abs(projected_remaining):.2f} over the selected toll budget."
    return f"This route leaves ${projected_remaining:.2f} in the selected toll budget."


def _route_value_explanation(candidate: RouteValueCandidate) -> str:
    return (
        f"Recommended strategy: {candidate.strategy}. "
        f"Pay for: {candidate.toll_worth_paying}. "
        f"Avoid: {candidate.toll_not_worth_paying}. "
        f"{candidate.enter_guidance} {candidate.exit_guidance} "
        f"{candidate.service_road_guidance} {candidate.budget_impact}"
    )


def _fastest_route_minutes(route_option: NormalizedRouteOption) -> int:
    service_minutes = _service_minutes(route_option)
    local_minutes = sum(
        segment.estimated_minutes
        for segment in route_option.segments
        if segment.segment_type == "local_road"
    )
    return max(route_option.total_minutes - min(service_minutes + local_minutes, 10), 1)


def _service_minutes(route_option: NormalizedRouteOption) -> int:
    return sum(
        segment.estimated_minutes
        for segment in route_option.segments
        if segment.segment_type in {"service_road", "local_road"}
    )


def _toll_segments(route_option: NormalizedRouteOption) -> List[NormalizedRouteSegment]:
    return [
        segment
        for segment in route_option.segments
        if segment.segment_type == "toll" and segment.estimated_cost > 0
    ]


def _connector_segments(
    segments: List[NormalizedRouteSegment],
) -> List[NormalizedRouteSegment]:
    connector_segments = [
        segment
        for segment in segments
        if _is_connector_or_bridge(segment)
    ]
    if connector_segments:
        return connector_segments
    return []


def _unique_segments(
    segments: List[NormalizedRouteSegment],
) -> List[NormalizedRouteSegment]:
    seen = set()
    unique = []
    for segment in segments:
        key = segment.segment_label
        if key not in seen:
            unique.append(segment)
            seen.add(key)
    return unique


def _without_connector_segment(
    segments: List[NormalizedRouteSegment],
) -> List[NormalizedRouteSegment]:
    connector_labels = {
        segment.segment_label
        for segment in _connector_segments(segments)
    }
    return [
        segment
        for segment in segments
        if segment.segment_label not in connector_labels
    ]


def _high_value_segments(
    segments: List[NormalizedRouteSegment],
) -> List[NormalizedRouteSegment]:
    high_value = [
        segment
        for segment in segments
        if segment.estimated_minutes / max(segment.estimated_cost, 0.01) >= 2.5
    ]
    if high_value:
        return high_value
    if not segments:
        return []
    return [max(segments, key=lambda segment: segment.estimated_minutes / max(segment.estimated_cost, 0.01))]


def _low_value_segments(
    segments: List[NormalizedRouteSegment],
) -> List[NormalizedRouteSegment]:
    high_value_labels = {
        segment.segment_label
        for segment in _high_value_segments(segments)
    }
    return [
        segment
        for segment in segments
        if segment.segment_label not in high_value_labels
    ]


def _is_connector_or_bridge(segment: NormalizedRouteSegment) -> bool:
    label = f"{segment.segment_label} {segment.road_name}".lower()
    return any(keyword in label for keyword in ["bridge", "connector", "ramp"])


def _paid_charge_reason(segment: NormalizedRouteSegment) -> str:
    value = segment.estimated_minutes / max(segment.estimated_cost, 0.01)
    return (
        f"Worth paying because it provides about {segment.estimated_minutes} "
        f"minutes of toll-road usefulness at {value:.1f} minutes per dollar."
    )


def _avoided_charge_reason(segment: NormalizedRouteSegment, strategy: str) -> str:
    if _is_connector_or_bridge(segment):
        return "Avoided because this bridge, ramp, or connector toll has low route value."
    if strategy == "delayed_toll_entry":
        return "Avoided by delaying toll entry until the paid segment becomes useful."
    if strategy == "early_toll_exit":
        return "Avoided by exiting before the route stops extracting enough toll value."
    if strategy == "service_road_to_destination":
        return "Avoided by staying on service/local road to the destination."
    return "Avoided because the segment does not provide enough value for the budget."


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
    if budget_period == BudgetPeriod.monthly:
        return monthly_budget
    return monthly_budget * 12


def _budget_pressure(remaining_budget: float, route_cost: float, budget_limit: float) -> str:
    if remaining_budget <= 0 or route_cost > remaining_budget:
        return "over_budget"
    if remaining_budget - route_cost <= max(2.0, budget_limit * 0.15):
        return "close_to_budget"
    return "comfortable"


def _ntta_value_breakdowns(route_option: NormalizedRouteOption) -> List[ValueScoreBreakdown]:
    breakdowns = []
    for segment in _toll_segments(route_option):
        match = _ntta_segment_match(segment)
        if match is None:
            continue
        road_short, entry_index, exit_index = match
        breakdown = build_value_score_breakdown(road_short, entry_index, exit_index)
        if breakdown is None:
            continue
        breakdowns.append(ValueScoreBreakdown(**breakdown.model_dump()))
    return breakdowns


def _ntta_segment_match(segment: NormalizedRouteSegment) -> Optional[Tuple[str, int, int]]:
    road_name = segment.road_name.lower()
    start = segment.start_location.lower()
    end = segment.end_location.lower()
    label = segment.segment_label.lower()
    if "dallas north tollway" in road_name:
        if "frisco" in start or "segment a" in label:
            return ("DNT", 26, 17)
        if "downtown" in end or "north dallas" in start or "segment c" in label:
            return ("DNT", 17, 0)
    if "121" in road_name or "sam rayburn" in road_name:
        return ("SH-121", 17, 0)
    return None


def _ntta_value_summary(breakdowns: List[ValueScoreBreakdown]) -> dict:
    if not breakdowns:
        return {
            "entry_value_score": 0,
            "exit_value_score": 0,
            "combined_value_score": 0,
            "wasted_behind": 0,
            "unused_ahead": 0,
            "paid_but_unused_reason": "No NTTA toll-tier data matched this route.",
            "value_loss_reason": "No NTTA toll-tier data matched this route.",
        }
    lowest = min(breakdowns, key=lambda item: item.combined_value_score)
    return {
        "entry_value_score": round(
            sum(item.entry_value_score for item in breakdowns) / len(breakdowns)
        ),
        "exit_value_score": round(
            sum(item.exit_value_score for item in breakdowns) / len(breakdowns)
        ),
        "combined_value_score": round(
            sum(item.combined_value_score for item in breakdowns) / len(breakdowns)
        ),
        "wasted_behind": sum(item.wasted_behind for item in breakdowns),
        "unused_ahead": sum(item.unused_ahead for item in breakdowns),
        "paid_but_unused_reason": lowest.paid_but_unused_reason,
        "value_loss_reason": lowest.value_loss_reason,
    }
