import os
from typing import Any, Optional


def storage_mode() -> str:
    return os.getenv("TOLLIO_STORAGE_MODE", "mock").strip().lower()


def should_use_mongodb() -> bool:
    return storage_mode() == "mongodb" and bool(os.getenv("MONGODB_URI"))


def get_database() -> Optional[Any]:
    """Return a MongoDB database only when live persistence is explicitly enabled."""
    if not should_use_mongodb():
        return None

    try:
        from pymongo import MongoClient
    except ImportError as exc:
        raise RuntimeError("pymongo is required for TOLLIO_STORAGE_MODE=mongodb") from exc

    client = MongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=2000)
    return client[os.getenv("MONGODB_DATABASE", "tollio_ai")]
