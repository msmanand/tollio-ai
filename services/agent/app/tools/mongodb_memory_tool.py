import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


def _data_source() -> str:
    if os.getenv("TOLLIO_STORAGE_MODE", "mock").lower() == "mongodb" and os.getenv("MONGODB_URI"):
        return "mongodb"
    return "mock_mongodb_memory_tool"


def _mcp_config_present() -> bool:
    return (Path(__file__).resolve().parents[2] / "mcp.mongodb.json").exists()


def _collection(name: str):
    if _data_source() != "mongodb":
        return None
    try:
        from pymongo import MongoClient

        client = MongoClient(
            os.environ["MONGODB_URI"],
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000,
            socketTimeoutMS=2000,
        )
        client.admin.command("ping")
        return client[os.getenv("MONGODB_DATABASE", "tollio_ai")][name]
    except Exception:
        return None


def save_trip_decision_tool(
    commute_plan_id: str,
    user_label: str,
    estimated_savings: float = 0.0,
) -> Dict[str, object]:
    normalized_id = commute_plan_id.lower().replace(" ", "-")
    collection = _collection("agent_tool_traces")
    if collection is not None:
        document = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tool_name": "save_trip_decision_tool",
            "action": "save_trip_decision",
            "commute_plan_id": commute_plan_id,
            "user_label": user_label,
            "estimated_savings": estimated_savings,
            "mcp_config_present": _mcp_config_present(),
        }
        result = collection.insert_one(document)
        return {
            "saved_trip_id": str(result.inserted_id),
            "status": "saved",
            "user_label": user_label,
            "estimated_savings": estimated_savings,
            "data_source": "mongodb",
            "mcp_config_present": _mcp_config_present(),
        }
    return {
        "saved_trip_id": f"mock-trip-{normalized_id}",
        "status": "saved",
        "user_label": user_label,
        "estimated_savings": estimated_savings,
        "data_source": _data_source(),
        "mcp_config_present": _mcp_config_present(),
    }


def get_budget_profile_tool(user_id: str = "demo-user") -> Dict[str, object]:
    return {
        "user_id": user_id,
        "daily_budget": 8.0,
        "weekly_budget": 40.0,
        "monthly_budget": 160.0,
        "data_source": _data_source(),
        "mcp_config_present": _mcp_config_present(),
    }


def get_recent_commutes_tool(user_id: str = "demo-user", limit: int = 5) -> Dict[str, object]:
    collection = _collection("agent_tool_traces")
    if collection is not None:
        docs = list(
            collection.find({"tool_name": "save_trip_decision_tool"}, {"_id": 0})
            .sort("created_at", -1)
            .limit(limit)
        )
        return {
            "user_id": user_id,
            "recent_commutes": docs,
            "data_source": "mongodb",
            "mcp_config_present": _mcp_config_present(),
        }
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
        "mcp_config_present": _mcp_config_present(),
    }


def update_savings_summary_tool(
    user_id: str = "demo-user",
    additional_savings: float = 0.0,
) -> Dict[str, object]:
    collection = _collection("agent_tool_traces")
    if collection is not None:
        document = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tool_name": "update_savings_summary_tool",
            "action": "update_savings_summary",
            "user_id": user_id,
            "additional_savings": additional_savings,
            "mcp_config_present": _mcp_config_present(),
        }
        result = collection.insert_one(document)
        return {
            "user_id": user_id,
            "estimated_total_savings": round(additional_savings, 2),
            "status": "updated",
            "data_source": "mongodb",
            "saved_trace_id": str(result.inserted_id),
            "mcp_config_present": _mcp_config_present(),
        }
    return {
        "user_id": user_id,
        "estimated_total_savings": round(4.5 + additional_savings, 2),
        "status": "updated",
        "data_source": _data_source(),
        "mcp_config_present": _mcp_config_present(),
    }
