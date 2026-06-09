from typing import List

from pydantic import BaseModel


class TripDecisionRecord(BaseModel):
    saved_trip_id: str
    commute_plan_id: str
    user_label: str
    route_summary: str
    estimated_savings: float
    optimized_route_cost: float
    created_by: str = "tollio_api"


class SavingsSummary(BaseModel):
    trip_count: int
    estimated_total_savings: float
    data_source: str


class BudgetProfile(BaseModel):
    user_id: str
    daily_budget: float
    weekly_budget: float
    monthly_budget: float
    current_daily_spend: float
    current_weekly_spend: float
    current_monthly_spend: float
    data_source: str


class BudgetStatus(BaseModel):
    budget_period: str
    budget_limit: float
    estimated_spend: float
    remaining_budget: float
    status: str
    data_source: str


class RecentTrips(BaseModel):
    trips: List[TripDecisionRecord]
    data_source: str
