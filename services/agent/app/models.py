from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class UrgencyMode(str, Enum):
    saver = "saver"
    balanced = "balanced"
    urgent = "urgent"


class BudgetPeriod(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class GantryAction(str, Enum):
    stay_on_toll = "stay_on_toll"
    exit_before_gantry = "exit_before_gantry"
    reenter_after_gantry = "reenter_after_gantry"
    avoid_toll = "avoid_toll"


class AgentRequest(BaseModel):
    user_message: str = Field(..., min_length=1)
    origin: str = Field(..., min_length=1)
    destination: str = Field(..., min_length=1)
    arrival_time: str = Field(..., min_length=1)
    urgency_mode: UrgencyMode
    daily_budget: float = Field(..., ge=0)
    weekly_budget: float = Field(..., ge=0)
    monthly_budget: float = Field(..., ge=0)
    budget_period: BudgetPeriod
    toll_pass_type: str = Field(..., min_length=1)
    vehicle_mpg: float = Field(..., gt=0)
    gas_price: float = Field(..., ge=0)
    avoid_excessive_signals: bool


class RouteOption(BaseModel):
    route_id: str
    summary: str
    estimated_minutes: int
    estimated_toll_cost: float
    map_polyline: str


class TollEstimate(BaseModel):
    route_id: str
    total_toll_cost: float
    toll_pass_type: str
    source: str


class GantryDecision(BaseModel):
    gantry_name_or_segment: str
    action: GantryAction
    toll_cost_avoided: float
    added_minutes: int
    budget_effect: str
    value_score: float
    reason: str


class BudgetStatus(BaseModel):
    budget_period: BudgetPeriod
    budget_limit: float
    projected_toll_spend: float
    remaining_budget: float
    is_budget_preserved: bool
    status: str


class SaveTripResult(BaseModel):
    saved_trip_id: str
    status: str


class AgentResponse(BaseModel):
    intent: str
    chosen_route: RouteOption
    route_options_considered: List[RouteOption]
    gantry_decisions: List[GantryDecision]
    budget_status: BudgetStatus
    user_explanation: str
    next_actions: List[str]
    saved_trip_id: str
    confidence_level: str
    data_sources_used: List[str]
    memory_trace: List[str] = Field(default_factory=list)
