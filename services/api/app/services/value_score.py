from typing import List, Optional

from pydantic import BaseModel

from app.data.ntta_roads import NTTARoad, ROADS, get_price


class ValueScoreBreakdown(BaseModel):
    road_name: str
    road_short: str
    entry_name: str
    exit_name: str
    tier_start: str
    tier_end: str
    entry_value_score: int
    exit_value_score: int
    combined_value_score: int
    wasted_behind: int
    unused_ahead: int
    paid_but_unused_reason: str
    value_loss_reason: str
    ntta_data_used: bool = True


def entry_value_score(
    road: NTTARoad,
    entry_index: int,
    destination_index: int,
    payment: str = "zipcash",
) -> int:
    tier_index = tier_start(road, entry_index, destination_index, payment)
    paid_exits = max(abs(destination_index - tier_index), 1)
    used_exits = max(abs(destination_index - entry_index), 1)
    return _score(used_exits, paid_exits)


def exit_value_score(
    road: NTTARoad,
    entry_index: int,
    exit_index: int,
    payment: str = "zipcash",
) -> int:
    tier_index = tier_end(road, entry_index, exit_index, payment)
    paid_exits = max(abs(tier_index - entry_index), 1)
    used_exits = max(abs(exit_index - entry_index), 1)
    return _score(used_exits, paid_exits)


def combined_value_score(
    road: NTTARoad,
    entry_index: int,
    exit_index: int,
    payment: str = "zipcash",
) -> int:
    return min(
        entry_value_score(road, entry_index, exit_index, payment),
        exit_value_score(road, entry_index, exit_index, payment),
    )


def wasted_behind(
    road: NTTARoad,
    entry_index: int,
    destination_index: int,
    payment: str = "zipcash",
) -> int:
    return abs(entry_index - tier_start(road, entry_index, destination_index, payment))


def unused_ahead(
    road: NTTARoad,
    entry_index: int,
    exit_index: int,
    payment: str = "zipcash",
) -> int:
    return abs(tier_end(road, entry_index, exit_index, payment) - exit_index)


def tier_start(
    road: NTTARoad,
    entry_index: int,
    destination_index: int,
    payment: str = "zipcash",
) -> int:
    base_price = get_price(road, entry_index, destination_index, payment)
    if base_price <= 0:
        return entry_index

    travel_direction = _direction(entry_index, destination_index)
    tier_index = entry_index
    probe = entry_index - travel_direction
    while _valid_exit(road, probe) and get_price(road, probe, destination_index, payment) == base_price:
        tier_index = probe
        probe -= travel_direction
    return tier_index


def tier_end(
    road: NTTARoad,
    entry_index: int,
    exit_index: int,
    payment: str = "zipcash",
) -> int:
    base_price = get_price(road, entry_index, exit_index, payment)
    if base_price <= 0:
        return exit_index

    travel_direction = _direction(entry_index, exit_index)
    tier_index = exit_index
    probe = exit_index + travel_direction
    while _valid_exit(road, probe) and get_price(road, entry_index, probe, payment) == base_price:
        tier_index = probe
        probe += travel_direction
    return tier_index


def paid_but_unused_reason(
    road: NTTARoad,
    entry_index: int,
    exit_index: int,
    payment: str = "zipcash",
) -> str:
    behind = wasted_behind(road, entry_index, exit_index, payment)
    ahead = unused_ahead(road, entry_index, exit_index, payment)
    if behind == 0 and ahead == 0:
        return "Entry and exit align with the paid NTTA tier; no obvious unused toll value."
    if behind and ahead:
        return (
            f"Paid tier includes {behind} exit(s) behind the driver and {ahead} "
            "exit(s) ahead that this trip does not use."
        )
    if behind:
        return f"Paid tier includes {behind} exit(s) behind the driver before the chosen entry."
    return f"Paid tier includes {ahead} exit(s) ahead after the chosen exit."


def value_loss_reason(
    road: NTTARoad,
    entry_index: int,
    exit_index: int,
    payment: str = "zipcash",
) -> str:
    entry_score = entry_value_score(road, entry_index, exit_index, payment)
    exit_score = exit_value_score(road, entry_index, exit_index, payment)
    combined_score = min(entry_score, exit_score)
    if combined_score >= 90:
        return "High-value toll use: the paid tier closely matches the road actually driven."
    if entry_score < 75 and exit_score < 75:
        return "Low value: this route pays for toll-road distance both before entry and after exit."
    if entry_score < 75:
        return "Value loss from entering after the paid tier already started."
    if exit_score < 75:
        return "Value loss from exiting before the paid tier fully ends."
    return "Moderate value: a small part of the paid tier is not used."


def build_value_score_breakdown(
    road_short: str,
    entry_index: int,
    exit_index: int,
    payment: str = "zipcash",
) -> Optional[ValueScoreBreakdown]:
    road = ROADS.get(road_short)
    if road is None or not _valid_exit(road, entry_index) or not _valid_exit(road, exit_index):
        return None
    if get_price(road, entry_index, exit_index, payment) <= 0:
        return None

    start_index = tier_start(road, entry_index, exit_index, payment)
    end_index = tier_end(road, entry_index, exit_index, payment)
    entry_score = entry_value_score(road, entry_index, exit_index, payment)
    exit_score = exit_value_score(road, entry_index, exit_index, payment)
    combined_score = min(entry_score, exit_score)
    return ValueScoreBreakdown(
        road_name=road.name,
        road_short=road.short,
        entry_name=road.exits[entry_index],
        exit_name=road.exits[exit_index],
        tier_start=road.exits[start_index],
        tier_end=road.exits[end_index],
        entry_value_score=entry_score,
        exit_value_score=exit_score,
        combined_value_score=combined_score,
        wasted_behind=wasted_behind(road, entry_index, exit_index, payment),
        unused_ahead=unused_ahead(road, entry_index, exit_index, payment),
        paid_but_unused_reason=paid_but_unused_reason(road, entry_index, exit_index, payment),
        value_loss_reason=value_loss_reason(road, entry_index, exit_index, payment),
    )


def average_combined_score(breakdowns: List[ValueScoreBreakdown]) -> int:
    if not breakdowns:
        return 0
    return round(sum(item.combined_value_score for item in breakdowns) / len(breakdowns))


def _direction(start_index: int, end_index: int) -> int:
    return 1 if end_index >= start_index else -1


def _valid_exit(road: NTTARoad, index: int) -> bool:
    return 0 <= index < len(road.exits)


def _score(used_exits: int, paid_exits: int) -> int:
    return round(max(0, min(100, (used_exits / max(paid_exits, 1)) * 100)))
