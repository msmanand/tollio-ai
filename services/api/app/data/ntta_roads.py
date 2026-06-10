from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


TollPayment = str


@dataclass(frozen=True)
class NTTARoad:
    id: int
    short: str
    name: str
    exits: List[str]
    zipcash: Dict[Tuple[int, int], Optional[float]]
    tolltag: Dict[Tuple[int, int], Optional[float]]


def _pair(a: int, b: int) -> Tuple[int, int]:
    return (min(a, b), max(a, b))


def _matrix(entries: Dict[Tuple[int, int], Optional[float]]) -> Dict[Tuple[int, int], Optional[float]]:
    return {
        _pair(a, b): value
        for (a, b), value in entries.items()
    }


DNT = NTTARoad(
    id=0,
    short="DNT",
    name="Dallas North Tollway",
    exits=[
        "IH 35E/Oaklawn/Wycliff",
        "Mockingbird/Lemmon",
        "Lovers/Northwest Highway",
        "Walnut Hill/Royal",
        "Forest/Harvest Hill",
        "IH 635",
        "Alpha",
        "Spring Valley",
        "Belt Line",
        "Arapaho",
        "Keller Springs",
        "Trinity Mills/Frankford",
        "PGBT",
        "Plano Parkway",
        "Park",
        "Parker",
        "Windhaven/Spring Creek",
        "Legacy",
        "Headquarters",
        "SRT",
        "Gaylord",
        "Warren",
        "John Hickman",
        "Lebanon",
        "Stone Brook",
        "Cotton Gin/Main",
        "Eldorado",
        "Panther Creek",
        "CR 24/US 380",
    ],
    zipcash=_matrix(
        {
            (0, 17): 3.31,
            (0, 15): 3.31,
            (0, 16): 3.31,
            (0, 18): 3.31,
            (0, 19): 3.31,
            (0, 20): 3.56,
            (11, 17): 1.15,
            (12, 17): 0.90,
            (13, 17): 0.90,
            (14, 17): 0.90,
            (15, 17): 0.53,
            (16, 17): 0.30,
            (17, 18): None,
            (17, 19): None,
            (17, 20): 0.50,
            (19, 20): None,
            (19, 22): 0.36,
            (19, 23): 0.36,
            (19, 25): 0.76,
            (19, 26): 1.58,
        }
    ),
    tolltag=_matrix(
        {
            (0, 17): 4.97,
            (0, 18): 4.97,
            (0, 19): 4.97,
            (0, 20): 5.45,
            (11, 17): 1.83,
            (12, 17): 1.35,
            (13, 17): 1.35,
            (14, 17): 1.35,
            (15, 17): 0.80,
            (16, 17): 0.53,
            (17, 18): None,
            (17, 19): None,
            (17, 20): 0.96,
            (19, 20): None,
            (19, 22): 0.59,
            (19, 23): 0.59,
            (19, 25): 1.14,
            (19, 26): 2.37,
        }
    ),
)


SH121 = NTTARoad(
    id=2,
    short="SH-121",
    name="Sam Rayburn Tollway (SH-121)",
    exits=[
        "Business 121/Denton Tap",
        "MacArthur",
        "Lake Vista",
        "IH 35E/Huffines/Hebron",
        "Carrollton Parkway",
        "Parker",
        "Old Denton",
        "Standridge",
        "Josey",
        "Plano Parkway",
        "Spring Creek",
        "Legacy",
        "DNT",
        "Parkwood",
        "Preston",
        "Ohio",
        "Hillcrest",
        "Coit",
        "Independence",
        "Custer",
        "Exchange",
        "Alma",
        "Stacy",
        "Lake Forest",
        "Hardin",
        "US 75",
    ],
    zipcash=_matrix(
        {
            (0, 17): 2.47,
            (1, 17): 2.19,
            (2, 17): 1.94,
            (3, 17): 1.94,
            (4, 17): 1.94,
            (5, 17): 1.94,
            (6, 17): 1.94,
            (7, 17): 1.34,
            (8, 17): 1.21,
            (9, 17): 1.07,
            (10, 17): 0.82,
            (11, 17): 0.56,
            (12, 17): 0.56,
            (13, 17): 0.56,
            (14, 17): 0.56,
            (15, 17): 0.56,
            (16, 17): None,
            (17, 18): None,
            (17, 19): 0.92,
            (17, 20): 1.91,
            (17, 21): 1.91,
            (17, 22): 1.91,
            (17, 25): 1.91,
            (8, 20): 2.56,
            (8, 21): 2.56,
            (8, 22): 2.56,
            (8, 25): 2.56,
        }
    ),
    tolltag=_matrix(
        {
            (0, 17): 3.71,
            (1, 17): 3.39,
            (2, 17): 2.91,
            (3, 17): 2.91,
            (4, 17): 2.91,
            (5, 17): 2.91,
            (6, 17): 2.91,
            (7, 17): 2.01,
            (8, 17): 1.82,
            (9, 17): 1.61,
            (10, 17): 1.33,
            (11, 17): 0.84,
            (12, 17): 0.84,
            (13, 17): 0.84,
            (14, 17): 0.84,
            (15, 17): 0.84,
            (16, 17): None,
            (17, 18): None,
            (17, 19): 1.38,
            (17, 20): 2.87,
            (17, 21): 2.87,
            (17, 22): 2.87,
            (17, 25): 2.87,
            (8, 20): 3.85,
            (8, 21): 3.85,
            (8, 22): 3.85,
            (8, 25): 3.85,
        }
    ),
)


ROADS = {
    "DNT": DNT,
    "SH-121": SH121,
}


def get_price(
    road: NTTARoad,
    a: int,
    b: int,
    payment: TollPayment = "zipcash",
) -> float:
    if a == b:
        return 0.0
    table = road.tolltag if payment == "tolltag" else road.zipcash
    value = table.get(_pair(a, b))
    return 0.0 if value is None else float(value)


def is_free_gap(road: NTTARoad, a: int, b: int) -> bool:
    return road.zipcash.get(_pair(a, b)) is None
