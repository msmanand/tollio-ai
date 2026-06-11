import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


SOURCE_URL = "https://www.ntta.org/sites/default/files/2025-06/NTTAS_2025-2027_Toll%20Rate%20Tables.pdf"
RATES_PATH = Path(__file__).with_name("ntta_rates_2025_2027.json")


class NTTARateEntry(BaseModel):
    road_name: str
    toll_point_name: str
    toll_point_code: str
    vehicle_class: str
    tolltag_rate: Optional[float]
    zipcash_rate: Optional[float]
    source_url: str
    effective_start: str
    effective_end: str
    confidence: str


@lru_cache(maxsize=1)
def load_ntta_rates() -> tuple[NTTARateEntry, ...]:
    return tuple(
        NTTARateEntry(**entry)
        for entry in json.loads(RATES_PATH.read_text())
    )


def toll_points(vehicle_class: str = "two_axle_passenger") -> list[NTTARateEntry]:
    return [
        entry
        for entry in load_ntta_rates()
        if entry.vehicle_class == vehicle_class
    ]


def find_toll_points(query: str, vehicle_class: str = "two_axle_passenger") -> list[NTTARateEntry]:
    normalized_query = _normalize(query)
    if not normalized_query:
        return []
    points = toll_points(vehicle_class)
    exact = [
        entry
        for entry in points
        if normalized_query in {
            _normalize(entry.toll_point_name),
            _normalize(entry.toll_point_code),
        }
    ]
    if exact:
        return exact
    return [
        entry
        for entry in points
        if normalized_query in _normalize(entry.toll_point_name)
        or normalized_query in _normalize(entry.road_name)
        or normalized_query in _normalize(entry.toll_point_code)
    ]


def get_toll_point_by_name(
    toll_point_name: str,
    vehicle_class: str = "two_axle_passenger",
) -> Optional[NTTARateEntry]:
    matches = find_toll_points(toll_point_name, vehicle_class)
    for match in matches:
        if _normalize(match.toll_point_name) == _normalize(toll_point_name):
            return match
    return matches[0] if matches else None


def unknown_rate(query: str, vehicle_class: str = "two_axle_passenger") -> NTTARateEntry:
    return NTTARateEntry(
        road_name="Unknown",
        toll_point_name=query or "Unknown",
        toll_point_code="UNKNOWN",
        vehicle_class=vehicle_class,
        tolltag_rate=None,
        zipcash_rate=None,
        source_url=SOURCE_URL,
        effective_start="2025-07-01",
        effective_end="2027-06-30",
        confidence="unknown",
    )


def _normalize(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())
