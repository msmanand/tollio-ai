"""Normalize the uploaded NTTA toll calculator matrix data.

The uploaded PDF is the source document for the Tollio demo. The legacy Tollio
road matrix file is a transcription of that calculator matrix and is used here
as the machine-readable source so the app can load road-level entry/exit tables
without inventing any toll values.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any


SOURCE_PDF = Path("/Users/tsp00/Downloads/NTTAS Toll Calculator_April 2025.pdf")
LEGACY_ROADS = Path("/Users/tsp00/Downloads/tollio/tollio/src/data/roads.ts")
OUTPUT = Path("services/api/app/data/ntta_matrices_april_2025.json")


def main() -> None:
    if not SOURCE_PDF.exists():
        raise FileNotFoundError(f"Uploaded NTTA PDF not found: {SOURCE_PDF}")
    if not LEGACY_ROADS.exists():
        raise FileNotFoundError(f"Legacy matrix source not found: {LEGACY_ROADS}")

    roads = _parse_legacy_roads(LEGACY_ROADS.read_text())
    payload = {
        "source_file": SOURCE_PDF.name,
        "source_path": str(SOURCE_PDF),
        "effective_date": "2025-04-01",
        "confidence": "uploaded_pdf_matrix_transcription",
        "roads": roads,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")


def _parse_legacy_roads(source: str) -> list[dict[str, Any]]:
    start = source.index("export const ROADS")
    assignment = source.index("=", start)
    array_start = source.index("[", assignment)
    array_end = _matching(source, array_start, "[", "]")
    array_body = source[array_start + 1 : array_end]

    roads = []
    cursor = 0
    while cursor < len(array_body):
        try:
            object_start = array_body.index("{", cursor)
        except ValueError:
            break
        object_end = _matching(array_body, object_start, "{", "}")
        block = array_body[object_start : object_end + 1]
        roads.append(_parse_road(block))
        cursor = object_end + 1
    return roads


def _parse_road(block: str) -> dict[str, Any]:
    road_id = int(_field(block, "id"))
    short = _quoted_field(block, "short")
    name = _quoted_field(block, "name")
    exits = _literal_array(_field_array(block, "exits"))
    lower_rate_matrix = _literal_array(_field_array(block, "zipcash"))
    higher_rate_matrix = _literal_array(_field_array(block, "tolltag"))
    return {
        "road_id": road_id,
        "road_short": short,
        "road_name": name,
        "exits": exits,
        "tolltag": lower_rate_matrix,
        "zipcash": higher_rate_matrix,
        "source_metadata": {
            "source_file": SOURCE_PDF.name,
            "effective_date": "2025-04-01",
            "payment_types": ["tolltag", "zipcash"],
            "confidence": "uploaded_pdf_matrix_transcription",
        },
    }


def _field(block: str, name: str) -> str:
    match = re.search(rf"\b{name}\s*:\s*([^,\n]+)", block)
    if not match:
        raise ValueError(f"Missing field: {name}")
    return match.group(1).strip()


def _quoted_field(block: str, name: str) -> str:
    value = _field(block, name)
    return ast.literal_eval(value)


def _field_array(block: str, name: str) -> str:
    marker = re.search(rf"\b{name}\s*:\s*\[", block)
    if not marker:
        raise ValueError(f"Missing array field: {name}")
    array_start = marker.end() - 1
    array_end = _matching(block, array_start, "[", "]")
    return block[array_start : array_end + 1]


def _literal_array(value: str) -> list[Any]:
    return ast.literal_eval(value.replace("null", "None"))


def _matching(source: str, start: int, open_char: str, close_char: str) -> int:
    depth = 0
    in_string: str | None = None
    escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
            continue
        if char in ('"', "'"):
            in_string = char
        elif char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return index
    raise ValueError(f"Unclosed {open_char} at {start}")


if __name__ == "__main__":
    main()
