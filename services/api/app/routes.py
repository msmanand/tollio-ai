from app.models import (
    BudgetStatusResponse,
    BudgetPeriod,
    CommutePlanRequest,
    CommutePlanResponse,
    TripSaveRequest,
    TripSaveResponse,
    UrgencyMode,
)
from app.services.budget_engine import evaluate_budget
from app.services.commute_planner import build_commute_plan
from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/api/v1/commute/plan", response_model=CommutePlanResponse)
def plan_commute(request: CommutePlanRequest) -> CommutePlanResponse:
    return build_commute_plan(request)


@router.post("/api/v1/trips/save", response_model=TripSaveResponse)
def save_trip(request: TripSaveRequest) -> TripSaveResponse:
    return TripSaveResponse(
        status="accepted",
        message=f"Trip '{request.user_label}' accepted by placeholder contract.",
    )


@router.get("/api/v1/budget/status", response_model=BudgetStatusResponse)
def budget_status() -> BudgetStatusResponse:
    budget_result = evaluate_budget(
        budget_amount=8.0,
        budget_period=BudgetPeriod.daily,
        current_period_spend=6.25,
        commute_days_per_week=5,
        trips_per_commute_day=2,
        include_weekends=False,
        planned_trip_toll_cost=0.0,
        urgency_mode=UrgencyMode.balanced,
        savings_to_date=4.5,
    )
    return BudgetStatusResponse(
        budget_period=BudgetPeriod.daily,
        budget_limit=budget_result.period_budget,
        estimated_spend=budget_result.current_period_spend,
        remaining_budget=budget_result.remaining_budget,
        status=budget_result.budget_status,
        budget_summary=budget_result.dashboard_summary,
    )
