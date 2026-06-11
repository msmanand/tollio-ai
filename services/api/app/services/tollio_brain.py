from dataclasses import dataclass
from functools import cmp_to_key
from typing import Dict, List, Optional, Tuple

from app.data.ntta_matrix import NTTAMatrixRoad, find_exit_index, find_road, load_matrix_roads
from app.data.ntta_rates import NTTARateEntry


TrafficMode = str
TollPayment = str


@dataclass(frozen=True)
class BrainRoad:
    id: int
    short: str
    name: str
    exits: List[str]
    matrix: Optional[Dict[Tuple[int, int], Optional[float]]] = None
    tolltag_matrix: Optional[Dict[Tuple[int, int], Optional[float]]] = None
    zipcash_matrix: Optional[Dict[Tuple[int, int], Optional[float]]] = None
    toll_points_by_exit: Optional[Dict[int, NTTARateEntry]] = None


@dataclass(frozen=True)
class BrainProfile:
    toll_payment: TollPayment = "tolltag"
    mpg: float = 28.0
    vehicle_type: str = "gas"
    gas_price: float = 3.25
    traffic_mode: TrafficMode = "offpeak"


@dataclass(frozen=True)
class PathSegment:
    road: int
    entry: int
    exit: int
    connector: Optional[str] = None
    connector_type: Optional[str] = None


@dataclass(frozen=True)
class RoadConnection:
    from_road: int
    from_exit: int
    to_road: int
    to_entry: int
    via_name: str
    via: str


@dataclass(frozen=True)
class EntryOption:
    exit_idx: int
    exit_name: str
    price: float
    score: int
    svc_mins: int
    svc_miles: float
    gas_cost: float
    saving: float
    is_gantry_start: bool
    is_gap: bool
    wasted: int
    is_natural: bool


@dataclass(frozen=True)
class ExitOption:
    exit_idx: int
    exit_name: str
    price: float
    score: int
    svc_mins: int
    svc_miles: float
    gas_cost: float
    saving: float
    is_tier_end: bool
    is_gap: bool
    unused: int
    is_natural: bool


@dataclass(frozen=True)
class EntryAnalysis:
    natural: EntryOption
    suggestion: Optional[EntryOption]


@dataclass(frozen=True)
class ExitAnalysis:
    natural: ExitOption
    suggestion: Optional[ExitOption]


@dataclass(frozen=True)
class SegmentResult:
    road: int
    road_name: str
    road_short: str
    natural_entry: int
    natural_exit: int
    natural_price: float
    used_entry: EntryOption
    used_exit: ExitOption
    entry_analysis: EntryAnalysis
    exit_analysis: ExitAnalysis
    price: float
    value_score: int
    toll_mins: int
    connector: Optional[str]
    connector_type: Optional[str]
    connection_fully_used: Optional[bool]


@dataclass(frozen=True)
class OptimizationResult:
    segments: List[SegmentResult]
    label: str
    total_price: float
    natural_total: float
    toll_saved: float
    total_svc_mins: int
    total_svc_miles: float
    gas_cost: float
    net_saving: float
    avg_value_score: int
    is_best: bool = False


@dataclass(frozen=True)
class ServiceRoadResult:
    minutes: int
    miles: float


def getPrice(road: BrainRoad, a: int, b: int, payment: TollPayment = "tolltag") -> Optional[float]:
    if a == b:
        return 0.0
    if road.tolltag_matrix is not None and road.zipcash_matrix is not None:
        table = road.tolltag_matrix if payment == "tolltag" else road.zipcash_matrix
        pair = _pair(a, b)
        if pair not in table:
            return None
        value = table[pair]
        return 0.0 if value is None else round(float(value), 2)
    if road.matrix is not None:
        pair = _pair(a, b)
        if pair not in road.matrix:
            return None
        value = road.matrix[pair]
        return 0.0 if value is None else round(float(value), 2)
    if road.toll_points_by_exit is None:
        return None

    start, end = sorted((a, b))
    crossed = [
        rate
        for exit_idx, rate in road.toll_points_by_exit.items()
        if start < exit_idx <= end
    ]
    if not crossed:
        return None
    total = 0.0
    for rate in crossed:
        value = rate.tolltag_rate if payment == "tolltag" else rate.zipcash_rate
        if value is None:
            return None
        total += value
    return round(total, 2)


