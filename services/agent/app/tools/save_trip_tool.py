from typing import List

from app.models import AgentRequest, GantryDecision, RouteOption, SaveTripResult


def save_trip_tool(
    request: AgentRequest,
    chosen_route: RouteOption,
    gantry_decisions: List[GantryDecision],
) -> SaveTripResult:
    """Mock-save the trip decision until MongoDB/MCP integration exists."""
    normalized_origin = request.origin.lower().replace(" ", "-")
    normalized_destination = request.destination.lower().replace(" ", "-")
    return SaveTripResult(
        saved_trip_id=f"mock-trip-{normalized_origin}-to-{normalized_destination}",
        status=f"mock_saved_{chosen_route.route_id}_{len(gantry_decisions)}_decisions",
    )
