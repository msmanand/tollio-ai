# Tollio AI

Built by Anand Meenakshi Sundaram.

Tollio AI is a budget-aware toll routing agent that helps drivers decide which tolls are worth paying, which gantries to avoid, and how to stay under a daily, weekly, monthly, or yearly toll budget.

AI coding tools may assist implementation, but product strategy, architecture, and the Gantry Intelligence concept are founder-led.

## What Works Now

- FastAPI backend for commute planning, trip save, budget status, and system status.
- Mock Google Routes adapter with route segments, map markers, toll/service/local road data, and no live API calls by default.
- Deterministic Gantry Intelligence Engine and Route Value Optimizer.
- Browser demo dashboard with a mock map-style route view, paid/avoided tolls, route value score, budget impact, and gantry decisions.
- Mock-first MongoDB/MCP persistence interfaces and Gemini-ready explanation layer.
- API, agent, and demo build verification.

## Run API

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

Open `http://localhost:5173`. The demo calls `http://localhost:8000` by default.

## Run Tests

```sh
cd services/api
source .venv/bin/activate
pip install -r requirements.txt
pytest

cd ../agent
source .venv/bin/activate
pip install -r requirements.txt
pytest

cd ../../apps/demo
npm install
npm run build
```

## Mock And Live Modes

Mock mode is the default for safe judging and local demos. No credentials are required.

- Google Routes live mode requires `ENABLE_LIVE_ROUTES=true` and `GOOGLE_MAPS_API_KEY`.
- MongoDB live mode requires `TOLLIO_STORAGE_MODE=mongodb` and `MONGODB_URI`.
- Gemini live mode requires `TOLLIO_AGENT_MODE=live` and `GEMINI_API_KEY`.

No secrets are committed. Live calls are intentionally gated.

## Demo Materials

- [Hackathon demo script](docs/demo/hackathon-demo-script.md)
- [Submission summary](docs/demo/submission-summary.md)
- [Demo verification](docs/demo/demo-verification.md)
- [Final audit report](docs/demo/final-audit-report.md)

## Repository Layout

- `apps/demo`: Local browser demo dashboard
- `apps/mobile`: React Native Expo mobile workspace placeholder
- `services/api`: FastAPI backend
- `services/agent`: Agent/tooling skeleton
- `packages/shared`: Shared package workspace
- `docs`: Product, architecture, setup, backlog, and demo docs
