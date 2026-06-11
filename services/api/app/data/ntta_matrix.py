import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from app.persistence.mongodb_client import MongoDBConnectionError, get_database, should_use_mongodb


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


_LOCAL_MATRIX_CACHE: Optional[List[NTTAMatrixRoad]] = None
_MONGODB_MATRIX_CACHE: Optional[List[NTTAMatrixRoad]] = None


def load_matrix_roads() -> List[NTTAMatrixRoad]:
    if should_use_mongodb():
        try:
            roads = load_matrix_roads_from_mongodb()
            if roads:
                return roads
            raise MongoDBConnectionError("MongoDB ntta_matrices collection has no seeded road documents.")
        except MongoDBConnectionError:
            if not allow_local_ntta_fallback():
                raise
        except Exception:
            if not allow_local_ntta_fallback():
                raise
    return load_matrix_roads_from_json()


def load_matrix_roads_from_json() -> List[NTTAMatrixRoad]:
    global _LOCAL_MATRIX_CACHE
    if _LOCAL_MATRIX_CACHE is not None:
        return _LOCAL_MATRIX_CACHE
    payload = json.loads(DATA_FILE.read_text())
    _LOCAL_MATRIX_CACHE = _roads_from_payload(payload)
    return _LOCAL_MATRIX_CACHE


def load_matrix_roads_from_mongodb(database=None) -> List[NTTAMatrixRoad]:
    global _MONGODB_MATRIX_CACHE
    if database is None and _MONGODB_MATRIX_CACHE is not None:
        return _MONGODB_MATRIX_CACHE
    db = database if database is not None else get_database()
    if db is None:
        return []
    docs = list(db["ntta_matrices"].find({}, {"_id": 0}).sort("road_id", 1))
    if not docs:
        return []
    payload = {
        "source_file": "MongoDB ntta_matrices",
        "effective_date": docs[0].get("effective_date", "unknown"),
        "confidence": docs[0].get("confidence", "unknown"),
        "roads": docs,
    }
    roads = _roads_from_payload(payload)
    if database is None:
        _MONGODB_MATRIX_CACHE = roads
    return roads


def matrix_data_source() -> str:
    if should_use_mongodb():
        try:
            if load_matrix_roads_from_mongodb():
                return "mongodb"
            return "local_json" if allow_local_ntta_fallback() else "mongodb_unavailable"
        except Exception:
            return "local_json" if allow_local_ntta_fallback() else "mongodb_unavailable"
    return "local_json"


def runtime_data_source() -> str:
    return "mongodb" if matrix_data_source() == "mongodb" else "local_json"


def allow_local_ntta_fallback() -> bool:
    return os.getenv("ALLOW_LOCAL_NTTA_FALLBACK", "false").strip().lower() == "true"


def _roads_from_payload(payload: dict) -> List[NTTAMatrixRoad]:
    roads = []
    for item in payload.get("roads", []):
        source = item.get("source_metadata", {})
        roads.append(
            NTTAMatrixRoad(
                road_id=item["road_id"],
                road_short=item["road_short"],
                road_name=item["road_name"],
                exits=item["exits"],
                tolltag=item["tolltag"],
                zipcash=item["zipcash"],
                source_file=source.get("source_file", item.get("source_file", payload["source_file"])),
                effective_date=source.get("effective_date", item.get("effective_date", payload["effective_date"])),
                confidence=source.get("confidence", item.get("confidence", payload["confidence"])),
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
    runtime_source = runtime_data_source()
    return [
        {
            "road_id": road.road_id,
            "road_short": road.road_short,
            "road_name": road.road_name,
            "exit_count": len(road.exits),
            "source_file": road.source_file,
            "effective_date": road.effective_date,
            "confidence": road.confidence,
            "runtime_data_source": runtime_source,
            "original_rate_source": road.source_file,
            "source_confidence": road.confidence,
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
