from app.config import SystemStatus, get_system_status
from app.models import (
    BudgetPeriod,
    BudgetStatusResponse,
    CommutePlanRequest,
    CommutePlanResponse,
    NTTARatesLookupResponse,
    NTTATollPoint,
    TripSaveRequest,
    TripSaveResponse,
    UrgencyMode,
)
from app.data.ntta_matrix import exit_options, find_exit_index, find_road, get_matrix_price, road_options
from app.data.ntta_rates import find_toll_points, toll_points, unknown_rate
from app.persistence.budget_repository import get_budget_repository
from app.persistence.trip_repository import get_trip_repository
from app.services.budget_engine import evaluate_budget
from app.services.commute_planner import build_commute_plan
from app.services.tollio_brain import (
    BrainProfile,
    entryVScore,
    exitVScore,
    optimize_trip_by_matrix_names,
    projectAnnualSaving,
    unusedAhead,
    vScore,
    wastedBehind,
)
from fastapi import APIRouter, HTTPException


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


@router.get("/api/v1/ntta/toll-points", response_model=list[NTTATollPoint])
def ntta_toll_points(vehicle_class: str = "two_axle_passenger") -> list[NTTATollPoint]:
    return [
        NTTATollPoint(**entry.model_dump())
        for entry in toll_points(vehicle_class)
    ]


@router.get("/api/v1/ntta/rates", response_model=NTTARatesLookupResponse)
def ntta_rates(entry: str, exit: str, vehicle_class: str = "two_axle_passenger") -> NTTARatesLookupResponse:
    entry_matches = find_toll_points(entry, vehicle_class) or [unknown_rate(entry, vehicle_class)]
    exit_matches = find_toll_points(exit, vehicle_class) or [unknown_rate(exit, vehicle_class)]
    return NTTARatesLookupResponse(
        exact_route_pricing_available=False,
        message=(
            "Exact entry-to-exit route pricing is not computed from the PDF toll-point table. "
            "Returning matched toll points and official rates only."
        ),
        entry_matches=[NTTATollPoint(**match.model_dump()) for match in entry_matches],
        exit_matches=[NTTATollPoint(**match.model_dump()) for match in exit_matches],
    )


@router.get("/api/v1/ntta/roads")
def ntta_roads() -> dict:
    return {"roads": road_options()}


@router.get("/api/v1/ntta/exits")
def ntta_exits(road: str) -> dict:
    matched_road = find_road(road)
    if matched_road is None:
        raise HTTPException(status_code=404, detail=f"Unknown NTTA road: {road}")
    return {
        "road": {
            "road_id": matched_road.road_id,
            "road_short": matched_road.road_short,
            "road_name": matched_road.road_name,
        },
        "exits": exit_options(matched_road),
        "source_metadata": _source_metadata(matched_road),
    }


@router.get("/api/v1/ntta/price")
def ntta_price(road: str, from_exit: str, to_exit: str, payment: str = "tolltag") -> dict:
    if payment not in {"tolltag", "zipcash"}:
        raise HTTPException(status_code=422, detail="payment must be tolltag or zipcash")
    matched_road = find_road(road)
    if matched_road is None:
        raise HTTPException(status_code=404, detail=f"Unknown NTTA road: {road}")
    lookup = get_matrix_price(matched_road, from_exit, to_exit, payment)
    return {
        "road_name": lookup.road_name,
        "road_short": lookup.road_short,
        "from_exit": lookup.from_exit,
        "to_exit": lookup.to_exit,
        "payment": lookup.payment,
        "price": lookup.price,
        "exact_matrix_match": lookup.exact_matrix_match,
        "source_metadata": {
            "source_file": lookup.source_file,
            "effective_date": lookup.effective_date,
            "payment_type": payment,
            "confidence": lookup.confidence,
        },
    }


@router.post("/api/v1/optimize/entry-exit")
def optimize_entry_exit(request: dict) -> dict:
    road_name = str(request.get("road", ""))
    from_exit = str(request.get("from_exit", ""))
    to_exit = str(request.get("to_exit", ""))
    payment = str(request.get("payment", "tolltag"))
    if payment not in {"tolltag", "zipcash"}:
        raise HTTPException(status_code=422, detail="payment must be tolltag or zipcash")

    matched_road = find_road(road_name)
    if matched_road is None:
        raise HTTPException(status_code=404, detail=f"Unknown NTTA road: {road_name}")
    from_index = find_exit_index(matched_road, from_exit)
    to_index = find_exit_index(matched_road, to_exit)
    if from_index is None or to_index is None:
        raise HTTPException(status_code=404, detail="Unknown NTTA from/to exit for selected road")

    profile = BrainProfile(
        toll_payment=payment,
        mpg=float(request.get("mpg", 28) or 28),
        gas_price=float(request.get("gas_price", 3.25) or 3.25),
        vehicle_type=str(request.get("vehicle_type", "gas")),
        traffic_mode=str(request.get("traffic_mode", "offpeak")),
    )
    results = optimize_trip_by_matrix_names(matched_road.road_short, from_exit, to_exit, profile)
    if not results:
        raise HTTPException(status_code=404, detail="No matrix route found for selected road/exits")

    best = results[0]
    natural_route = _natural_option(matched_road, from_index, to_index, profile)
    optimized_route = _brain_result_option(best, matched_road)
    ranked_options = sorted(
        [optimized_route, natural_route],
        key=lambda item: (-item["combined_value_score"], item["toll_price"]),
    )
    recommendation = _recommendation(best, matched_road, profile.toll_payment)
    return {
        "natural_route": natural_route,
        "optimized_route": optimized_route,
        "ranked_options": ranked_options,
        "explanation": recommendation["plain_english_reason"],
        "recommendation": recommendation,
        "source_metadata": _source_metadata(matched_road),
    }


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


