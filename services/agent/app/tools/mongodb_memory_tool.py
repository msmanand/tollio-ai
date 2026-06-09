import os
from typing import Dict, List


def _data_source() -> str:
    if os.getenv("TOLLIO_STORAGE_MODE", "mock").lower() == "mongodb" and os.getenv("MONGODB_URI"):
        return "mongodb_ready_interface"
    return "mock_mongodb_memory_tool"


def save_trip_decision_tool(
    commute_plan_id: str,
    user_label: str,
    estimated_savings: float = 0.0,
) -> Dict[str, object]:
    normalized_id = commute_plan_id.lower().replace(" ", "-")
    return {
        "saved_trip_id": f"mock-trip-{normalized_id}",
        "status": "saved",
        "user_label": user_label,
        "estimated_savings": estimated_savings,
        "data_source": _data_source(),
    }


def get_budget_profile_tool(user_id: str = "demo-user") -> Dict[str, object]:
    return {
        "user_id": user_id,
        "daily_budget": 8.0,
        "weekly_budget": 40.0,
        "monthly_budget": 160.0,
        "data_source": _data_source(),
    }


def get_recent_commutes_tool(user_id: str = "demo-user", limit: int = 5) -> Dict[str, object]:
    commutes: List[Dict[str, object]] = [
        {
            "saved_trip_id": "mock-trip-frisco-to-downtown-dallas",
            "route_summary": "Frisco to Downtown Dallas gantry-aware route",
            "estimated_savings": 4.5,
        }
    ][:limit]
    return {
        "user_id": user_id,
        "recent_commutes": commutes,
        "data_source": _data_source(),
    }


def update_savings_summary_tool(
    user_id: str = "demo-user",
    additional_savings: float = 0.0,
) -> Dict[str, object]:
    return {
        "user_id": user_id,
        "estimated_total_savings": round(4.5 + additional_savings, 2),
        "status": "updated",
        "data_source": _data_source(),
    }
