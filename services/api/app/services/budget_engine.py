from math import ceil
from typing import Optional

from pydantic import BaseModel

from app.models import BudgetDashboardSummary, BudgetPeriod, UrgencyMode


class BudgetIntelligenceResult(BaseModel):
    period_budget: float
    current_period_spend: float
    remaining_budget: float
    estimated_commute_days_remaining: int
    estimated_trips_remaining: int
    recommended_per_trip_allowance: float
    planned_trip_toll_cost: float
    after_trip_remaining_budget: float
    budget_status: str
    forecast_status: str
    recommendation: str
    dashboard_summary: BudgetDashboardSummary


def evaluate_budget(
    budget_amount: float,
    budget_period: BudgetPeriod,
    current_period_spend: float,
    commute_days_per_week: int,
    trips_per_commute_day: int,
    include_weekends: bool,
    planned_trip_toll_cost: float,
    urgency_mode: UrgencyMode,
    remaining_days_in_period: Optional[int] = None,
    savings_to_date: float = 0.0,
) -> BudgetIntelligenceResult:
    period_budget = round(budget_amount, 2)
    current_spend = round(current_period_spend, 2)
    remaining_budget = round(period_budget - current_spend, 2)
    commute_days_remaining = _estimate_commute_days_remaining(
        budget_period=budget_period,
        commute_days_per_week=commute_days_per_week,
        include_weekends=include_weekends,
        remaining_days_in_period=remaining_days_in_period,
    )
    trips_remaining = max(commute_days_remaining * trips_per_commute_day, 1)
    allowance = round(max(remaining_budget, 0.0) / trips_remaining, 2)
    after_trip_remaining = round(remaining_budget - planned_trip_toll_cost, 2)
    budget_status = _budget_status(period_budget, remaining_budget)
    projected_period_spend = round(current_spend + planned_trip_toll_cost * trips_remaining, 2)
    projected_overage = round(max(projected_period_spend - period_budget, 0.0), 2)
    forecast_status = _forecast_status(
        planned_trip_toll_cost=planned_trip_toll_cost,
        recommended_per_trip_allowance=allowance,
        after_trip_remaining_budget=after_trip_remaining,
        projected_overage=projected_overage,
        budget_status=budget_status,
    )
    recommendation = _recommendation(
        budget_status=budget_status,
        forecast_status=forecast_status,
        urgency_mode=urgency_mode,
        planned_trip_toll_cost=planned_trip_toll_cost,
        recommended_per_trip_allowance=allowance,
    )

    return BudgetIntelligenceResult(
        period_budget=period_budget,
        current_period_spend=current_spend,
        remaining_budget=remaining_budget,
        estimated_commute_days_remaining=commute_days_remaining,
        estimated_trips_remaining=trips_remaining,
        recommended_per_trip_allowance=allowance,
        planned_trip_toll_cost=round(planned_trip_toll_cost, 2),
        after_trip_remaining_budget=after_trip_remaining,
        budget_status=budget_status,
        forecast_status=forecast_status,
        recommendation=recommendation,
        dashboard_summary=BudgetDashboardSummary(
            spend_to_date=current_spend,
            budget_remaining=max(after_trip_remaining, 0.0),
            projected_period_spend=projected_period_spend,
            projected_overage=projected_overage,
            savings_to_date=round(savings_to_date, 2),
            dashboard_message=(
                f"{forecast_status.replace('_', ' ').title()}: "
                f"${allowance:.2f} recommended per remaining trip; "
                f"this trip is ${planned_trip_toll_cost:.2f}."
            ),
        ),
    )


def _estimate_commute_days_remaining(
    budget_period: BudgetPeriod,
    commute_days_per_week: int,
    include_weekends: bool,
    remaining_days_in_period: Optional[int],
) -> int:
    if budget_period == BudgetPeriod.daily:
        return 1

    default_days = {
        BudgetPeriod.weekly: 7 if include_weekends else commute_days_per_week,
        BudgetPeriod.monthly: 30 if include_weekends else commute_days_per_week * 4,
        BudgetPeriod.yearly: 365 if include_weekends else commute_days_per_week * 52,
    }[budget_period]

    if remaining_days_in_period is None:
        return max(default_days, 1)

    if include_weekends:
        return max(remaining_days_in_period, 1)

    estimated = ceil(remaining_days_in_period * (commute_days_per_week / 7))
    return max(estimated, 1)


def _budget_status(period_budget: float, remaining_budget: float) -> str:
    if remaining_budget < 0:
        return "over_budget"
    if remaining_budget <= max(2.0, period_budget * 0.15):
        return "close_to_limit"
    return "under_budget"


def _forecast_status(
    planned_trip_toll_cost: float,
    recommended_per_trip_allowance: float,
    after_trip_remaining_budget: float,
    projected_overage: float,
    budget_status: str,
) -> str:
    if budget_status == "over_budget" or after_trip_remaining_budget < 0 or projected_overage > 0:
        return "projected_over"
    if planned_trip_toll_cost > recommended_per_trip_allowance:
        return "at_risk"
    return "on_track"


def _recommendation(
    budget_status: str,
    forecast_status: str,
    urgency_mode: UrgencyMode,
    planned_trip_toll_cost: float,
    recommended_per_trip_allowance: float,
) -> str:
    if budget_status == "over_budget":
        return "You are already over this toll budget; use stronger toll avoidance unless the trip is urgent."
    if forecast_status == "projected_over":
        return "This trip projects the period over budget; skip low-value gantries and prefer service-road alternatives."
    if forecast_status == "at_risk":
        return (
            f"This trip costs ${planned_trip_toll_cost:.2f}, above the "
            f"${recommended_per_trip_allowance:.2f} per-trip allowance; avoid low-value tolls."
        )
    if urgency_mode == UrgencyMode.urgent:
        return "You are on track; urgent mode can spend on high-value toll segments."
    return "You are on track; keep paying only for toll segments with clear time value."
