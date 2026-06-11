#!/usr/bin/env python3
"""Seed official NTTA matrix data into MongoDB without printing secrets."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = REPO_ROOT / "services/api/app/data/ntta_matrices_april_2025.json"


def main() -> int:
    uri = os.getenv("MONGODB_URI", "").strip()
    if not uri:
        print("MONGODB_URI is not set; seed skipped.")
        return 0

    try:
        from pymongo import MongoClient
        from pymongo.errors import PyMongoError
    except ImportError:
        print("pymongo is required to seed NTTA matrix data.")
        return 1

    payload = json.loads(DATA_FILE.read_text())
    database_name = os.getenv("MONGODB_DATABASE", "tollio_ai")
    client = None
    try:
        client = MongoClient(
            uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
        )
        client.admin.command("ping")
        collection = client[database_name]["ntta_matrices"]
        count = 0
        for road in payload["roads"]:
            source = road.get("source_metadata", {})
            document = {
                **road,
                "source_file": source.get("source_file", payload["source_file"]),
                "effective_date": source.get("effective_date", payload["effective_date"]),
                "confidence": source.get("confidence", payload["confidence"]),
                "source_metadata": {
                    **source,
                    "seeded_from": str(DATA_FILE.relative_to(REPO_ROOT)),
                },
            }
            collection.update_one(
                {
                    "road_name": road["road_name"],
                    "effective_date": document["effective_date"],
                    "source_metadata.source_file": document["source_metadata"].get("source_file"),
                },
                {"$set": document},
                upsert=True,
            )
            count += 1
        print(f"Seeded {count} NTTA matrix road document(s) into {database_name}.ntta_matrices.")
        return 0
    except (PyMongoError, OSError) as exc:
        print(f"MongoDB seed failed: {exc.__class__.__name__}")
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    sys.exit(main())
