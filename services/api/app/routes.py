from app.config import SystemStatus, get_system_status
from app.models import (
    BudgetPeriod,
    BudgetStatusResponse,
    CommutePlanRequest,
    CommutePlanResponse,
    TripSaveRequest,
    TripSaveResponse,
    UrgencyMode,
)
from app.persistence.budget_repository import get_budget_repository
from app.persistence.trip_repository import get_trip_repository
from app.services.budget_engine import evaluate_budget
from app.services.commute_planner import build_commute_plan
from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/api/v1/system/status", response_model=SystemStatus)
def system_status() -> SystemStatus:
    return get_system_status()


@router.post("/api/v1/commute/plan", response_model=CommutePlanResponse)
def plan_commute(request: CommutePlanRequest) -> CommutePlanResponse:
    return build_commute_plan(request)


@router.post("/api/v1/trips/save", response_model=TripSaveResponse)
def save_trip(request: TripSaveRequest) -> TripSaveResponse:
    saved_trip = get_trip_repository().save_trip_decision(
        commute_plan_id=request.commute_plan_id,
        user_label=request.user_label,
    )
    return TripSaveResponse(
        status="saved",
        message=f"Trip '{request.user_label}' saved by {saved_trip.created_by}.",
        saved_trip_id=saved_trip.saved_trip_id,
    )


@router.get("/api/v1/budget/status", response_model=BudgetStatusResponse)
def budget_status() -> BudgetStatusResponse:
    budget = get_budget_repository().get_budget_status()
    budget_period = BudgetPeriod(budget.budget_period)
    budget_result = evaluate_budget(
        budget_amount=budget.budget_limit,
        budget_period=budget_period,
        current_period_spend=budget.estimated_spend,
        commute_days_per_week=5,
        trips_per_commute_day=2,
        include_weekends=False,
        planned_trip_toll_cost=0.0,
        urgency_mode=UrgencyMode.balanced,
        savings_to_date=4.5,
    )
    return BudgetStatusResponse(
        budget_period=budget_period,
        budget_limit=budget.budget_limit,
        estimated_spend=budget.estimated_spend,
        remaining_budget=budget.remaining_budget,
        status=budget.status,
        budget_summary=budget_result.dashboard_summary,
    )
