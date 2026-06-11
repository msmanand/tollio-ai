#!/usr/bin/env python3
"""Normalize official NTTA 2025-2027 PDF toll-rate rows into JSON.

The checked-in rows below are copied from the official NTTA PDF text extraction
for toll points used by the Tollio demo and tests. The script intentionally
keeps unknown route pricing out of the output; entries are toll-point rates.
"""

import json
from pathlib import Path


SOURCE_URL = "https://www.ntta.org/sites/default/files/2025-06/NTTAS_2025-2027_Toll%20Rate%20Tables.pdf"
EFFECTIVE_START = "2025-07-01"
EFFECTIVE_END = "2027-06-30"
OUTPUT_PATH = Path("services/api/app/data/ntta_rates_2025_2027.json")

VEHICLE_CLASSES = [
    "two_axle_passenger",
    "three_axle",
    "four_axle",
    "five_axle",
    "six_or_more_axle",
]

OFFICIAL_ROWS = [
    ("Dallas North Tollway", "Wycliff Main Lane Gantry", "MLP1", [1.94, 3.88, 3.88, 7.76, 5.82, 11.64, 7.76, 15.52, 9.70, 19.40]),
    ("Dallas North Tollway", "Mockingbird Lane", "MOCLN", [1.41, 2.82, 2.82, 5.64, 4.23, 8.46, 5.64, 11.28, 7.05, 14.10]),
    ("Dallas North Tollway", "Northwest Highway", "NORHY", [0.96, 1.92, 1.92, 3.84, 2.88, 5.76, 3.84, 7.68, 4.80, 9.60]),
    ("Dallas North Tollway", "Royal Lane", "ROYLN", [0.51, 1.02, 1.02, 2.04, 1.53, 3.06, 2.04, 4.08, 2.55, 5.10]),
    ("Dallas North Tollway", "Spring Valley Road", "SPVRD", [0.34, 0.68, 0.68, 1.36, 1.02, 2.04, 1.36, 2.72, 1.70, 3.40]),
    ("Dallas North Tollway", "Belt Line Road", "BELRD", [0.45, 0.90, 0.90, 1.80, 1.35, 2.70, 1.80, 3.60, 2.25, 4.50]),
    ("Dallas North Tollway", "Keller Springs Road", "KESRD", [0.67, 1.34, 1.34, 2.68, 2.01, 4.02, 2.68, 5.36, 3.35, 6.70]),
    ("Dallas North Tollway", "Trinity Mills Main Lane Gantry", "MLP2", [1.39, 2.78, 2.78, 5.56, 4.17, 8.34, 5.56, 11.12, 6.95, 13.90]),
    ("Dallas North Tollway", "Parker Main Lane Gantry", "MLP3", [1.23, 2.46, 2.46, 4.92, 3.69, 7.38, 4.92, 9.84, 6.15, 12.30]),
    ("Dallas North Tollway", "Legacy Drive", "LEGDR", [0.34, 0.68, 0.68, 1.36, 1.02, 2.04, 1.36, 2.72, 1.70, 3.40]),
    ("Dallas North Tollway", "Eldorado Main Lane Gantry", "MLP4", [2.19, 4.38, 4.38, 8.76, 6.57, 13.14, 8.76, 17.52, 10.95, 21.90]),
    ("Dallas North Tollway", "Eldorado Parkway", "ELDPY", [0.79, 1.58, 1.58, 3.16, 2.37, 4.74, 3.16, 6.32, 3.95, 7.90]),
    ("President George Bush Turnpike", "Coit Road", "COIRD", [0.79, 1.58, 1.58, 3.16, 2.37, 4.74, 3.16, 6.32, 3.95, 7.90]),
    ("President George Bush Turnpike", "Coit Main Lane Gantry", "MLP7", [1.65, 3.30, 3.30, 6.60, 4.95, 9.90, 6.60, 13.20, 8.25, 16.50]),
    ("President George Bush Turnpike", "Preston Road", "PRERD", [0.44, 0.88, 0.88, 1.76, 1.32, 2.64, 1.76, 3.52, 2.20, 4.40]),
    ("President George Bush Turnpike", "Josey Lane", "JOSLN", [0.53, 1.06, 1.06, 2.12, 1.59, 3.18, 2.12, 4.24, 2.65, 5.30]),
    ("Lewisville Lake Toll Bridge", "Lewisville Lake Toll Bridge", "LLTB", [1.55, 3.10, 3.10, 6.20, 4.65, 9.30, 6.20, 12.40, 7.75, 15.50]),
    ("Sam Rayburn Tollway", "Denton Tap Main Lane Gantry", "MLG1", [0.74, 1.48, 1.48, 2.96, 2.22, 4.44, 2.96, 5.92, 3.70, 7.40]),
    ("Sam Rayburn Tollway", "Josey Main Lane Gantry", "MLG2", [1.91, 3.82, 3.82, 7.64, 5.73, 11.46, 7.64, 15.28, 9.55, 19.10]),
    ("Sam Rayburn Tollway", "Coit Road", "COIRD", [0.78, 1.56, 1.56, 3.12, 2.34, 4.68, 3.12, 6.24, 3.90, 7.80]),
    ("Sam Rayburn Tollway", "Preston Road", "PRERD", [0.34, 0.68, 0.68, 1.36, 1.02, 2.04, 1.36, 2.72, 1.70, 3.40]),
    ("Sam Rayburn Tollway", "Custer Main Lane Gantry", "MLG3", [2.64, 5.28, 5.28, 10.56, 7.92, 15.84, 10.56, 21.12, 13.20, 26.40]),
    ("Chisholm Trail Parkway", "Farm Market 917", "FM917", [0.87, 1.74, 1.74, 3.48, 2.61, 5.22, 3.48, 6.96, 4.35, 8.70]),
]


def normalize_entries() -> list[dict]:
    entries = []
    for road_name, point_name, point_code, rates in OFFICIAL_ROWS:
        for index, vehicle_class in enumerate(VEHICLE_CLASSES):
            entries.append(
                {
                    "road_name": road_name,
                    "toll_point_name": point_name,
                    "toll_point_code": point_code,
                    "vehicle_class": vehicle_class,
                    "tolltag_rate": rates[index * 2],
                    "zipcash_rate": rates[index * 2 + 1],
                    "source_url": SOURCE_URL,
                    "effective_start": EFFECTIVE_START,
                    "effective_end": EFFECTIVE_END,
                    "confidence": "exact",
                }
            )
    return entries


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(normalize_entries(), indent=2) + "\n")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
