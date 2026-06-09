from app.models import (
    BudgetStatusResponse,
    CommutePlanRequest,
    CommutePlanResponse,
    TripSaveRequest,
    TripSaveResponse,
)
from app.persistence.budget_repository import get_budget_repository
from app.persistence.trip_repository import get_trip_repository
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
    saved_trip = get_trip_repository().save_trip_decision(
        commute_plan_id=request.commute_plan_id,
        user_label=request.user_label,
    )
    return TripSaveResponse(
        status="saved",
        message=f"Trip '{request.user_label}' saved.",
        saved_trip_id=saved_trip.saved_trip_id,
    )


@router.get("/api/v1/budget/status", response_model=BudgetStatusResponse)
def budget_status() -> BudgetStatusResponse:
    budget = get_budget_repository().get_budget_status()
    return BudgetStatusResponse(
        budget_period=budget.budget_period,
        budget_limit=budget.budget_limit,
        estimated_spend=budget.estimated_spend,
        remaining_budget=budget.remaining_budget,
        status=budget.status,
    )
