from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class NTTAConnection:
    from_road: str
    from_exit: str
    to_road: str
    to_entry: str
    via_name: str
    via: str


CONNECTIONS: List[NTTAConnection] = [
    NTTAConnection(
        from_road="DNT",
        from_exit="SRT",
        to_road="SH-121",
        to_entry="DNT",
        via_name="SRT Interchange",
        via="free",
    ),
    NTTAConnection(
        from_road="SH-121",
        from_exit="DNT",
        to_road="DNT",
        to_entry="SRT",
        via_name="SRT Interchange",
        via="free",
    ),
]
