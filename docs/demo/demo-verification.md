# Demo Verification

These commands verify the current `main` branch in safe mock mode. No live API keys or paid calls are required.

Run commands from the repository root unless noted.

## Run API Tests

```sh
cd services/api
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Run Agent Tests

```sh
cd services/agent
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Run API Locally

```sh
cd services/api
source .venv/bin/activate
uvicorn main:app --reload
```

## System Status

```sh
curl http://localhost:8000/api/v1/system/status
```

Expected safe demo posture: mock mode by default, no live credentials required.

## Plan Demo Commute

```sh
curl -X POST http://localhost:8000/api/v1/commute/plan \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "Frisco",
    "destination": "Downtown Dallas",
    "arrival_time": "08:30",
    "urgency_mode": "balanced",
    "daily_budget": 8,
    "weekly_budget": 40,
    "monthly_budget": 160,
    "budget_period": "daily",
    "toll_pass_type": "NTTA TollTag",
    "vehicle_mpg": 28,
    "gas_price": 3.25,
    "avoid_excessive_signals": true
  }'
```

Verify the response includes route segments, map markers, gantry decisions, optimized toll cost, estimated savings, added minutes, and budget impact.

## Save Trip

```sh
curl -X POST http://localhost:8000/api/v1/trips/save \
  -H "Content-Type: application/json" \
  -d '{
    "commute_plan_id": "demo-frisco-downtown-0830",
    "user_label": "Frisco to Downtown Dallas by 8:30"
  }'
```

## Check Budget Status

```sh
curl http://localhost:8000/api/v1/budget/status
```

Verify the response includes daily budget limit, estimated spend, remaining budget, and status.
