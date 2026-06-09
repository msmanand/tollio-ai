# TOL-ADR-001: Agent Structure

## Status

Accepted

## Decision

Use a single Tollio commute agent with tool-based orchestration.

## Why

This matches the hackathon scope, keeps the implementation easy to test, and gives Tollio AI a clear path to future MCP integration. A single agent can coordinate route options, toll estimates, gantry intelligence, budget status, and trip saving while the tool boundaries remain stable.

## Alternatives Considered

- Multi-agent swarm: deferred because it would add orchestration complexity before the core commute contract is proven.
- Direct backend-only logic: deferred because Tollio AI needs an agent layer that can later connect to Gemini and Agent Builder patterns.
- Mobile-only logic: rejected because budget-aware gantry intelligence should be reusable across clients.

## Future Migration Path

Later prompts can connect the current tools to MCP, Google Routes API, MongoDB, and live Gemini calls without replacing the public agent input/output contract.