def findPaths(fromRoad: int, fromExit: int, toRoad: int, toExit: int) -> List[List[PathSegment]]:
    if fromRoad == toRoad:
        return [[PathSegment(road=fromRoad, entry=fromExit, exit=toExit)]]
    paths = []
    for connection in _connections():
        if connection.from_road == fromRoad and connection.to_road == toRoad:
            paths.append(
                [
                    PathSegment(
                        road=fromRoad,
                        entry=fromExit,
                        exit=connection.from_exit,
                        connector=connection.via_name,
                        connector_type=connection.via,
                    ),
                    PathSegment(road=toRoad, entry=connection.to_entry, exit=toExit),
                ]
            )
    for first in _connections():
        if first.from_road != fromRoad:
            continue
        for second in _connections():
            if second.from_road == first.to_road and second.to_road == toRoad:
                paths.append(
                    [
                        PathSegment(
                            road=fromRoad,
                            entry=fromExit,
                            exit=first.from_exit,
                            connector=first.via_name,
                            connector_type=first.via,
                        ),
                        PathSegment(
                            road=first.to_road,
                            entry=first.to_entry,
                            exit=second.from_exit,
                            connector=second.via_name,
                            connector_type=second.via,
                        ),
                        PathSegment(road=toRoad, entry=second.to_entry, exit=toExit),
                    ]
                )
    return paths


def entryVScore(road: BrainRoad, entryIdx: int, destIdx: int, payment: TollPayment = "tolltag") -> int:
    price = getPrice(road, entryIdx, destIdx, payment)
    if price is None or price == 0:
        return 100
    direction = _direction(entryIdx, destIdx)
    tier_start = entryIdx
    probe = entryIdx - direction
    while _valid_exit(road, probe) and getPrice(road, probe, destIdx, payment) == price:
        tier_start = probe
        probe -= direction
    exits_paid_for = max(abs(destIdx - tier_start), 1)
    exits_used = max(abs(destIdx - entryIdx), 1)
    return _score(exits_used, exits_paid_for)


def exitVScore(road: BrainRoad, entryIdx: int, exitIdx: int, payment: TollPayment = "tolltag") -> int:
    price = getPrice(road, entryIdx, exitIdx, payment)
    if price is None or price == 0:
        return 100
    direction = _direction(entryIdx, exitIdx)
    tier_end = exitIdx
    probe = exitIdx + direction
    while _valid_exit(road, probe) and getPrice(road, entryIdx, probe, payment) == price:
        tier_end = probe
        probe += direction
    exits_paid_for = max(abs(tier_end - entryIdx), 1)
    exits_used = max(abs(exitIdx - entryIdx), 1)
    return _score(exits_used, exits_paid_for)


def vScore(road: BrainRoad, entryIdx: int, exitIdx: int, payment: TollPayment = "tolltag") -> int:
    return min(
        entryVScore(road, entryIdx, exitIdx, payment),
        exitVScore(road, entryIdx, exitIdx, payment),
    )


def isGantryStart(road: BrainRoad, exitIdx: int, destIdx: int, payment: TollPayment = "tolltag") -> bool:
    direction = _direction(exitIdx, destIdx)
    before = exitIdx - direction
    if not _valid_exit(road, before):
        return True
    price = getPrice(road, exitIdx, destIdx, payment)
    price_before = getPrice(road, before, destIdx, payment)
    if price is None or price_before is None:
        return False
    return price_before > price + 0.01


def isTierEnd(road: BrainRoad, entryIdx: int, exitIdx: int, payment: TollPayment = "tolltag") -> bool:
    direction = _direction(entryIdx, exitIdx)
    after = exitIdx + direction
    if not _valid_exit(road, after):
        return True
    price = getPrice(road, entryIdx, exitIdx, payment)
    price_after = getPrice(road, entryIdx, after, payment)
    if price is None or price_after is None:
        return False
    return price_after > price + 0.01


