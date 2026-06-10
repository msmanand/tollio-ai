# Tollio AI Submission Summary

## Project Name

Tollio AI

## Founder / Builder

Anand Meenakshi Sundaram

## One-Line Description

Tollio AI is a budget-aware toll routing agent that helps drivers decide which toll gantries are worth paying.

## Problem

Drivers often face repeated toll scanners without knowing which ones meaningfully improve arrival time and which ones quietly drain the daily, weekly, or monthly toll budget.

## Technical Architecture

- FastAPI backend contracts for commute planning, trip save, budget status, and system status.
- Google Routes adapter boundary for mock-first and live-gated route data.
- Deterministic Gantry Intelligence Engine for segment-level toll decisions.
- Agent skeleton with tool-based orchestration.
- MongoDB/MCP-ready persistence direction for trip memory, budgets, and savings.
- Gemini-ready explanation layer that explains deterministic decisions without changing them.

## Agent Workflow

1. Receive commute request with origin, destination, arrival time, urgency, vehicle cost inputs, and toll budgets.
2. Get route options through the route adapter.
3. Score gantry and segment decisions with the deterministic engine.
4. Explain budget and time tradeoffs.
5. Save trip and inspect budget state.

## Partner MCP Usage

MongoDB/MCP is intended for saved commute memory, budget profiles, and savings history. The project is designed so future MCP tools can attach to repository and agent-memory boundaries without changing the commute contract.

## Google Cloud / Gemini Usage

Google Routes and Gemini are live-gated/readiness-enabled. Google Routes is the future route data provider. Gemini is the future explanation/orchestration layer, constrained to explain provided deterministic decisions only.

## Demo Scenario

"Get me from Frisco to Downtown Dallas by 8:30, but keep me under my $8 daily toll budget."

The demo returns route segments, map markers, optimized toll cost, estimated savings, added minutes, gantry decisions, and budget impact.

## What Is Working Now

- FastAPI commute planning contract.
- Mock route adapter with map-ready route segments and markers.
- Deterministic Gantry Intelligence Engine.
- Trip save and budget status placeholder endpoints.
- API and agent test suites.
- End-to-end demo flow coverage when present on the active branch.

## Mock-Gated vs Live-Ready

- Mock mode is default for safe judging and local demos.
- Google Routes is live-gated by `ENABLE_LIVE_ROUTES=true` plus an API key.
- MongoDB is live-gated by `TOLLIO_STORAGE_MODE=mongodb` plus a MongoDB URI.
- Gemini is live-gated by `TOLLIO_AGENT_MODE=live` plus a Gemini API key.

No real credentials are committed, and live calls are not required for demo verification.

## Future Roadmap

1. Merge live-readiness and live-provider branches into main.
2. Enable Google Routes live smoke test.
3. Enable MongoDB Atlas persistence.
4. Enable Gemini explanation layer.
5. Build the React Native Expo mobile demo.
6. Expand gantry metadata and toll-provider coverage.
