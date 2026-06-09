from app.models import (
    BudgetStatusResponse,
    BudgetPeriod,
    CommutePlanRequest,
    CommutePlanResponse,
    TripSaveRequest,
    TripSaveResponse,
)
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
    return BudgetStatusResponse(
        budget_period=BudgetPeriod.daily,
        budget_limit=8.0,
        estimated_spend=6.25,
        remaining_budget=1.75,
        status="placeholder_budget_available",
    )