def wastedBehind(road: BrainRoad, entryIdx: int, destIdx: int, payment: TollPayment = "tolltag") -> int:
    price = getPrice(road, entryIdx, destIdx, payment)
    if price is None:
        return 0
    direction = _direction(entryIdx, destIdx)
    count = 0
    probe = entryIdx - direction
    while _valid_exit(road, probe) and getPrice(road, probe, destIdx, payment) == price:
        count += 1
        probe -= direction
    return count


def unusedAhead(road: BrainRoad, entryIdx: int, exitIdx: int, payment: TollPayment = "tolltag") -> int:
    price = getPrice(road, entryIdx, exitIdx, payment)
    if price is None:
        return 0
    direction = _direction(entryIdx, exitIdx)
    count = 0
    probe = exitIdx + direction
    while _valid_exit(road, probe) and getPrice(road, entryIdx, probe, payment) == price:
        count += 1
        probe += direction
    return count


def getServiceRoadTime(numExits: int, mode: TrafficMode) -> ServiceRoadResult:
    minutes_per_exit = {"rush": 3.0, "offpeak": 2.0, "night": 1.0}.get(mode, 2.0)
    return ServiceRoadResult(
        minutes=round(abs(numExits) * minutes_per_exit),
        miles=round(abs(numExits) * 0.9, 2),
    )


def getTollRoadTime(numExits: int, mode: TrafficMode) -> int:
    minutes_per_exit = {"rush": 2.0, "offpeak": 1.2, "night": 0.8}.get(mode, 1.2)
    return round(abs(numExits) * minutes_per_exit)


def serviceRoadGasCost(miles: float, mpg: float, gasPrice: float, vehicleType: str) -> float:
    if vehicleType == "ev" or mpg <= 0:
        return 0.0
    return round((miles / mpg) * gasPrice, 2)


def analyzeEntry(
    roadIdx: int,
    naturalEntry: int,
    destIdx: int,
    profile: BrainProfile,
    roads: Optional[List[BrainRoad]] = None,
) -> EntryAnalysis:
    road = _road(roadIdx, roads)
    payment = profile.toll_payment
    natural_price = _known_price(road, naturalEntry, destIdx, payment)
    natural = EntryOption(
        exit_idx=naturalEntry,
        exit_name=road.exits[naturalEntry],
        price=natural_price,
        score=entryVScore(road, naturalEntry, destIdx, payment),
        svc_mins=0,
        svc_miles=0.0,
        gas_cost=0.0,
        saving=0.0,
        is_gantry_start=isGantryStart(road, naturalEntry, destIdx, payment),
        is_gap=False,
        wasted=wastedBehind(road, naturalEntry, destIdx, payment),
        is_natural=True,
    )
    suggestion = None
    direction = _direction(naturalEntry, destIdx)
    for i in range(naturalEntry + direction, destIdx, direction):
        p = getPrice(road, i, destIdx, payment)
        p_before = getPrice(road, i - direction, destIdx, payment)
        if p is None or p_before is None:
            continue
        is_gap = _is_free_gap(road, i - direction, i, payment)
        is_new_tier = p_before > p + 0.01
        if (is_new_tier or is_gap) and p < natural_price - 0.01:
            svc = getServiceRoadTime(abs(i - naturalEntry), profile.traffic_mode)
            gas = serviceRoadGasCost(svc.miles, profile.mpg, profile.gas_price, profile.vehicle_type)
            suggestion = EntryOption(
                exit_idx=i,
                exit_name=road.exits[i],
                price=round(p, 2),
                score=entryVScore(road, i, destIdx, payment),
                svc_mins=svc.minutes,
                svc_miles=svc.miles,
                gas_cost=gas,
                saving=round(natural_price - p, 2),
                is_gantry_start=is_new_tier,
                is_gap=is_gap,
                wasted=wastedBehind(road, i, destIdx, payment),
                is_natural=False,
            )
            break
        if p == 0:
            break
    return EntryAnalysis(natural=natural, suggestion=suggestion)


