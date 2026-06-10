# TOL-ADR-005: Live Integration Readiness

## Status

Accepted

## Decision

Prepare all external integrations behind readiness checks before enabling live mode.

## Why

This avoids accidental paid API usage and keeps local development simple. Developers can verify whether Google Routes, MongoDB, and Gemini are configured without requiring real credentials or making live calls.

## Alternatives Considered

- Always-live mode: rejected because it risks paid usage and breaks local development without credentials.
- Environment-specific code branches: rejected because behavior should be driven by runtime configuration, not divergent code.
- Hardcoded secrets: rejected because secrets must never be committed.

## Future Migration

- TOL-P07 Google Routes Live
- TOL-P08 MongoDB Atlas Live
- TOL-P09 Gemini Live
