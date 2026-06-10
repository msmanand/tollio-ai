# Tollio AI

Tollio AI is a Google Cloud Rapid Agent Hackathon project.

Built by Anand Meenakshi Sundaram.

AI coding tools may assist implementation, but product strategy, architecture, and the Gantry Intelligence concept are founder-led.

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

This commit establishes only the traceable project foundation. Product features, routing logic, agent behavior, API contracts, MCP integration, Google Routes integration, MongoDB persistence, and mobile demo screens are intentionally deferred to later prompt IDs.

## Hackathon Demo

Demo materials:

- [Hackathon demo script](docs/demo/hackathon-demo-script.md)
- [Submission summary](docs/demo/submission-summary.md)
- [Demo verification](docs/demo/demo-verification.md)

Mock mode is the default for safe judging and local demos. Google Routes, MongoDB, and Gemini are live-gated/readiness-enabled, and the deterministic Gantry Intelligence Engine is the core working logic.

## Verification

To verify the foundation:

1. Confirm the branch with `git status --short --branch`.
2. Confirm Node 22 is standardized with `cat .nvmrc`.
3. Confirm npm workspaces are declared with `cat package.json`.
4. Confirm placeholder-only environment keys with `cat .env.example`.
5. Confirm the traceable backlog with `cat docs/backlog/TOL-BACKLOG.md`.
6. Confirm no product features are implemented by checking that app, service, and package workspaces contain only foundation placeholders.
7. Run `npm install`, `npm run --if-present lint`, and `npm run --if-present test` when npm is available.
