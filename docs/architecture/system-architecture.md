# Tollio AI System Architecture

## Purpose

This document records the intended architecture direction for Tollio AI. It is a foundation artifact only; implementation will be introduced in later prompt IDs.

## Planned Components

- `apps/mobile`: React Native Expo client for driver-facing budget-aware toll routing.
- `services/api`: FastAPI boundary for mobile clients and backend orchestration.
- `services/agent`: Gemini and Google Cloud Agent Builder / ADK agent workspace.
- `packages/shared`: Shared contracts, types, and cross-workspace definitions.
- MCP layer: Planned integration point for tool and data access.
- MongoDB: Planned partner-track persistence layer.
- Google Routes API: Planned routing and route metadata provider.
- Gantry Intelligence Engine: Planned segment-level analysis layer for toll gantries.

## Foundation Constraint

No product features, routing decisions, agent workflows, database models, or API endpoints are implemented in this prompt.
