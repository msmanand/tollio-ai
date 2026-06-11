from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class UrgencyMode(str, Enum):
    saver = "saver"
    balanced = "balanced"
    urgent = "urgent"


class BudgetPeriod(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


class GantryAction(str, Enum):
    stay_on_toll = "stay_on_toll"
    exit_before_gantry = "exit_before_gantry"
    reenter_after_gantry = "reenter_after_gantry"
    avoid_toll = "avoid_toll"


class SegmentType(str, Enum):
    toll = "toll"
    service_road = "service_road"
    local_road = "local_road"


class MarkerType(str, Enum):
    origin = "origin"
    destination = "destination"
    gantry = "gantry"
    exit = "exit"
    reentry = "reentry"
    warning = "warning"


class CommutePlanRequest(BaseModel):
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
    budget_amount: Optional[float] = Field(default=None, ge=0)
    current_period_spend: float = Field(default=0.0, ge=0)
    commute_days_per_week: int = Field(default=5, ge=1, le=7)
    trips_per_commute_day: int = Field(default=2, ge=1, le=10)
    include_weekends: bool = False
    remaining_days_in_period: Optional[int] = Field(default=None, ge=0)


class GantryDecision(BaseModel):
    gantry_name_or_segment: str
    action: GantryAction
    toll_cost_avoided: float
    added_minutes: int
    budget_effect: str
    value_score: float
    reason: str


class RouteSegment(BaseModel):
    segment_label: str
    road_name: str
    start_location: str
    end_location: str
    segment_type: SegmentType
    estimated_minutes: int
    estimated_cost: float
    distance_miles: float = 0.0
    tolltag_rate: Optional[float] = None
    zipcash_rate: Optional[float] = None
    rate_confidence: Optional[str] = None
    rate_source: Optional[str] = None


class MapMarker(BaseModel):
    marker_type: MarkerType
    label: str
    latitude: float
    longitude: float
    description: str


class BudgetDashboardSummary(BaseModel):
    spend_to_date: float
    budget_remaining: float
    projected_period_spend: float
    projected_overage: float
    savings_to_date: float = 0.0
    dashboard_message: str


class RouteCharge(BaseModel):
    label: str
    amount: float
    reason: str
    tolltag_rate: Optional[float] = None
    zipcash_rate: Optional[float] = None
    confidence: Optional[str] = None
    source: Optional[str] = None


class NTTATollPoint(BaseModel):
    road_name: str
    toll_point_name: str
    toll_point_code: str
    vehicle_class: str
    tolltag_rate: Optional[float]
    zipcash_rate: Optional[float]
    source_url: str
    effective_start: str
    effective_end: str
    confidence: str


class NTTARatesLookupResponse(BaseModel):
    exact_route_pricing_available: bool
    message: str
    entry_matches: List[NTTATollPoint]
    exit_matches: List[NTTATollPoint]


class ValueScoreBreakdown(BaseModel):
    road_name: str
    road_short: str
    entry_name: str
    exit_name: str
    tier_start: str
    tier_end: str
    entry_value_score: int
    exit_value_score: int
    combined_value_score: int
    wasted_behind: int
    unused_ahead: int
    paid_but_unused_reason: str
    value_loss_reason: str
    ntta_data_used: bool = True


class CommutePlanResponse(BaseModel):
    recommended_route_summary: str
    natural_route_cost: float
    optimized_route_cost: float
    estimated_savings: float
    added_minutes: int
    budget_impact: str
    gantry_decisions: List[GantryDecision]
    explanation: str
    confidence_level: str
    data_sources_used: List[str]
    map_route_polyline: str
    natural_route_polyline: str
    optimized_route_polyline: str
    route_segments: List[RouteSegment]
    map_markers: List[MapMarker]
    budget_summary: Optional[BudgetDashboardSummary] = None
    recommended_strategy: Optional[str] = None
    route_value_score: Optional[float] = None
    toll_minutes_used: Optional[int] = None
    service_road_minutes: Optional[int] = None
    avoided_charges: List[RouteCharge] = Field(default_factory=list)
    paid_charges: List[RouteCharge] = Field(default_factory=list)
    value_score_breakdown: List[ValueScoreBreakdown] = Field(default_factory=list)
    entry_value_score: Optional[int] = None
    exit_value_score: Optional[int] = None
    combined_value_score: Optional[int] = None
    paid_but_unused_reason: Optional[str] = None
    value_loss_reason: Optional[str] = None
    ntta_data_used: bool = False
    google_routes_data_used: bool = False


class TripSaveRequest(BaseModel):
    commute_plan_id: str = Field(..., min_length=1)
    user_label: str = Field(..., min_length=1)


class TripSaveResponse(BaseModel):
    status: str
    message: str
    saved_trip_id: str


class BudgetStatusResponse(BaseModel):
    budget_period: BudgetPeriod
    budget_limit: float
    estimated_spend: float
    remaining_budget: float
    status: str
    budget_summary: Optional[BudgetDashboardSummary] = None
