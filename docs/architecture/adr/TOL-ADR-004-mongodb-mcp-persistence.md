# TOL-ADR-004: MongoDB MCP Persistence

## Status

Accepted

## Decision

Use a MongoDB MCP-ready persistence layer for trip memory, budget profile, and savings history.

## Why

MongoDB aligns with the hackathon partner track, fits document-style commute history, and gives the future Tollio agent a natural memory store for saved trips, budget preferences, and accumulated savings summaries.

## Alternatives Considered

- Supabase/Postgres: strong relational option, but less aligned with the MongoDB partner track and document-shaped commute memory.
- Local-only storage: useful for demos, but not enough for user history or future agent memory.
- Direct file storage: simple, but brittle and not suitable for multi-device or agent workflows.

## Future Migration Path

Connect the repositories and agent memory tool to the official MongoDB MCP server and a live Atlas cluster. Mock mode remains the default for local tests and demos without credentials.
