# Tollio AI Submission Summary

## Project

Tollio AI

## Founder / Builder

Anand Meenakshi Sundaram

## One-Line Pitch

Tollio AI is a budget-aware toll routing agent that helps drivers pay only for toll segments that create real route value.

## Problem

Navigation apps usually treat toll routing as a blunt switch: use tolls or avoid tolls. Real commuters need a more precise answer: which gantry, connector, bridge, or toll segment is actually worth the money today?

## Solution

Tollio compares toll-road time, service-road time, cost, budget pressure, urgency, and segment value. It recommends a route strategy, shows which tolls were paid or avoided, explains why the strategy wins, and displays the impact on the selected toll budget.

## Core Innovation

The Gantry Intelligence Engine and Route Value Optimizer analyze toll decisions at gantry and segment level. Tollio can evaluate full toll, delayed toll entry, early toll exit, service road to destination, connector/bridge avoidance, and max-value-after-paid-gantry strategies.

## Technical Architecture

- FastAPI backend for commute planning, trip save, budget status, and system status.
- Mock-first Google Routes adapter with map-ready route segments and markers.
- Deterministic route value scoring engine.
- Gemini-ready explanation layer that explains provided deterministic outputs.
- MongoDB/MCP-ready persistence and agent tool interfaces.
- Vite React demo dashboard for local judging.

## Demo Scenario

Use the preset: Frisco to Downtown Dallas under an $8 daily toll budget.

The demo shows:

- Recommended strategy and route value score
- Paid toll charges and avoided toll charges
- Toll-road, service-road, and local-road minutes
- Natural cost, optimized cost, savings, and added minutes
- Gantry decisions and map markers
- Budget remaining and driver-friendly explanation

## Google / Gemini / MongoDB Readiness

Mock mode is the default and requires no credentials.

- Google Routes is live-gated by `ENABLE_LIVE_ROUTES=true` plus `GOOGLE_MAPS_API_KEY`.
- Gemini is live-gated by `TOLLIO_AGENT_MODE=live` plus `GEMINI_API_KEY`; Gemini is constrained to explain, not invent or change route decisions.
- MongoDB Atlas is live-gated by `TOLLIO_STORAGE_MODE=mongodb` plus `MONGODB_URI`.
- MCP alignment is represented through agent memory tool interfaces for trips, budgets, recent commutes, and savings.

## What Is Working Now

- Backend API and route contracts
- Deterministic toll route value scoring
- Mock map-style demo dashboard
- Mock persistence and readiness checks
- API, agent, and demo build tests

## Known Limitations

- No live Google Maps rendering yet; the dashboard uses SVG/CSS mock map visualization.
- Live Google Routes, Gemini, and MongoDB require credentials and explicit mode flags.
- Toll data is mock scenario data until live provider integration is enabled.