def analyzeExit(
    roadIdx: int,
    entryIdx: int,
    naturalExit: int,
    profile: BrainProfile,
    roads: Optional[List[BrainRoad]] = None,
) -> ExitAnalysis:
    road = _road(roadIdx, roads)
    payment = profile.toll_payment
    natural_price = _known_price(road, entryIdx, naturalExit, payment)
    natural = ExitOption(
        exit_idx=naturalExit,
        exit_name=road.exits[naturalExit],
        price=natural_price,
        score=exitVScore(road, entryIdx, naturalExit, payment),
        svc_mins=0,
        svc_miles=0.0,
        gas_cost=0.0,
        saving=0.0,
        is_tier_end=isTierEnd(road, entryIdx, naturalExit, payment),
        is_gap=False,
        unused=unusedAhead(road, entryIdx, naturalExit, payment),
        is_natural=True,
    )
    suggestion = None
    direction = _direction(entryIdx, naturalExit)
    for i in range(naturalExit - direction, entryIdx, -direction):
        p = getPrice(road, entryIdx, i, payment)
        p_after = getPrice(road, entryIdx, i + direction, payment)
        if p is None or p_after is None:
            continue
        is_gap = _is_free_gap(road, i, i + direction, payment)
        is_tier_end = p_after > p + 0.01
        if (is_tier_end or is_gap) and p < natural_price - 0.01:
            svc = getServiceRoadTime(abs(naturalExit - i), profile.traffic_mode)
            gas = serviceRoadGasCost(svc.miles, profile.mpg, profile.gas_price, profile.vehicle_type)
            suggestion = ExitOption(
                exit_idx=i,
                exit_name=road.exits[i],
                price=round(p, 2),
                score=exitVScore(road, entryIdx, i, payment),
                svc_mins=svc.minutes,
                svc_miles=svc.miles,
                gas_cost=gas,
                saving=round(natural_price - p, 2),
                is_tier_end=is_tier_end,
                is_gap=is_gap,
                unused=unusedAhead(road, entryIdx, i, payment),
                is_natural=False,
            )
            break
    return ExitAnalysis(natural=natural, suggestion=suggestion)


def optimizeTrip(
    fromRoad: int,
    fromExit: int,
    toRoad: int,
    toExit: int,
    profile: BrainProfile,
    roads: Optional[List[BrainRoad]] = None,
) -> List[OptimizationResult]:
    active_roads = roads or OFFICIAL_ROADS
    paths = findPaths(fromRoad, fromExit, toRoad, toExit)
    results = []
    for path in paths:
        segments = []
        for index, seg in enumerate(path):
            is_first = index == 0
            is_last = index == len(path) - 1
            road = _road(seg.road, active_roads)
            if is_first:
                entry_analysis = analyzeEntry(seg.road, seg.entry, seg.exit, profile, active_roads)
            else:
                entry_analysis = _synthetic_entry(road, seg.entry)
            used_entry = entry_analysis.suggestion or entry_analysis.natural

            if is_last:
                exit_analysis = analyzeExit(seg.road, used_entry.exit_idx, seg.exit, profile, active_roads)
            else:
                exit_analysis = _synthetic_exit(road, seg.exit)
            used_exit = exit_analysis.suggestion or exit_analysis.natural

            price = _known_price(road, used_entry.exit_idx, used_exit.exit_idx, profile.toll_payment)
            natural_price = _known_price(road, seg.entry, seg.exit, profile.toll_payment)
            score = vScore(road, used_entry.exit_idx, used_exit.exit_idx, profile.toll_payment)
            toll_mins = getTollRoadTime(abs(used_exit.exit_idx - used_entry.exit_idx), profile.traffic_mode)
            connection_fully_used = None
            if seg.connector:
                connection_fully_used = isTierEnd(road, used_entry.exit_idx, used_exit.exit_idx, profile.toll_payment)
            segments.append(
                SegmentResult(
                    road=seg.road,
                    road_name=road.name,
                    road_short=road.short,
                    natural_entry=seg.entry,
                    natural_exit=seg.exit,
                    natural_price=natural_price,
                    used_entry=used_entry,
                    used_exit=used_exit,
                    entry_analysis=entry_analysis,
                    exit_analysis=exit_analysis,
                    price=price,
                    value_score=score,
                    toll_mins=toll_mins,
                    connector=seg.connector,
                    connector_type=seg.connector_type,
                    connection_fully_used=connection_fully_used,
                )
            )
        total_price = round(sum(segment.price for segment in segments), 2)
        natural_total = round(sum(segment.natural_price for segment in segments), 2)
        toll_saved = round(natural_total - total_price, 2)
        total_svc_mins = sum(segment.used_entry.svc_mins + segment.used_exit.svc_mins for segment in segments)
        total_svc_miles = round(
            sum(segment.used_entry.svc_miles + segment.used_exit.svc_miles for segment in segments),
            2,
        )
        gas_cost = round(sum(segment.used_entry.gas_cost + segment.used_exit.gas_cost for segment in segments), 2)
        net_saving = round(toll_saved - gas_cost, 2)
        avg_value_score = round(sum(segment.value_score for segment in segments) / max(len(segments), 1))
        label = " -> ".join(dict.fromkeys(segment.road_short for segment in segments))
        results.append(
            OptimizationResult(
                segments=segments,
                label=label,
                total_price=total_price,
                natural_total=natural_total,
                toll_saved=toll_saved,
                total_svc_mins=total_svc_mins,
                total_svc_miles=total_svc_miles,
                gas_cost=gas_cost,
                net_saving=net_saving,
                avg_value_score=avg_value_score,
            )
        )
    results.sort(key=cmp_to_key(_rank_results))
    if results:
        best = results[0]
        results[0] = OptimizationResult(**{**best.__dict__, "is_best": True})
    return results


