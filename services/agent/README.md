# Tollio AI Agent

Single-agent skeleton for Tollio AI commute recommendations.

Agent name: `tollio_commute_agent`

This service is Gemini / Google ADK-compatible in structure, but TOL-P02 runs deterministic mock orchestration only. It does not call Gemini, Google Routes API, MongoDB, MCP, or external paid APIs.

## Setup

```sh
cd services/agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run Mock Agent

```sh
TOLLIO_AGENT_MODE=mock python main.py
```

## Run Tests

```sh
pytest
```

## Future Integration Points

- Gemini / Google ADK: replace mock orchestration with live model coordination.
- Google Routes API: replace `route_options_tool` placeholder output.
- Toll provider or Google tollInfo: replace `toll_estimate_tool` placeholder output.
- MCP: expose tool calls through a standard tool server.
- MongoDB: replace `save_trip_tool` mock persistence.
