import json
import os
from typing import Any, Dict, List, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request

from pydantic import BaseModel

from app.data.ntta_rates import get_toll_point_by_name


class NormalizedRouteSegment(BaseModel):
    segment_label: str
    road_name: str
    start_location: str
    end_location: str
    segment_type: str
    estimated_minutes: int
    estimated_cost: float
    distance_miles: float
    tolltag_rate: Optional[float] = None
    zipcash_rate: Optional[float] = None
    rate_confidence: Optional[str] = None
    rate_source: Optional[str] = None


class NormalizedMapMarker(BaseModel):
    marker_type: str
    label: str
    latitude: float
    longitude: float
    description: str


class NormalizedRouteOption(BaseModel):
    route_id: str
    route_label: str
    total_minutes: int
    total_distance_miles: float
    estimated_toll_cost: float
    polyline: str
    segments: List[NormalizedRouteSegment]
    map_markers: List[NormalizedMapMarker]
    data_source: str


def live_routes_enabled() -> bool:
    return (
        os.getenv("ENABLE_LIVE_ROUTES", "false").strip().lower() == "true"
        and bool(os.getenv("GOOGLE_MAPS_API_KEY"))
    )


def get_route_options(
    origin: str,
    destination: str,
    arrival_time: str,
    traffic_mode: str,
) -> List[NormalizedRouteOption]:
    if live_routes_enabled():
        return _get_live_route_options(origin, destination, arrival_time, traffic_mode)
    return _get_mock_route_options(origin, destination)


def estimate_toll_info(route: NormalizedRouteOption) -> Dict[str, Any]:
    return {
        "route_id": route.route_id,
        "estimated_toll_cost": route.estimated_toll_cost,
        "data_source": route.data_source,
    }


def normalize_route_segments(route: Dict[str, Any]) -> List[NormalizedRouteSegment]:
    segments = route.get("segments", [])
    return [NormalizedRouteSegment(**segment) for segment in segments]


def _get_mock_route_options(origin: str, destination: str) -> List[NormalizedRouteOption]:
    if origin.strip().lower() == "frisco" and destination.strip().lower() == "downtown dallas":
        natural_segments = [
            {
                "segment_label": "Eldorado Main Lane Gantry",
                "road_name": "Dallas North Tollway",
                "start_location": "Frisco",
                "end_location": "Legacy Drive",
                "segment_type": "toll",
                "estimated_minutes": 18,
                "estimated_cost": _official_tolltag_rate("Eldorado Main Lane Gantry"),
                "distance_miles": 13.2,
                **_rate_metadata("Eldorado Main Lane Gantry"),
            },
            {
                "segment_label": "Legacy Drive",
                "road_name": "Dallas North Tollway",
                "start_location": "Legacy Drive",
                "end_location": "North Dallas",
                "segment_type": "toll",
                "estimated_minutes": 7,
                "estimated_cost": _official_tolltag_rate("Legacy Drive"),
                "distance_miles": 5.8,
                **_rate_metadata("Legacy Drive"),
            },
            {
                "segment_label": "Wycliff Main Lane Gantry",
                "road_name": "Dallas North Tollway",
                "start_location": "North Dallas",
                "end_location": "Downtown Dallas",
                "segment_type": "toll",
                "estimated_minutes": 16,
                "estimated_cost": _official_tolltag_rate("Wycliff Main Lane Gantry"),
                "distance_miles": 10.4,
                **_rate_metadata("Wycliff Main Lane Gantry"),
            },
        ]
        optimized_segments = [
            {
                "segment_label": "Eldorado Main Lane Gantry",
                "road_name": "Dallas North Tollway",
                "start_location": "Frisco",
                "end_location": "Legacy Drive",
                "segment_type": "toll",
                "estimated_minutes": 18,
                "estimated_cost": _official_tolltag_rate("Eldorado Main Lane Gantry"),
                "distance_miles": 13.2,
                **_rate_metadata("Eldorado Main Lane Gantry"),
            },
            {
                "segment_label": "Segment B",
                "road_name": "Legacy Drive Service Road",
                "start_location": "Legacy Drive Exit",
                "end_location": "North Dallas Reentry",
                "segment_type": "service_road",
                "estimated_minutes": 8,
                "estimated_cost": 0.0,
                "distance_miles": 4.7,
            },
            {
                "segment_label": "Wycliff Main Lane Gantry",
                "road_name": "Dallas North Tollway",
                "start_location": "North Dallas Reentry",
                "end_location": "Downtown Dallas",
                "segment_type": "toll",
                "estimated_minutes": 20,
                "estimated_cost": _official_tolltag_rate("Wycliff Main Lane Gantry"),
                "distance_miles": 10.4,
                **_rate_metadata("Wycliff Main Lane Gantry"),
            },
        ]
        markers = [
            {
                "marker_type": "origin",
                "label": "Frisco",
                "latitude": 33.1507,
                "longitude": -96.8236,
                "description": "Placeholder origin for the sample commute.",
            },
            {
                "marker_type": "gantry",
                "label": "DNT Frisco Mainline",
                "latitude": 33.0931,
                "longitude": -96.8211,
                "description": "High-value toll segment recommended to keep.",
            },
            {
                "marker_type": "exit",
                "label": "Exit before Legacy scanner",
                "latitude": 33.0735,
                "longitude": -96.8218,
                "description": "Skip the low-value gantry with small time impact.",
            },
            {
                "marker_type": "reentry",
                "label": "Reenter North Dallas",
                "latitude": 32.9541,
                "longitude": -96.8204,
                "description": "Rejoin toll route after the low-value scanner.",
            },
            {
                "marker_type": "destination",
                "label": "Downtown Dallas",
                "latitude": 32.7767,
                "longitude": -96.7970,
                "description": "Placeholder destination for the sample commute.",
            },
        ]
        return [
            _route_option(
                route_id="natural_full_toll",
                route_label="Full Dallas North Tollway route",
                total_minutes=41,
                total_distance_miles=29.4,
                estimated_toll_cost=_segments_cost(natural_segments),
                polyline="placeholder_natural_dnt_full_toll_route",
                segments=natural_segments,
                map_markers=markers,
            ),
            _route_option(
                route_id="optimized_gantry_plan",
                route_label="Gantry-aware optimized route",
                total_minutes=46,
                total_distance_miles=28.3,
                estimated_toll_cost=_segments_cost(optimized_segments),
                polyline="placeholder_exit_legacy_reenter_north_dallas",
                segments=optimized_segments,
                map_markers=markers,
            ),
        ]

    return [
        _route_option(
            route_id="mock_generic_route",
            route_label="Mock route pending Google Routes integration",
            total_minutes=0,
            total_distance_miles=0.0,
            estimated_toll_cost=0.0,
            polyline="placeholder_generic_route",
            segments=[
                {
                    "segment_label": "Placeholder segment",
                    "road_name": "Unknown",
                    "start_location": origin,
                    "end_location": destination,
                    "segment_type": "local_road",
                    "estimated_minutes": 0,
                    "estimated_cost": 0.0,
                    "distance_miles": 0.0,
                }
            ],
            map_markers=[
                {
                    "marker_type": "origin",
                    "label": origin,
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "description": "Placeholder origin marker.",
                },
                {
                    "marker_type": "destination",
                    "label": destination,
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "description": "Placeholder destination marker.",
                },
            ],
        )
    ]


