import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional


TollPayment = str


@dataclass(frozen=True)
class NTTAMatrixRoad:
    road_id: int
    road_short: str
    road_name: str
    exits: List[str]
    tolltag: List[List[Optional[float]]]
    zipcash: List[List[Optional[float]]]
    source_file: str
    effective_date: str
    confidence: str


@dataclass(frozen=True)
class PriceLookup:
    road_name: str
    road_short: str
    from_exit: str
    to_exit: str
    payment: TollPayment
    price: Optional[float]
    source_file: str
    effective_date: str
    confidence: str
    exact_matrix_match: bool


DATA_FILE = Path(__file__).with_name("ntta_matrices_april_2025.json")


@lru_cache(maxsize=1)
def load_matrix_roads() -> List[NTTAMatrixRoad]:
    payload = json.loads(DATA_FILE.read_text())
    roads = []
    for item in payload["roads"]:
        source = item.get("source_metadata", {})
        roads.append(
            NTTAMatrixRoad(
                road_id=item["road_id"],
                road_short=item["road_short"],
                road_name=item["road_name"],
                exits=item["exits"],
                tolltag=item["tolltag"],
                zipcash=item["zipcash"],
                source_file=source.get("source_file", payload["source_file"]),
                effective_date=source.get("effective_date", payload["effective_date"]),
                confidence=source.get("confidence", payload["confidence"]),
            )
        )
    return roads


def find_road(road: str) -> Optional[NTTAMatrixRoad]:
    normalized = _normalize(road)
    for item in load_matrix_roads():
        if normalized in {
            _normalize(str(item.road_id)),
            _normalize(item.road_short),
            _normalize(item.road_name),
        }:
            return item
    return None


def find_exit_index(road: NTTAMatrixRoad, exit_name: str) -> Optional[int]:
    normalized = _normalize(exit_name)
    for index, name in enumerate(road.exits):
        if normalized == _normalize(name):
            return index
    for index, name in enumerate(road.exits):
        if normalized and normalized in _normalize(name):
            return index
    return None


def get_matrix_price(
    road: NTTAMatrixRoad,
    from_exit: str,
    to_exit: str,
    payment: TollPayment = "tolltag",
) -> PriceLookup:
    from_index = find_exit_index(road, from_exit)
    to_index = find_exit_index(road, to_exit)
    price = None
    exact = False
    if from_index is not None and to_index is not None:
        price = price_by_index(road, from_index, to_index, payment)
        exact = price is not None
    return PriceLookup(
        road_name=road.road_name,
        road_short=road.road_short,
        from_exit=from_exit,
        to_exit=to_exit,
        payment=payment,
        price=price,
        source_file=road.source_file,
        effective_date=road.effective_date,
        confidence=road.confidence if exact else "unknown",
        exact_matrix_match=exact,
    )


def price_by_index(
    road: NTTAMatrixRoad,
    from_index: int,
    to_index: int,
    payment: TollPayment = "tolltag",
) -> Optional[float]:
    if from_index == to_index:
        return 0.0
    table = road.tolltag if payment == "tolltag" else road.zipcash
    if not _valid_index(road, from_index) or not _valid_index(road, to_index):
        return None
    value = table[from_index][to_index]
    return 0.0 if value is None else round(float(value), 2)


def road_options() -> list[dict]:
    return [
        {
            "road_id": road.road_id,
            "road_short": road.road_short,
            "road_name": road.road_name,
            "exit_count": len(road.exits),
            "source_file": road.source_file,
            "effective_date": road.effective_date,
            "confidence": road.confidence,
        }
        for road in load_matrix_roads()
    ]


def exit_options(road: NTTAMatrixRoad) -> list[dict]:
    return [
        {
            "exit_index": index,
            "exit_name": name,
        }
        for index, name in enumerate(road.exits)
    ]


def _valid_index(road: NTTAMatrixRoad, index: int) -> bool:
    return 0 <= index < len(road.exits)


def _normalize(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())