def _natural_option(road, from_index: int, to_index: int, profile: BrainProfile) -> dict:
    from_exit = road.exits[from_index]
    to_exit = road.exits[to_index]
    lookup = get_matrix_price(road, from_exit, to_exit, profile.toll_payment)
    natural_price = lookup.price
    if natural_price is None:
        natural_price = 0.0
    return {
        "entry": from_exit,
        "exit": to_exit,
        "toll_price": natural_price,
        "natural_price": natural_price,
        "toll_saved": 0.0,
        "service_road_minutes": 0,
        "service_road_miles": 0.0,
        "gas_cost": 0.0,
        "net_saving": 0.0,
        "entry_value_score": entryVScore(_brain_road_from_matrix(road), from_index, to_index, profile.toll_payment),
        "exit_value_score": exitVScore(_brain_road_from_matrix(road), from_index, to_index, profile.toll_payment),
        "combined_value_score": vScore(_brain_road_from_matrix(road), from_index, to_index, profile.toll_payment),
        "wasted_behind": wastedBehind(_brain_road_from_matrix(road), from_index, to_index, profile.toll_payment),
        "unused_ahead": unusedAhead(_brain_road_from_matrix(road), from_index, to_index, profile.toll_payment),
        "recommendation_label": "Natural Route",
        "plain_english_reason": "This is the toll cost for the selected NTTA matrix entry and exit.",
    }


def _brain_result_option(result, road) -> dict:
    segment = result.segments[0]
    entry = segment.used_entry
    exit_option = segment.used_exit
    label = "Recommended"
    if result.net_saving <= 0 and result.avg_value_score >= 95:
        label = "Natural Route Already Strong"
    return {
        "entry": entry.exit_name,
        "exit": exit_option.exit_name,
        "toll_price": result.total_price,
        "natural_price": result.natural_total,
        "toll_saved": result.toll_saved,
        "service_road_minutes": result.total_svc_mins,
        "service_road_miles": result.total_svc_miles,
        "gas_cost": result.gas_cost,
        "net_saving": result.net_saving,
        "entry_value_score": segment.used_entry.score,
        "exit_value_score": segment.used_exit.score,
        "combined_value_score": result.avg_value_score,
        "wasted_behind": segment.used_entry.wasted,
        "unused_ahead": segment.used_exit.unused,
        "recommendation_label": label,
        "plain_english_reason": _plain_reason(result, road),
    }


def _recommendation(result, road, payment: str) -> dict:
    segment = result.segments[0]
    natural_entry = road.exits[segment.natural_entry]
    natural_exit = road.exits[segment.natural_exit]
    option = _brain_result_option(result, road)
    natural_score = vScore(
        _brain_road_from_matrix(road),
        segment.natural_entry,
        segment.natural_exit,
        payment,
    )
    return {
        "natural_entry": natural_entry,
        "better_entry": option["entry"],
        "natural_exit": natural_exit,
        "better_exit": option["exit"],
        "toll_saved": result.toll_saved,
        "gas_cost": result.gas_cost,
        "net_saving": result.net_saving,
        "extra_time_minutes": result.total_svc_mins,
        "natural_value_score": natural_score,
        "optimized_value_score": result.avg_value_score,
        "annual_saving_projection": projectAnnualSaving(result.net_saving),
        "plain_english_reason": option["plain_english_reason"],
    }


def _plain_reason(result, road) -> str:
    segment = result.segments[0]
    entry_changed = segment.used_entry.exit_idx != segment.natural_entry
    exit_changed = segment.used_exit.exit_idx != segment.natural_exit
    parts = []
    if entry_changed:
        parts.append(
            f"Entering at {segment.used_entry.exit_name} instead of {road.exits[segment.natural_entry]} avoids paying for an earlier toll tier you would not fully use."
        )
    if exit_changed:
        parts.append(
            f"Exiting at {segment.used_exit.exit_name} instead of {road.exits[segment.natural_exit]} avoids paying for unused toll road ahead."
        )
    if not parts:
        parts.append("The selected entry and exit already use the paid toll tier efficiently.")
    if result.net_saving > 0:
        parts.append(
            f"The matrix shows ${result.toll_saved:.2f} in toll savings, ${result.gas_cost:.2f} in gas cost, and ${result.net_saving:.2f} net saved."
        )
    return " ".join(parts)


def _source_metadata(road) -> dict:
    return {
        "source_file": road.source_file,
        "effective_date": road.effective_date,
        "payment_types": ["tolltag", "zipcash"],
        "confidence": road.confidence,
    }


def _brain_road_from_matrix(road):
    from app.services.tollio_brain import matrix_brain_roads

    for item in matrix_brain_roads():
        if item.id == road.road_id:
            return item
    raise HTTPException(status_code=404, detail=f"Unknown NTTA road: {road.road_name}")
