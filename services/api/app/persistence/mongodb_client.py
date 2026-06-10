import os
from typing import Any, Optional


class MongoDBConnectionError(RuntimeError):
    """Raised when explicit MongoDB mode is requested but unavailable."""


def storage_mode() -> str:
    return os.getenv("TOLLIO_STORAGE_MODE", "mock").strip().lower()


def should_use_mongodb() -> bool:
    return storage_mode() == "mongodb" and bool(os.getenv("MONGODB_URI", "").strip())


def get_mongodb_client(client_factory=None) -> Optional[Any]:
    if storage_mode() != "mongodb":
        return None

    uri = os.getenv("MONGODB_URI", "").strip()
    if not uri:
        raise MongoDBConnectionError(
            "TOLLIO_STORAGE_MODE=mongodb requires MONGODB_URI to be set."
        )

    if client_factory is None:
        try:
            from pymongo import MongoClient
            from pymongo.errors import PyMongoError
        except ImportError as exc:
            raise MongoDBConnectionError("pymongo is required for MongoDB mode.") from exc
        client_factory = MongoClient
        handled_errors = (PyMongoError, OSError)
    else:
        handled_errors = (Exception,)

    client = client_factory(
        uri,
        serverSelectionTimeoutMS=2000,
        connectTimeoutMS=2000,
        socketTimeoutMS=2000,
    )
    try:
        client.admin.command("ping")
    except handled_errors as exc:
        raise MongoDBConnectionError(
            "Unable to connect to MongoDB Atlas with current MONGODB_URI."
        ) from exc
    return client


def get_database(client_factory=None) -> Optional[Any]:
    client = get_mongodb_client(client_factory=client_factory)
    if client is None:
        return None
    return client[os.getenv("MONGODB_DATABASE", "tollio_ai")]