def projectAnnualSaving(netSavingPerTrip: float, tripsPerDay: int = 2, workdaysPerYear: int = 220) -> float:
    return round(netSavingPerTrip * tripsPerDay * workdaysPerYear, 2)


def _rank_results(left: OptimizationResult, right: OptimizationResult) -> int:
    if abs(left.avg_value_score - right.avg_value_score) > 5:
        return right.avg_value_score - left.avg_value_score
    if left.total_price < right.total_price:
        return -1
    if left.total_price > right.total_price:
        return 1
    return 0


def optimize_trip_by_names(
    origin: str,
    destination: str,
    profile: BrainProfile,
) -> List[OptimizationResult]:
    origin_match = find_exit(origin)
    destination_match = find_exit(destination)
    if origin_match is None or destination_match is None:
        return []
    from_road, from_exit = origin_match
    to_road, to_exit = destination_match
    return optimizeTrip(from_road, from_exit, to_road, to_exit, profile)


def optimize_trip_by_matrix_names(
    road_name: str,
    from_exit: str,
    to_exit: str,
    profile: BrainProfile,
) -> List[OptimizationResult]:
    road = find_road(road_name)
    if road is None:
        return []
    from_index = find_exit_index(road, from_exit)
    to_index = find_exit_index(road, to_exit)
    if from_index is None or to_index is None:
        return []
    roads = matrix_brain_roads()
    return optimizeTrip(road.road_id, from_index, road.road_id, to_index, profile, roads)


def find_exit(name: str) -> Optional[Tuple[int, int]]:
    normalized = _normalize(name)
    for road in matrix_brain_roads():
        for index, exit_name in enumerate(road.exits):
            if normalized == _normalize(exit_name) or normalized in _normalize(exit_name):
                return road.id, index
    for alias, target in EXIT_ALIASES.items():
        if normalized == _normalize(alias):
            return target
    return None


def _synthetic_entry(road: BrainRoad, entry: int) -> EntryAnalysis:
    option = EntryOption(entry, road.exits[entry], 0.0, 100, 0, 0.0, 0.0, 0.0, True, False, 0, True)
    return EntryAnalysis(natural=option, suggestion=None)


def _synthetic_exit(road: BrainRoad, exit_idx: int) -> ExitAnalysis:
    option = ExitOption(exit_idx, road.exits[exit_idx], 0.0, 100, 0, 0.0, 0.0, 0.0, True, False, 0, True)
    return ExitAnalysis(natural=option, suggestion=None)


def _known_price(road: BrainRoad, a: int, b: int, payment: TollPayment) -> float:
    value = getPrice(road, a, b, payment)
    return 0.0 if value is None else round(value, 2)


