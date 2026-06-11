from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.persistence.mongodb_client import MongoDBConnectionError, get_database, should_use_mongodb


def save_optimization_run(
    request_payload: dict[str, Any],
    best_recommendation: dict[str, Any],
    ranked_options: list[dict[str, Any]],
    source_metadata: dict[str, Any],
) -> dict[str, Any]:
    if not should_use_mongodb():
        return {
            "status": "skipped",
            "data_source": "mock",
            "reason": "TOLLIO_STORAGE_MODE is not mongodb or MONGODB_URI is missing.",
        }

    document = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input": _safe_request_payload(request_payload),
        "best_recommendation": _option_summary(best_recommendation),
        "ranked_options": [_option_summary(option) for option in ranked_options],
        "payment": request_payload.get("payment", "tolltag"),
        "source_metadata": source_metadata,
    }
    try:
        db = get_database()
        result = db["optimization_runs"].insert_one(document)
        return {
            "status": "saved",
            "data_source": "mongodb",
            "saved_id": str(result.inserted_id),
        }
    except MongoDBConnectionError as exc:
        return {"status": "failed", "data_source": "mongodb", "error": str(exc)}
    except Exception as exc:
        return {"status": "failed", "data_source": "mongodb", "error": exc.__class__.__name__}


def write_memory_probe() -> dict[str, Any]:
    if not should_use_mongodb():
        return {"status": "skipped", "data_source": "mock"}
    try:
        db = get_database()
        result = db["optimization_runs"].insert_one(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "kind": "demo_memory_probe",
                "source_metadata": {"endpoint": "/api/v1/demo/mongodb-invocation"},
            }
        )
        return {"status": "success", "data_source": "mongodb", "saved_id": str(result.inserted_id)}
    except Exception as exc:
        return {"status": "failure", "data_source": "mongodb", "error": exc.__class__.__name__}


def _safe_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    blocked = {"mongodb_uri", "gemini_api_key", "google_maps_api_key", "api_key", "password"}
    return {key: value for key, value in payload.items() if key.lower() not in blocked}


def _option_summary(option: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": option.get("label"),
        "route_path_label": option.get("route_path_label"),
        "entry": option.get("entry"),
        "exit": option.get("exit"),
        "toll_cost": option.get("toll_cost"),
        "toll_saved": option.get("toll_saved"),
        "net_savings": option.get("net_savings"),
        "added_minutes": option.get("added_minutes"),
        "value_score": option.get("value_score"),
        "confidence": option.get("confidence"),
    }
