# Demo Verification

These commands verify the current `main` branch in safe mock mode. No live API keys or paid calls are required.

Run commands from the repository root unless noted.

## API Tests

```sh
cd services/api
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Agent Tests

```sh
cd services/agent
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Demo Build

```sh
cd apps/demo
npm install
npm run build
```

## Run API Locally

```sh
cd services/api
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

## Run Demo Dashboard

```sh
cd apps/demo
npm install
npm run dev
```

Open `http://localhost:5173`.

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

Verify the response includes:

- `recommended_strategy`
- `route_value_score`
- `toll_minutes_used`
- `service_road_minutes`
- `avoided_charges`
- `paid_charges`
- `route_segments`
- `map_markers`
- `gantry_decisions`
- `budget_summary`

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

Verify the response includes daily budget limit, estimated spend, remaining budget, status, and budget summary.
