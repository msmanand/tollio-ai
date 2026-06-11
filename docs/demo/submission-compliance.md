# Tollio AI Submission Compliance

## Gemini Runtime

- Runtime file: `services/api/app/services/explanation_service.py`
- Proof endpoint: `GET /api/v1/demo/gemini-invocation`
- Live gate: `TOLLIO_AGENT_MODE=live` and `GEMINI_API_KEY` present
- Safe default: mock explanation, no external call

Judges can run:

```sh
cd services/api
source .venv/bin/activate
uvicorn main:app --reload
curl http://localhost:8000/api/v1/demo/gemini-invocation
```

Expected response includes:

- `mode`
- `gemini_configured`
- `invocation_path`
- `sample_explanation`
- `status`

## Agent Builder-Compatible Runtime

- Runtime file: `services/agent/app/tollio_agent_runtime.py`
- Command:

```sh
cd services/agent
source .venv/bin/activate
python -m app.tollio_agent_runtime
```

The runtime orchestrates:

- `route_options_tool`
- `toll_estimate_tool`
- `gantry_intelligence_tool`
- `budget_status_tool`
- MongoDB memory tools
- Gemini explanation tool

## MongoDB MCP

- MCP config: `services/agent/mcp.mongodb.json`
- Memory tool path: `services/agent/app/tools/mongodb_memory_tool.py`
- Runtime proof: `python -m app.tollio_agent_runtime` prints `memory_trace`

Each memory trace item includes:

- `tool_name`
- `action`
- `input`
- `output`
- `mcp_config_present`

Current status: MCP-ready and mock-safe. Live MongoDB Atlas/MCP requires `MONGODB_URI` and official MCP server setup.

## Demo Commands

API:

```sh
cd services/api
source .venv/bin/activate
uvicorn main:app --reload
```

Demo:

```sh
cd apps/demo
source /Users/tsp00/.nvm/nvm.sh
nvm use 22
npm install
npm run dev
```

Agent runtime:

```sh
cd services/agent
source .venv/bin/activate
python -m app.tollio_agent_runtime
```

## Test Results Expected

```sh
cd services/api && source .venv/bin/activate && pytest
cd ../../services/agent && source .venv/bin/activate && pytest
cd ../../apps/demo && source /Users/tsp00/.nvm/nvm.sh && nvm use 22 && npm install && npm run build
git diff --check
```

Expected:

- API tests pass
- Agent tests pass
- Demo build passes
- `git diff --check` passes

## What Judges Should Click Or Run

1. Run the API locally and call `/api/v1/demo/gemini-invocation`.
2. Run `python -m app.tollio_agent_runtime` to see the Agent Builder-compatible runtime and MongoDB memory trace.
3. Run the demo dashboard and use the NTTA road/exit dropdowns to compare toll options.
4. Review `services/agent/mcp.mongodb.json` for the MongoDB MCP configuration boundary.