def _route_option(
    route_id: str,
    route_label: str,
    total_minutes: int,
    total_distance_miles: float,
    estimated_toll_cost: float,
    polyline: str,
    segments: List[Dict[str, Any]],
    map_markers: List[Dict[str, Any]],
) -> NormalizedRouteOption:
    return NormalizedRouteOption(
        route_id=route_id,
        route_label=route_label,
        total_minutes=total_minutes,
        total_distance_miles=total_distance_miles,
        estimated_toll_cost=estimated_toll_cost,
        polyline=polyline,
        segments=normalize_route_segments({"segments": segments}),
        map_markers=[NormalizedMapMarker(**marker) for marker in map_markers],
        data_source="mock_google_routes_adapter",
    )


def _official_tolltag_rate(toll_point_name: str) -> float:
    rate = get_toll_point_by_name(toll_point_name)
    return rate.tolltag_rate if rate and rate.tolltag_rate is not None else 0.0


def _segments_cost(segments: List[Dict[str, Any]]) -> float:
    return round(sum(segment.get("estimated_cost", 0.0) for segment in segments), 2)


def _rate_metadata(toll_point_name: str) -> Dict[str, Any]:
    rate = get_toll_point_by_name(toll_point_name)
    if rate is None:
        return {
            "tolltag_rate": None,
            "zipcash_rate": None,
            "rate_confidence": "unknown",
            "rate_source": None,
        }
    return {
        "tolltag_rate": rate.tolltag_rate,
        "zipcash_rate": rate.zipcash_rate,
        "rate_confidence": rate.confidence,
        "rate_source": rate.source_url,
    }


def _get_live_route_options(
    origin: str,
    destination: str,
    arrival_time: str,
    traffic_mode: str,
) -> List[NormalizedRouteOption]:
    api_key = os.environ["GOOGLE_MAPS_API_KEY"]
    payload = {
        "origin": {"address": origin},
        "destination": {"address": destination},
        "travelMode": "DRIVE",
        "routingPreference": _routing_preference(traffic_mode),
        "computeAlternativeRoutes": True,
        "extraComputations": ["TOLLS"],
        "polylineQuality": "OVERVIEW",
    }
    if arrival_time:
        payload["arrivalTime"] = arrival_time

    req = urllib_request.Request(
        "https://routes.googleapis.com/directions/v2:computeRoutes",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": (
                "routes.duration,routes.distanceMeters,routes.polyline,"
                "routes.travelAdvisory,routes.legs,routes.routeLabels"
            ),
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=10) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        normalized = _normalize_live_response(response_payload, origin=origin, destination=destination)
        if normalized:
            return normalized
    except (OSError, urllib_error.URLError, json.JSONDecodeError):
        pass

    return _live_fallback_mock_routes(origin, destination)


