from typing import Dict, Optional

from app.persistence.models import RecentTrips, SavingsSummary, TripDecisionRecord
from app.persistence.mongodb_client import get_database, should_use_mongodb


_MOCK_TRIPS: Dict[str, TripDecisionRecord] = {}


class TripRepository:
    def __init__(self, database=None):
        self.database = database if database is not None else get_database()
        self.data_source = "mongodb" if should_use_mongodb() else "mock_persistence"

    def save_trip_decision(
        self,
        commute_plan_id: str,
        user_label: str,
        route_summary: str = "Saved Tollio commute decision",
        estimated_savings: float = 0.0,
        optimized_route_cost: float = 0.0,
    ) -> TripDecisionRecord:
        saved_trip_id = f"trip-{commute_plan_id.lower().replace(' ', '-')}"
        record = TripDecisionRecord(
            saved_trip_id=saved_trip_id,
            commute_plan_id=commute_plan_id,
            user_label=user_label,
            route_summary=route_summary,
            estimated_savings=estimated_savings,
            optimized_route_cost=optimized_route_cost,
        )
        if self.database is not None:
            self.database.trips.update_one(
                {"saved_trip_id": saved_trip_id},
                {"$set": record.model_dump()},
                upsert=True,
            )
        else:
            _MOCK_TRIPS[saved_trip_id] = record
        return record

    def get_recent_trips(self, limit: int = 5) -> RecentTrips:
        if self.database is not None:
            docs = self.database.trips.find({}, {"_id": 0}).sort("_id", -1).limit(limit)
            return RecentTrips(
                trips=[TripDecisionRecord(**doc) for doc in docs],
                data_source=self.data_source,
            )

        trips = list(_MOCK_TRIPS.values())[-limit:]
        if not trips:
            trips = [
                TripDecisionRecord(
                    saved_trip_id="trip-sample-commute-plan",
                    commute_plan_id="sample-commute-plan",
                    user_label="Frisco to Downtown Dallas",
                    route_summary="Mock gantry-aware commute decision",
                    estimated_savings=4.5,
                    optimized_route_cost=6.25,
                )
            ]
        return RecentTrips(trips=trips, data_source=self.data_source)

    def get_savings_summary(self) -> SavingsSummary:
        trips = self.get_recent_trips(limit=100).trips
        return SavingsSummary(
            trip_count=len(trips),
            estimated_total_savings=round(sum(trip.estimated_savings for trip in trips), 2),
            data_source=self.data_source,
        )


def get_trip_repository(database: Optional[object] = None) -> TripRepository:
    return TripRepository(database=database)
