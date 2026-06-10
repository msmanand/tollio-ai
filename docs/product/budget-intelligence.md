# Budget Intelligence

Tollio AI converts a driver toll budget into practical guidance for each commute. The goal is not just to say whether a route is affordable, but to show how much toll spend is safe for this trip and how aggressively the Gantry Intelligence Engine should avoid low-value scanners.

## How User Budgets Work

Drivers can provide a daily, weekly, monthly, or yearly toll budget. Tollio estimates how many commute trips remain in that budget period and turns the remaining budget into a recommended per-trip allowance.

Inputs used by the deterministic budget engine:

- Budget amount and period
- Current period spend
- Commute days per week
- Trips per commute day
- Whether weekend travel should count
- Remaining days in the period, when available
- Planned toll cost for the candidate trip
- Urgency mode

The approximation is intentionally simple for the hackathon foundation. Calendar precision can improve later, but current behavior is deterministic and testable.

## Examples

Daily budget:

- Budget: $8 today
- Current spend: $2
- Trips left today: 2
- Recommended allowance: $3 per trip
- A $3 planned toll trip remains on track.

Weekly budget:

- Budget: $50 this week
- Current spend: $10
- Commute pattern: 5 days, 2 trips per day
- Estimated trips remaining: 10
- Recommended allowance: $4 per trip.

Monthly budget:

- Budget: $200 this month
- Current spend: $20
- Remaining calendar days: 14
- Weekends excluded, 5 commute days per week
- Estimated commute days remaining: 10
- Estimated trips remaining: 20
- Recommended allowance: $9 per trip.

Yearly budget:

- Budget: $2,400 this year
- Current spend: $400
- Commute pattern: 5 days, 2 trips per day
- Estimated trips remaining: 520
- Recommended allowance: about $3.85 per trip.

## How Budget Pressure Affects Gantry Decisions

The budget engine produces budget status and forecast status:

- `under_budget`: the driver still has comfortable remaining budget.
- `close_to_limit`: remaining budget is low.
- `over_budget`: current spend already exceeds the selected period budget.
- `on_track`: planned toll spend fits the per-trip allowance.
- `at_risk`: planned toll spend exceeds the allowance but does not yet project a hard overage.
- `projected_over`: the trip or remaining pattern is projected to exceed the period budget.

When budget pressure is high, the Gantry Intelligence Engine can recommend stronger toll avoidance. That includes skipping low-value gantries, exiting earlier, staying on service roads longer when time impact is acceptable, or avoiding a toll segment entirely. Urgent mode can still prefer time savings, but over-budget trips receive clear warnings.

## Dashboard Metrics

Commute planning and budget status responses include a dashboard-ready budget summary:

- `spend_to_date`
- `budget_remaining`
- `projected_period_spend`
- `projected_overage`
- `savings_to_date`
- `dashboard_message`

These fields are designed for future mobile and demo dashboards without requiring live Google Routes, Gemini, or MongoDB credentials.
