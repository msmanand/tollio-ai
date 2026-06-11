# Tollio AI

Tollio AI is a Google Cloud Rapid Agent Hackathon project.

Built by Anand Meenakshi Sundaram.

AI coding tools may assist implementation, but product strategy, architecture, and the Gantry Intelligence concept are founder-led.

## Submission Runtime Quick Start

- Repository: `https://github.com/msmanand/tollio-ai`
- License: MIT, see `LICENSE`
- Local API:

```sh
cd services/api
source .venv/bin/activate
uvicorn main:app --reload
```

- Local demo dashboard:

```sh
cd apps/demo
source /Users/tsp00/.nvm/nvm.sh
nvm use 22
npm install
npm run dev
```

- Gemini runtime proof endpoint:

```sh
curl http://localhost:8000/api/v1/demo/gemini-invocation
```

- MongoDB runtime proof endpoint:

```sh
curl http://localhost:8000/api/v1/demo/mongodb-invocation
```

- Seed NTTA matrix data to MongoDB Atlas after setting `MONGODB_URI`:

```sh
python scripts/seed_ntta_to_mongodb.py
```

- Agent Builder / ADK-compatible runtime command:

```sh
cd services/agent
source .venv/bin/activate
python -m app.tollio_agent_runtime
```

- MongoDB MCP config path: `services/agent/mcp.mongodb.json`
- Required env vars for live integrations:
  - Gemini: `TOLLIO_AGENT_MODE=live`, `GEMINI_API_KEY=...`
  - MongoDB: `TOLLIO_STORAGE_MODE=mongodb`, `MONGODB_URI=...`, `MONGODB_DATABASE=tollio_ai`
  - Demo hosting CORS: `TOLLIO_CORS_ORIGINS=https://YOUR_VERCEL_APP.vercel.app`
  - Demo API URL: `VITE_TOLLIO_API_URL=https://YOUR_API_HOST`
- Test commands:

```sh
cd services/api && source .venv/bin/activate && pytest
cd ../../services/agent && source .venv/bin/activate && pytest
cd ../../apps/demo && source /Users/tsp00/.nvm/nvm.sh && nvm use 22 && npm install && npm run build
```

## Thesis

Tollio AI is a budget-aware toll routing agent that helps drivers decide which toll gantries are worth paying, when to exit before unnecessary toll scanners, and how to stay under daily, weekly, or monthly toll budgets.

## Core Innovation

Gantry Intelligence Engine: analyzes toll roads at gantry and segment level instead of only deciding "use toll" or "avoid toll."

## Stack Direction

- Gemini
- Google Cloud Agent Builder / ADK
- MCP
- Google Routes API
- FastAPI
- React Native Expo
- MongoDB partner track

## Repository Layout

- `apps/mobile`: React Native Expo mobile app workspace
- `services/api`: FastAPI service workspace
- `services/agent`: Gemini / Google Cloud Agent Builder / ADK agent workspace
- `packages/shared`: Shared contracts and utilities workspace
- `docs/product`: Product specs
- `docs/architecture`: Architecture notes
- `docs/demo`: Demo narrative
- `docs/backlog`: Traceable prompt backlog

## Foundation Status

The repository now includes the mock-mode FastAPI commute planning API, mock-mode agent skeleton, Google Routes adapter boundary, deterministic Gantry Intelligence Engine, and focused API/agent tests. Live Google Routes, Gemini, MongoDB/MCP, and mobile UI work remain gated or future-facing unless explicitly merged in later branches.

Tollio uses NTTA matrix data for DFW toll intelligence in the local demo. When `TOLLIO_STORAGE_MODE=mongodb` and `MONGODB_URI` are configured, NTTA matrix data and optimization run summaries are stored in MongoDB. Google Maps/Routes remains the future route geometry, ETA, and traffic input; it is not required for the NTTA matrix demo.

## Hackathon Demo

Demo materials:

- [Hackathon demo script](docs/demo/hackathon-demo-script.md)
- [Submission summary](docs/demo/submission-summary.md)
- [Demo verification](docs/demo/demo-verification.md)
- [Final audit report](docs/demo/final-audit-report.md)
- [Submission compliance](docs/demo/submission-compliance.md)

Mock mode is the default for safe judging and local demos. The working demo uses NTTA matrix data, deterministic toll intelligence, and route-value options. MongoDB and Gemini are live-gated runtime paths when credentials are configured. Google Routes is designed as the future geometry/ETA provider and remains gated.

## Hackathon Compliance

### Gemini Runtime Usage

Gemini is used as an explanation layer only. Tollio's deterministic toll decisions remain the source of truth; Gemini is instructed not to change toll decisions or invent route data.

Runtime behavior:

- Default: `TOLLIO_AGENT_MODE=mock`, no Gemini call.
- Live: `TOLLIO_AGENT_MODE=live` and `GEMINI_API_KEY` set, `services/api/app/services/explanation_service.py` calls Gemini through the Google Generative Language API.
- Safe judge endpoint: `GET /api/v1/demo/gemini-invocation`.

Verify locally without credentials:

```sh
curl http://localhost:8000/api/v1/demo/gemini-invocation
```

Verify live path after setting credentials:

```sh
export TOLLIO_AGENT_MODE=live
export GEMINI_API_KEY=YOUR_GEMINI_API_KEY
curl http://localhost:8000/api/v1/demo/gemini-invocation
```

The response includes `mode`, `gemini_configured`, `invocation_path`, `sample_explanation`, and `status`.

### MongoDB Runtime Usage

MongoDB stores official NTTA matrix documents in `ntta_matrices`, optimization run summaries in `optimization_runs`, and agent memory/tool traces through the MongoDB memory tool. The API reads NTTA roads, exits, and matrix prices from MongoDB first when `TOLLIO_STORAGE_MODE=mongodb` and `MONGODB_URI` are configured, then falls back to local JSON if MongoDB is unavailable in non-strict mode.

Seed and verify:

```sh
set -a
source .env.local
set +a
python scripts/seed_ntta_to_mongodb.py
curl http://localhost:8000/api/v1/demo/mongodb-invocation
curl http://localhost:8000/api/v1/ntta/roads
```

### Google Cloud Agent Builder-Compatible Agent Flow

The agent service in `services/agent` is structured as an Agent Builder/ADK-compatible tool flow:

1. `route_options_tool`
2. `toll_estimate_tool`
3. `gantry_intelligence_tool`
4. `budget_status_tool`
5. MongoDB memory tool boundary
6. final driver explanation

Run the deterministic agent:

```sh
cd services/agent
source .venv/bin/activate
TOLLIO_AGENT_MODE=mock python main.py
```

Run the Agent Builder / ADK-compatible runtime entry point:

```sh
cd services/agent
source .venv/bin/activate
python -m app.tollio_agent_runtime
```

### MongoDB MCP Partner Track Usage

Tollio includes a MongoDB memory/tool layer for trip memory, budget profile, recent commutes, and savings summaries.

- Runtime adapter: `services/agent/app/tools/mongodb_memory_tool.py`
- Agent call path: `services/agent/app/agent.py` calls the MongoDB memory tool during normal agent execution.
- MCP config artifact: `services/agent/mcp.mongodb.json`

Current status: MCP-ready and mock-safe by default. Do not claim live MCP unless the official MongoDB MCP server is installed and `MONGODB_URI` is configured.

### Hosted Deployment Instructions

API on Cloud Run using the included Dockerfile:

```sh
gcloud run deploy tollio-api \
  --source services/api \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars TOLLIO_AGENT_MODE=mock,TOLLIO_STORAGE_MODE=mock,TOLLIO_CORS_ORIGINS=https://YOUR_VERCEL_APP.vercel.app
```

API on Render:

1. Create a new Web Service from this repository.
2. Root directory: `services/api`.
3. Runtime: Docker.
4. Environment variables: `TOLLIO_AGENT_MODE=mock`, `TOLLIO_STORAGE_MODE=mock`, `TOLLIO_CORS_ORIGINS=https://YOUR_VERCEL_APP.vercel.app`.

Demo dashboard on Vercel:

1. Import this repository.
2. Root directory: `apps/demo`.
3. Build command: `npm run build`.
4. Output directory: `dist`.
5. Set `VITE_TOLLIO_API_URL=https://YOUR_API_HOST`.

Local smoke test before hosting:

```sh
cd services/api && source .venv/bin/activate && pytest
cd ../../apps/demo && source /Users/tsp00/.nvm/nvm.sh && nvm use 22 && npm run build
```

## Local Demo Dashboard

Run the API:

```sh
cd services/api
source .venv/bin/activate
uvicorn main:app --reload
```

Run the browser demo:

```sh
cd apps/demo
npm install
npm run dev
```

Open `http://localhost:5173`. The demo calls `http://localhost:8000` by default and stays in mock mode.

## Verification

To verify the foundation:

1. Confirm the branch with `git status --short --branch`.
2. Confirm Node 22 is standardized with `cat .nvmrc`.
3. Confirm npm workspaces are declared with `cat package.json`.
4. Confirm placeholder-only environment keys with `cat .env.example`.
5. Confirm the traceable backlog with `cat docs/backlog/TOL-BACKLOG.md`.
6. Confirm no product features are implemented by checking that app, service, and package workspaces contain only foundation placeholders.
7. Run `npm install`, `npm run --if-present lint`, and `npm run --if-present test` when npm is available.
