# TOL-ADR-002: Google Routes Adapter

## Status

Accepted

## Decision

Add a Google Routes adapter with a mock-first/live-gated design.

## Why

The hackathon demo needs map-aligned route contracts, route segments, polylines, and map markers. Live Google Routes API calls should be controlled so local development, tests, and review flows do not require API keys or incur paid usage by default.

## Alternatives Considered

- Static route data: simple, but it would keep map logic buried in the commute planner instead of behind a provider boundary.
- Direct mobile Google Maps calls: deferred because the backend and agent need stable route contracts before mobile UI work.
- Third-party toll API first: deferred because Google Routes alignment is the next required platform integration path.

## Future Migration Path

Enable live Google Routes API in TOL-P06 or later by setting `ENABLE_LIVE_ROUTES=true` and providing `GOOGLE_MAPS_API_KEY`. The adapter can then normalize live route payloads into the existing Tollio route option, segment, marker, and polyline contract.