def _normalize_live_response(
    response_payload: Dict[str, Any],
    origin: str = "origin",
    destination: str = "destination",
) -> List[NormalizedRouteOption]:
    normalized = []
    for index, route in enumerate(response_payload.get("routes", []), start=1):
        duration_seconds = _duration_to_seconds(route.get("duration", "0s"))
        distance_miles = round(route.get("distanceMeters", 0) / 1609.344, 2)
        toll_cost = _extract_live_toll_cost(route)
        segments = _normalize_live_segments(
            route=route,
            origin=origin,
            destination=destination,
            duration_seconds=duration_seconds,
            distance_miles=distance_miles,
            toll_cost=toll_cost,
        )
        normalized.append(
            NormalizedRouteOption(
                route_id=f"google_routes_{index}",
                route_label=_live_route_label(route, index),
                total_minutes=round(duration_seconds / 60),
                total_distance_miles=distance_miles,
                estimated_toll_cost=toll_cost,
                polyline=route.get("polyline", {}).get("encodedPolyline", ""),
                segments=segments,
                map_markers=_live_map_markers(origin, destination),
                data_source="live_google_routes_api",
            )
        )
    return normalized


def _normalize_live_segments(
    route: Dict[str, Any],
    origin: str,
    destination: str,
    duration_seconds: int,
    distance_miles: float,
    toll_cost: float,
) -> List[NormalizedRouteSegment]:
    steps = []
    for leg in route.get("legs", []):
        steps.extend(leg.get("steps", []))

    if not steps:
        return [
            NormalizedRouteSegment(
                segment_label="Google route overview",
                road_name="Provided by Google Routes",
                start_location=origin,
                end_location=destination,
                segment_type="toll" if toll_cost > 0 else "local_road",
                estimated_minutes=round(duration_seconds / 60),
                estimated_cost=toll_cost,
                distance_miles=distance_miles,
            )
        ]

    segment_count = len(steps)
    segments = []
    for index, step in enumerate(steps, start=1):
        step_duration_seconds = _duration_to_seconds(step.get("staticDuration", step.get("duration", "0s")))
        step_distance_miles = round(step.get("distanceMeters", 0) / 1609.344, 2)
        road_name = _road_name(step)
        step_toll_cost = toll_cost if index == 1 else 0.0
        segments.append(
            NormalizedRouteSegment(
                segment_label=f"Google step {index}",
                road_name=road_name,
                start_location=origin if index == 1 else f"Step {index - 1}",
                end_location=destination if index == segment_count else f"Step {index}",
                segment_type="toll" if step_toll_cost > 0 else "local_road",
                estimated_minutes=round(step_duration_seconds / 60),
                estimated_cost=step_toll_cost,
                distance_miles=step_distance_miles,
            )
        )
    return segments


def _duration_to_seconds(duration: str) -> int:
    if not duration.endswith("s"):
        return 0
    return int(float(duration[:-1]))


def _extract_live_toll_cost(route: Dict[str, Any]) -> float:
    toll_info = route.get("travelAdvisory", {}).get("tollInfo", {})
    prices = toll_info.get("estimatedPrice", [])
    if not prices:
        return 0.0
    first_price = prices[0]
    units = float(first_price.get("units", 0))
    nanos = float(first_price.get("nanos", 0)) / 1_000_000_000
    return round(units + nanos, 2)


def _routing_preference(traffic_mode: str) -> str:
    if traffic_mode in {"urgent", "balanced"}:
        return "TRAFFIC_AWARE"
    return "TRAFFIC_AWARE_OPTIMAL"


def _live_route_label(route: Dict[str, Any], index: int) -> str:
    labels = route.get("routeLabels", [])
    if labels:
        return f"Google Routes option {index}: {', '.join(labels)}"
    return f"Google Routes option {index}"


def _road_name(step: Dict[str, Any]) -> str:
    navigation_instruction = step.get("navigationInstruction", {})
    instructions = navigation_instruction.get("instructions")
    if instructions:
        return instructions
    return "Google Routes step"


def _live_map_markers(origin: str, destination: str) -> List[NormalizedMapMarker]:
    return [
        NormalizedMapMarker(
            marker_type="origin",
            label=origin,
            latitude=0.0,
            longitude=0.0,
            description="Live Google Routes origin address; coordinates deferred to map client.",
        ),
        NormalizedMapMarker(
            marker_type="destination",
            label=destination,
            latitude=0.0,
            longitude=0.0,
            description="Live Google Routes destination address; coordinates deferred to map client.",
        ),
    ]


def _live_fallback_mock_routes(origin: str, destination: str) -> List[NormalizedRouteOption]:
    routes = _get_mock_route_options(origin, destination)
    return [
        route.model_copy(
            update={
                "data_source": "mock_google_routes_adapter_live_fallback",
                "route_label": f"{route.route_label} (live fallback)",
            }
        )
        for route in routes
    ]