def _road(road_idx: int, roads: Optional[List[BrainRoad]] = None) -> BrainRoad:
    active_roads = roads or OFFICIAL_ROADS
    for road in active_roads:
        if road.id == road_idx:
            return road
    raise ValueError(f"Unknown road index {road_idx}")


def _is_free_gap(road: BrainRoad, a: int, b: int, payment: TollPayment) -> bool:
    return getPrice(road, a, b, payment) == 0


def _pair(a: int, b: int) -> Tuple[int, int]:
    return (min(a, b), max(a, b))


def _direction(start: int, end: int) -> int:
    return 1 if end >= start else -1


def _valid_exit(road: BrainRoad, idx: int) -> bool:
    return 0 <= idx < len(road.exits)


def _score(used: int, paid: int) -> int:
    return round(max(0, min(100, used / max(paid, 1) * 100)))


def _normalize(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def _official_toll_points_by_exit(road_short: str, exits: List[str]) -> Dict[int, NTTARateEntry]:
    mapped = {}
    for index, exit_name in enumerate(exits):
        rate = get_toll_point_by_name(exit_name)
        if rate is not None and _road_matches(road_short, rate.road_name):
            mapped[index] = rate
    for alias, (road_id, exit_index) in EXIT_ALIASES.items():
        road = next((item for item in OFFICIAL_ROADS_SEED if item[0] == road_id), None)
        if road and road[1] == road_short:
            rate = get_toll_point_by_name(alias)
            if rate is not None and _road_matches(road_short, rate.road_name):
                mapped[exit_index] = rate
    return mapped


def _road_matches(road_short: str, road_name: str) -> bool:
    if road_short == "DNT":
        return road_name == "Dallas North Tollway"
    if road_short == "SH-121":
        return road_name == "Sam Rayburn Tollway"
    return False


def _connections() -> List[RoadConnection]:
    roads = matrix_brain_roads()
    seeds = [
        (0, "SRT", 2, "DNT", "SRT Interchange", "free"),
        (2, "DNT", 0, "SRT", "SRT Interchange", "free"),
        (0, "PGBT", 1, "DNT", "DNT/PGBT Interchange", "free"),
        (1, "DNT", 0, "PGBT", "DNT/PGBT Interchange", "free"),
    ]
    connections = []
    for from_road, from_name, to_road, to_name, via_name, via in seeds:
        try:
            from_exit = _find_exit_index(_road(from_road, roads), from_name)
            to_entry = _find_exit_index(_road(to_road, roads), to_name)
        except ValueError:
            continue
        connections.append(RoadConnection(from_road, from_exit, to_road, to_entry, via_name, via))
    return connections


def _find_exit_index(road: BrainRoad, name: str) -> int:
    normalized = _normalize(name)
    for index, exit_name in enumerate(road.exits):
        if normalized in _normalize(exit_name):
            return index
    raise ValueError(f"Exit {name} not found on {road.short}")


def matrix_brain_roads() -> List[BrainRoad]:
    return [_matrix_road_to_brain(road) for road in load_matrix_roads()]


def _matrix_road_to_brain(road: NTTAMatrixRoad) -> BrainRoad:
    return BrainRoad(
        id=road.road_id,
        short=road.road_short,
        name=road.road_name,
        exits=road.exits,
        tolltag_matrix={
            _pair(row_index, column_index): value
            for row_index, row in enumerate(road.tolltag)
            for column_index, value in enumerate(row)
        },
        zipcash_matrix={
            _pair(row_index, column_index): value
            for row_index, row in enumerate(road.zipcash)
            for column_index, value in enumerate(row)
        },
    )

EXIT_ALIASES = {
    "Royal Lane": (0, 3),
    "Trinity Mills Main Lane Gantry": (0, 11),
    "Frankford Road": (0, 11),
    "Eldorado Main Lane Gantry": (0, 26),
    "Wycliff Main Lane Gantry": (0, 0),
    "Coit Road": (2, 17),
    "Coit Main Lane Gantry": (2, 17),
    "Preston Road": (2, 14),
    "Josey Lane": (2, 8),
    "Josey Main Lane Gantry": (2, 8),
}

OFFICIAL_ROADS = matrix_brain_roads()
