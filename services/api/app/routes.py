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
from app.data.ntta_matrix import exit_options, find_exit_index, find_road, get_matrix_price, matrix_data_source, road_options
from app.data.ntta_rates import find_toll_points, toll_points, unknown_rate
from app.persistence.budget_repository import get_budget_repository
from app.persistence.optimization_repository import save_optimization_run, write_memory_probe
from app.persistence.trip_repository import get_trip_repository
from app.services.budget_engine import evaluate_budget
from app.services.commute_planner import build_commute_plan
from app.services.explanation_service import generate_explanation
from app.services.tollio_brain import (
    BrainProfile,
    PathSegment,
    entryVScore,
    exitVScore,
    findPaths,
    getPrice,
    getServiceRoadTime,
    matrix_brain_roads,
    projectAnnualSaving,
    serviceRoadGasCost,
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


@router.get("/api/v1/demo/gemini-invocation")
def demo_gemini_invocation() -> dict:
    status = get_system_status()
    sample_plan = build_commute_plan(
        CommutePlanRequest(
            origin="Frisco",
            destination="Downtown Dallas",
            arrival_time="08:30",
            urgency_mode=UrgencyMode.balanced,
            daily_budget=8,
            weekly_budget=40,
            monthly_budget=160,
            budget_period=BudgetPeriod.daily,
            toll_pass_type="NTTA TollTag",
            vehicle_mpg=28,
            gas_price=3.25,
            avoid_excessive_signals=True,
        )
    )
    explanation = generate_explanation(sample_plan)
    gemini_invoked = explanation.data_source == "live_gemini"
    return {
        "mode": status.agent_mode,
        "gemini_configured": status.gemini_ready,
        "invocation_path": {
            "endpoint": "/api/v1/demo/gemini-invocation",
            "service": "services/api/app/services/explanation_service.py",
            "live_gate": "TOLLIO_AGENT_MODE=live and GEMINI_API_KEY present",
            "gemini_invoked": gemini_invoked,
            "data_source": explanation.data_source,
            "live_error": explanation.live_error,
        },
        "sample_explanation": {
            "short_explanation": explanation.short_explanation,
            "driver_friendly_summary": explanation.driver_friendly_summary,
            "caution_notes": explanation.caution_notes,
        },
        "status": "live_gemini_invoked" if gemini_invoked else "mock_explanation_returned",
    }


@router.get("/api/v1/demo/mongodb-invocation")
def demo_mongodb_invocation() -> dict:
    status = get_system_status()
    source = matrix_data_source()
    roads = road_options()
    memory_write = write_memory_probe()
    mongodb_ready = status.mongodb_ready and source == "mongodb"
    return {
        "mongodb_mode": status.mongodb_mode,
        "mongodb_ready": mongodb_ready,
        "ntta_source": source,
        "collections_checked": ["ntta_matrices", "optimization_runs"],
        "sample_road_count": len(roads),
        "memory_write_test": memory_write,
        "status": "mongodb_runtime_ready" if mongodb_ready else "local_json_or_mongodb_unavailable",
    }


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
    return {"roads": road_options(), "source_metadata": {"data_source": matrix_data_source()}}


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
            "data_source": matrix_data_source(),
        },
    }


