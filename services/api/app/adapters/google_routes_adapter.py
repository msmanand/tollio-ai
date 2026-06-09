import json
import os
from typing import Any, Dict, List
from urllib import request as urllib_request

from pydantic import BaseModel


class NormalizedRouteSegment(BaseModel):
    segment_label: str
    road_name: str
    start_location: str
    end_location: str
    segment_type: str
    estimated_minutes: int
    estimated_cost: float
    distance_miles: float


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
                "segment_label": "Segment A",
                "road_name": "Dallas North Tollway",
                "start_location": "Frisco",
                "end_location": "Legacy Drive",
                "segment_type": "toll",
                "estimated_minutes": 18,
                "estimated_cost": 4.25,
                "distance_miles": 13.2,
            },
            {
                "segment_label": "Segment B",
                "road_name": "Dallas North Tollway",
                "start_location": "Legacy Drive",
                "end_location": "North Dallas",
                "segment_type": "toll",
                "estimated_minutes": 7,
                "estimated_cost": 4.50,
                "distance_miles": 5.8,
            },
            {
                "segment_label": "Segment C",
                "road_name": "Dallas North Tollway",
                "start_location": "North Dallas",
                "end_location": "Downtown Dallas",
                "segment_type": "toll",
                "estimated_minutes": 16,
                "estimated_cost": 2.00,
                "distance_miles": 10.4,
            },
        ]
        optimized_segments = [
            {
                "segment_label": "Segment A",
                "road_name": "Dallas North Tollway",
                "start_location": "Frisco",
                "end_location": "Legacy Drive",
                "segment_type": "toll",
                "estimated_minutes": 18,
                "estimated_cost": 4.25,
                "distance_miles": 13.2,
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
                "segment_label": "Segment C",
                "road_name": "Dallas North Tollway",
                "start_location": "North Dallas Reentry",
                "end_location": "Downtown Dallas",
                "segment_type": "toll",
                "estimated_minutes": 20,
                "estimated_cost": 2.0,
                "distance_miles": 10.4,
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
                estimated_toll_cost=10.75,
                polyline="placeholder_natural_dnt_full_toll_route",
                segments=natural_segments,
                map_markers=markers,
            ),
            _route_option(
                route_id="optimized_gantry_plan",
                route_label="Gantry-aware optimized route",
                total_minutes=46,
                total_distance_miles=28.3,
                estimated_toll_cost=6.25,
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
        "routingPreference": traffic_mode,
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
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline,routes.travelAdvisory",
        },
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=10) as response:
        response_payload = json.loads(response.read().decode("utf-8"))
    return _normalize_live_response(response_payload)


def _normalize_live_response(response_payload: Dict[str, Any]) -> List[NormalizedRouteOption]:
    normalized = []
    for index, route in enumerate(response_payload.get("routes", []), start=1):
        duration_seconds = _duration_to_seconds(route.get("duration", "0s"))
        distance_miles = round(route.get("distanceMeters", 0) / 1609.344, 2)
        toll_cost = _extract_live_toll_cost(route)
        normalized.append(
            NormalizedRouteOption(
                route_id=f"google_routes_{index}",
                route_label=f"Google Routes option {index}",
                total_minutes=round(duration_seconds / 60),
                total_distance_miles=distance_miles,
                estimated_toll_cost=toll_cost,
                polyline=route.get("polyline", {}).get("encodedPolyline", ""),
                segments=[
                    NormalizedRouteSegment(
                        segment_label="Google route overview",
                        road_name="Provided by Google Routes",
                        start_location="origin",
                        end_location="destination",
                        segment_type="toll" if toll_cost > 0 else "local_road",
                        estimated_minutes=round(duration_seconds / 60),
                        estimated_cost=toll_cost,
                        distance_miles=distance_miles,
                    )
                ],
                map_markers=[],
                data_source="live_google_routes_api",
            )
        )
    return normalized


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
