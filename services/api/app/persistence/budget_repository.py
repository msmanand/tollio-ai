from typing import Dict, Optional

from app.persistence.models import BudgetProfile, BudgetStatus
from app.persistence.mongodb_client import get_database, should_use_mongodb


_MOCK_BUDGETS: Dict[str, BudgetProfile] = {}


class BudgetRepository:
    def __init__(self, database=None):
        self.database = database if database is not None else get_database()
        self.data_source = "mongodb" if should_use_mongodb() else "mock_persistence"

    def get_budget_profile(self, user_id: str = "demo-user") -> BudgetProfile:
        if self.database is not None:
            doc = self.database.budgets.find_one({"user_id": user_id}, {"_id": 0})
            if doc:
                return BudgetProfile(**doc)

        return _MOCK_BUDGETS.get(user_id) or BudgetProfile(
            user_id=user_id,
            daily_budget=8.0,
            weekly_budget=40.0,
            monthly_budget=160.0,
            current_daily_spend=6.25,
            current_weekly_spend=18.75,
            current_monthly_spend=62.5,
            data_source=self.data_source,
        )

    def update_budget_profile(
        self,
        user_id: str = "demo-user",
        daily_budget: float = 8.0,
        weekly_budget: float = 40.0,
        monthly_budget: float = 160.0,
    ) -> BudgetProfile:
        current = self.get_budget_profile(user_id=user_id)
        updated = BudgetProfile(
            user_id=user_id,
            daily_budget=daily_budget,
            weekly_budget=weekly_budget,
            monthly_budget=monthly_budget,
            current_daily_spend=current.current_daily_spend,
            current_weekly_spend=current.current_weekly_spend,
            current_monthly_spend=current.current_monthly_spend,
            data_source=self.data_source,
        )

        if self.database is not None:
            self.database.budgets.update_one(
                {"user_id": user_id},
                {"$set": updated.model_dump()},
                upsert=True,
            )
        else:
            _MOCK_BUDGETS[user_id] = updated

        return updated

    def get_budget_status(
        self,
        user_id: str = "demo-user",
        budget_period: str = "daily",
    ) -> BudgetStatus:
        profile = self.get_budget_profile(user_id=user_id)
        if budget_period == "weekly":
            limit = profile.weekly_budget
            spend = profile.current_weekly_spend
        elif budget_period == "monthly":
            limit = profile.monthly_budget
            spend = profile.current_monthly_spend
        else:
            budget_period = "daily"
            limit = profile.daily_budget
            spend = profile.current_daily_spend

        remaining = round(limit - spend, 2)
        return BudgetStatus(
            budget_period=budget_period,
            budget_limit=limit,
            estimated_spend=spend,
            remaining_budget=remaining,
            status="budget_available" if remaining >= 0 else "budget_exceeded",
            data_source=self.data_source,
        )


def get_budget_repository(database: Optional[object] = None) -> BudgetRepository:
    return BudgetRepository(database=database)