@router.post("/api/v1/optimize/entry-exit")
def optimize_entry_exit(request: dict) -> dict:
    from_road_name = str(request.get("from_road") or request.get("road") or "")
    to_road_name = str(request.get("to_road") or request.get("road") or from_road_name)
    from_exit = str(request.get("from_exit", ""))
    to_exit = str(request.get("to_exit", ""))
    payment = str(request.get("payment", "tolltag"))
    if payment not in {"tolltag", "zipcash"}:
        raise HTTPException(status_code=422, detail="payment must be tolltag or zipcash")

    matched_from_road = find_road(from_road_name)
    matched_to_road = find_road(to_road_name)
    if matched_from_road is None:
        raise HTTPException(status_code=404, detail=f"Unknown NTTA road: {from_road_name}")
    if matched_to_road is None:
        raise HTTPException(status_code=404, detail=f"Unknown NTTA road: {to_road_name}")
    from_index = find_exit_index(matched_from_road, from_exit)
    to_index = find_exit_index(matched_to_road, to_exit)
    if from_index is None or to_index is None:
        raise HTTPException(status_code=404, detail="Unknown NTTA from/to exit for selected road")

    profile = BrainProfile(
        toll_payment=payment,
        mpg=float(request.get("mpg", 28) or 28),
        gas_price=float(request.get("gas_price", 3.25) or 3.25),
        vehicle_type=str(request.get("vehicle_type", "gas")),
        traffic_mode=str(request.get("traffic_mode", "offpeak")),
    )
    all_candidates = _candidate_options(
        matched_from_road,
        from_index,
        matched_to_road,
        to_index,
        profile,
        request,
    )
    if not all_candidates:
        raise HTTPException(status_code=404, detail="No matrix candidates found for selected road/exits")
    ranked_options = sorted(all_candidates, key=_candidate_sort_key)
    natural_route = next(item for item in all_candidates if item["label"] == "Natural Route")
    optimized_route = ranked_options[0]
    recommendation = _recommendation_from_candidate(optimized_route, natural_route)
    source_metadata = _source_metadata(matched_from_road)
    memory_write = save_optimization_run(request, optimized_route, ranked_options, source_metadata)
    return {
        "natural_route": natural_route,
        "optimized_route": optimized_route,
        "best_recommendation": optimized_route,
        "ranked_options": ranked_options,
        "all_candidates": all_candidates,
        "explanation": optimized_route["explanation"],
        "recommendation": recommendation,
        "source_metadata": source_metadata,
        "optimization_memory": memory_write,
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


def _candidate_options(from_road, from_index: int, to_road, to_index: int, profile: BrainProfile, request: dict) -> list[dict]:
    brain_roads = matrix_brain_roads()
    paths = findPaths(from_road.road_id, from_index, to_road.road_id, to_index)
    if not paths:
        return []
    natural_path = paths[0]
    natural = _candidate_for_path("Natural Route", natural_path, natural_path, profile, request)
    if natural is None:
        return []

    pool = []
    for path in paths:
        for candidate_path in _candidate_paths_for_natural_path(path):
            candidate = _candidate_for_path("Candidate", candidate_path, natural_path, profile, request)
            if candidate is None or _reject_candidate(candidate):
                continue
            pool.append(candidate)

    non_natural = [candidate for candidate in pool if not _same_path(candidate, natural)]
    best_value = _best_by(non_natural, key=_candidate_sort_key)
    cheapest = _best_by(non_natural, key=lambda item: (item["toll_cost"], item["added_minutes"], -item["value_score"]))
    fastest = _best_by(pool, key=lambda item: (item["added_minutes"], -item["net_savings"], -item["value_score"]))

    labeled = [natural]
    for label, candidate in [
        ("Best Value Route", best_value),
        ("Cheapest Route", cheapest),
        ("Fastest Compatible Route", fastest),
    ]:
        if candidate is not None:
            labeled.append(_with_label(candidate, label, natural))
    return _unique_user_options(labeled)


def _candidate_for_path(label: str, path: list[PathSegment], natural_path: list[PathSegment], profile: BrainProfile, request: dict):
    natural_price = _path_price(natural_path, profile)
    price = _path_price(path, profile)
    if price is None or natural_price is None:
        return None

    first = path[0]
    last = path[-1]
    natural_first = natural_path[0]
    natural_last = natural_path[-1]
    first_road = _brain_road(first.road)
    last_road = _brain_road(last.road)
    natural_first_road = _brain_road(natural_first.road)
    natural_last_road = _brain_road(natural_last.road)

    entry_detour = abs(first.entry - natural_first.entry)
    exit_detour = abs(natural_last.exit - last.exit)
    entry_service = getServiceRoadTime(entry_detour, profile.traffic_mode)
    exit_service = getServiceRoadTime(exit_detour, profile.traffic_mode)
    service_road_minutes = entry_service.minutes + exit_service.minutes
    service_road_miles = round(entry_service.miles + exit_service.miles, 2)
    gas_cost = serviceRoadGasCost(service_road_miles, profile.mpg, profile.gas_price, profile.vehicle_type)
    toll_saved = round(natural_price - price, 2)
    net_savings = round(toll_saved - gas_cost, 2)

    entry_score = entryVScore(first_road, first.entry, first.exit, profile.toll_payment)
    exit_score = exitVScore(last_road, last.entry, last.exit, profile.toll_payment)
    natural_entry_score = entryVScore(natural_first_road, natural_first.entry, natural_first.exit, profile.toll_payment)
    natural_exit_score = exitVScore(natural_last_road, natural_last.entry, natural_last.exit, profile.toll_payment)
    value_score = _path_value_score(path, profile)
    natural_value_score = _path_value_score(natural_path, profile)
    wasted = wastedBehind(first_road, first.entry, first.exit, profile.toll_payment)
    unused = unusedAhead(last_road, last.entry, last.exit, profile.toll_payment)
    natural_wasted = wastedBehind(natural_first_road, natural_first.entry, natural_first.exit, profile.toll_payment)
    natural_unused = unusedAhead(natural_last_road, natural_last.entry, natural_last.exit, profile.toll_payment)
    cost_per_minute_saved = None if service_road_minutes == 0 else round(toll_saved / service_road_minutes, 2)
    budget_impact = _budget_impact(price, request)
    confidence = _confidence(price, natural_price, net_savings, service_road_minutes)
    metrics = {
        "entry_value_score": entry_score,
        "exit_value_score": exit_score,
        "natural_entry_value_score": natural_entry_score,
        "natural_exit_value_score": natural_exit_score,
        "value_score": value_score,
        "natural_value_score": natural_value_score,
        "utilization_improvement": value_score - natural_value_score,
        "wasted_behind": wasted,
        "natural_wasted_behind": natural_wasted,
        "unused_ahead": unused,
        "natural_unused_ahead": natural_unused,
        "cost_per_minute_saved": cost_per_minute_saved,
        "budget_impact": budget_impact,
        "driver_simplicity": _simplicity_score(entry_detour, exit_detour, service_road_minutes),
        "confidence_rank": _confidence_rank(confidence),
    }
    route_path_label = _path_label(path)
    explanation = _candidate_explanation(
        first_road,
        last_road,
        natural_first.entry,
        natural_last.exit,
        first.entry,
        last.exit,
        toll_saved,
        net_savings,
        gas_cost,
        service_road_minutes,
        metrics,
    )
    return {
        "label": label,
        "route_path_label": route_path_label,
        "entry": first_road.exits[first.entry],
        "exit": last_road.exits[last.exit],
        "entry_instruction": f"Enter {first_road.short} at {first_road.exits[first.entry]}",
        "exit_instruction": f"Exit {last_road.short} at {last_road.exits[last.exit]}",
        "toll_cost": round(price, 2),
        "toll_price": round(price, 2),
        "natural_toll_cost": round(natural_price, 2),
        "natural_price": round(natural_price, 2),
        "toll_saved": toll_saved,
        "net_savings": net_savings,
        "net_saving": net_savings,
        "added_minutes": service_road_minutes,
        "service_road_minutes": service_road_minutes,
        "service_road_miles": service_road_miles,
        "gas_cost": gas_cost,
        "value_score": value_score,
        "entry_value_score": entry_score,
        "exit_value_score": exit_score,
        "combined_value_score": value_score,
        "wasted_behind": wasted,
        "unused_ahead": unused,
        "confidence": confidence,
        "why": explanation,
        "explanation": explanation,
        "recommendation_label": label,
        "plain_english_reason": explanation,
        "metrics": metrics,
        "segments": [_segment_payload(segment, profile) for segment in path],
    }


def _candidate_paths_for_natural_path(path: list[PathSegment]) -> list[list[PathSegment]]:
    first = path[0]
    last = path[-1]
    entry_candidates = _points_between(first.entry, first.exit)[:-1]
    exit_candidates = _points_between(last.entry, last.exit)[1:]
    candidates = []
    for entry in entry_candidates:
        for exit_idx in exit_candidates:
            adjusted = list(path)
            adjusted[0] = PathSegment(
                road=first.road,
                entry=entry,
                exit=first.exit,
                connector=first.connector,
                connector_type=first.connector_type,
            )
            adjusted[-1] = PathSegment(
                road=last.road,
                entry=last.entry if len(path) > 1 else entry,
                exit=exit_idx,
                connector=last.connector,
                connector_type=last.connector_type,
            )
            if _valid_candidate_path(adjusted):
                candidates.append(adjusted)
    return candidates


def _points_between(start: int, end: int) -> list[int]:
    direction = 1 if end >= start else -1
    return list(range(start, end + direction, direction))


def _valid_candidate_path(path: list[PathSegment]) -> bool:
    for segment in path:
        points = _points_between(segment.entry, segment.exit)
        if len(points) < 2:
            return False
    return True


def _path_price(path: list[PathSegment], profile: BrainProfile):
    total = 0.0
    for segment in path:
        price = getPrice(_brain_road(segment.road), segment.entry, segment.exit, profile.toll_payment)
        if price is None:
            return None
        total += price
    return round(total, 2)


def _path_value_score(path: list[PathSegment], profile: BrainProfile) -> int:
    scores = [
        vScore(_brain_road(segment.road), segment.entry, segment.exit, profile.toll_payment)
        for segment in path
    ]
    return round(sum(scores) / max(len(scores), 1))


def _path_label(path: list[PathSegment]) -> str:
    return " -> ".join(dict.fromkeys(_brain_road(segment.road).short for segment in path))


def _segment_payload(segment: PathSegment, profile: BrainProfile) -> dict:
    road = _brain_road(segment.road)
    return {
        "road": road.short,
        "entry": road.exits[segment.entry],
        "exit": road.exits[segment.exit],
        "connector": segment.connector,
        "connector_type": segment.connector_type,
        "toll_cost": getPrice(road, segment.entry, segment.exit, profile.toll_payment),
    }


def _candidate_explanation(
    entry_road,
    exit_road,
    natural_entry: int,
    natural_exit: int,
    entry_index: int,
    exit_index: int,
    toll_saved: float,
    net_savings: float,
    gas_cost: float,
    added_minutes: int,
    metrics: dict,
) -> str:
    if entry_index == natural_entry and exit_index == natural_exit:
        return "This is the natural route from the selected NTTA matrix entry and exit."

    parts = []
    attributed = False
    if entry_index != natural_entry:
        if (
            metrics["value_score"] >= metrics["natural_value_score"]
            and
            metrics["wasted_behind"] < metrics["natural_wasted_behind"]
            and metrics["entry_value_score"] > metrics["natural_entry_value_score"]
        ):
            parts.append(
                f"Entering at {entry_road.exits[entry_index]} instead of {entry_road.exits[natural_entry]} improves entry utilization."
            )
            attributed = True
        elif (
            metrics["value_score"] >= metrics["natural_value_score"]
            and metrics["entry_value_score"] > metrics["natural_entry_value_score"]
        ):
            parts.append(f"Entering at {entry_road.exits[entry_index]} improves the entry value score.")
            attributed = True
    if exit_index != natural_exit:
        if (
            metrics["value_score"] >= metrics["natural_value_score"]
            and
            metrics["unused_ahead"] < metrics["natural_unused_ahead"]
            and metrics["exit_value_score"] > metrics["natural_exit_value_score"]
        ):
            parts.append(
                f"Exiting at {exit_road.exits[exit_index]} instead of {exit_road.exits[natural_exit]} reduces unused paid distance ahead."
            )
            attributed = True
        elif (
            metrics["value_score"] >= metrics["natural_value_score"]
            and metrics["exit_value_score"] > metrics["natural_exit_value_score"]
        ):
            parts.append(f"Exiting at {exit_road.exits[exit_index]} improves the exit value score.")
            attributed = True
    if toll_saved > 0 and metrics["value_score"] < metrics["natural_value_score"]:
        parts.append(
            f"Recommended because it saves ${net_savings:.2f} net with {added_minutes} extra minutes, even though utilization score is lower."
        )
        attributed = True
    if toll_saved > 0 and not attributed:
        parts.append(
            "The matrix price is lower for this entry/exit combination, but the current utilization metrics do not attribute the savings to wasted-behind or unused-ahead segments."
        )
    if toll_saved > 0:
        parts.append(
            f"It saves ${toll_saved:.2f} in tolls, uses ${gas_cost:.2f} in gas, and nets ${net_savings:.2f} with {added_minutes} extra minutes."
        )
    if not parts:
        parts.append("This option is valid, but it does not improve the current toll utilization or savings metrics.")
    return " ".join(parts)


def _reject_candidate(candidate: dict) -> bool:
    if candidate["label"] == "Natural Route":
        return False
    if candidate["net_savings"] < 0.25 and candidate["added_minutes"] > 5:
        return True
    if candidate["added_minutes"] > 10 and candidate["net_savings"] < 2.0:
        return True
    return False


def _candidate_sort_key(candidate: dict) -> tuple:
    metrics = candidate["metrics"]
    return (
        -metrics["confidence_rank"],
        -candidate["net_savings"],
        -metrics["utilization_improvement"],
        candidate["added_minutes"],
        -_budget_score(metrics["budget_impact"]),
        -metrics["driver_simplicity"],
    )


def _with_label(candidate: dict, label: str, natural: dict) -> dict:
    relabeled = {**candidate, "label": label, "recommendation_label": label}
    relabeled["explanation"] = _candidate_explanation_from_metrics(relabeled, natural)
    relabeled["why"] = relabeled["explanation"]
    relabeled["plain_english_reason"] = relabeled["explanation"]
    return relabeled


def _candidate_explanation_from_metrics(candidate: dict, natural: dict) -> str:
    if candidate["entry"] == natural["entry"] and candidate["exit"] == natural["exit"]:
        return "This is the fastest compatible option because it stays with the selected natural entry and exit."
    return candidate["explanation"]


def _best_by(candidates: list[dict], key):
    if not candidates:
        return None
    return sorted(candidates, key=key)[0]


def _same_path(left: dict, right: dict) -> bool:
    return (
        left["route_path_label"] == right["route_path_label"]
        and left["entry"] == right["entry"]
        and left["exit"] == right["exit"]
    )


def _unique_user_options(candidates: list[dict]) -> list[dict]:
    unique = []
    seen_labels = set()
    for candidate in candidates:
        if candidate["label"] in seen_labels:
            continue
        unique.append(candidate)
        seen_labels.add(candidate["label"])
    return unique[:4]


def _confidence(price: float, natural_price: float, net_savings: float, added_minutes: int) -> str:
    if price is None or natural_price is None:
        return "unknown"
    if net_savings >= 0.5 and added_minutes <= 6:
        return "high"
    if net_savings >= 0:
        return "medium"
    return "low"


def _confidence_rank(confidence: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(confidence, 0)


def _budget_impact(toll_cost: float, request: dict) -> str:
    budget = request.get("budget_amount") or request.get("daily_budget")
    if budget is None:
        return "unknown"
    try:
        budget_value = float(budget)
    except (TypeError, ValueError):
        return "unknown"
    if toll_cost <= budget_value * 0.5:
        return "comfortable"
    if toll_cost <= budget_value:
        return "within_budget"
    return "over_budget"


def _budget_score(impact: str) -> int:
    return {"comfortable": 3, "within_budget": 2, "unknown": 1, "over_budget": 0}.get(impact, 0)


def _simplicity_score(entry_detour: int, exit_detour: int, added_minutes: int) -> int:
    changes = int(entry_detour > 0) + int(exit_detour > 0)
    return max(0, 100 - changes * 15 - added_minutes * 4)


def _recommendation_from_candidate(candidate: dict, natural: dict) -> dict:
    return {
        "natural_entry": natural["entry"],
        "better_entry": candidate["entry"],
        "natural_exit": natural["exit"],
        "better_exit": candidate["exit"],
        "toll_saved": candidate["toll_saved"],
        "gas_cost": candidate["gas_cost"],
        "net_saving": candidate["net_savings"],
        "extra_time_minutes": candidate["added_minutes"],
        "natural_value_score": natural["value_score"],
        "optimized_value_score": candidate["value_score"],
        "annual_saving_projection": projectAnnualSaving(candidate["net_savings"]),
        "plain_english_reason": candidate["explanation"],
    }


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
        "data_source": matrix_data_source(),
    }


def _brain_road_from_matrix(road):
    from app.services.tollio_brain import matrix_brain_roads

    for item in matrix_brain_roads():
        if item.id == road.road_id:
            return item
    raise HTTPException(status_code=404, detail=f"Unknown NTTA road: {road.road_name}")


def _brain_road(road_id: int):
    for item in matrix_brain_roads():
        if item.id == road_id:
            return item
    raise HTTPException(status_code=404, detail=f"Unknown NTTA road id: {road_id}")
