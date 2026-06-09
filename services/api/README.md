# Tollio AI API

FastAPI backend contracts for the Tollio AI agentic commute planning flow.

This service currently uses deterministic placeholder responses only. It does not call Gemini, Google Routes API, MongoDB, MCP, or any external paid API.

## Verification

Setup command:

```sh
cd services/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run API command:

```sh
uvicorn main:app --reload
```

Run tests command:

```sh
pytest
```

Sample commute plan request:

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
