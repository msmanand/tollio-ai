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
