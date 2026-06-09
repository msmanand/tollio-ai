from typing import List

from app.models import (
    AgentRequest,
    GantryAction,
    GantryDecision,
    RouteOption,
    TollEstimate,
)


def gantry_intelligence_tool(
    request: AgentRequest,
    route_options: List[RouteOption],
    toll_estimates: List[TollEstimate],
) -> List[GantryDecision]:
    """Return deterministic gantry-level decisions that demonstrate Tollio's core insight."""
    if request.origin.lower() == "frisco" and request.destination.lower() == "downtown dallas":
        return [
            GantryDecision(
                gantry_name_or_segment="DNT Frisco Mainline Segment",
                action=GantryAction.stay_on_toll,
                toll_cost_avoided=0.0,
                added_minutes=0,
                budget_effect="Worth paying because it protects arrival reliability.",
                value_score=0.91,
                reason="High minutes saved per toll dollar relative to local roads.",
            ),
            GantryDecision(
                gantry_name_or_segment="Legacy Drive Low-Value Gantry",
                action=GantryAction.exit_before_gantry,
                toll_cost_avoided=3.10,
                added_minutes=3,
                budget_effect="Avoids an unnecessary scanner and preserves the daily budget.",
                value_score=0.28,
                reason="The toll charge is high compared with the small travel-time benefit.",
            ),
            GantryDecision(
                gantry_name_or_segment="North Dallas Reentry Segment",
                action=GantryAction.reenter_after_gantry,
                toll_cost_avoided=1.40,
                added_minutes=2,
                budget_effect="Balances savings with a faster downtown approach.",
                value_score=0.72,
                reason="Reentry after the skipped gantry keeps the best remaining toll value.",
            ),
        ]

    return [
        GantryDecision(
            gantry_name_or_segment="Placeholder segment",
            action=GantryAction.avoid_toll,
            toll_cost_avoided=0.0,
            added_minutes=0,
            budget_effect="No budget change in placeholder mode.",
            value_score=0.0,
            reason="Live route and toll data are intentionally not connected yet.",
        )
    ]
