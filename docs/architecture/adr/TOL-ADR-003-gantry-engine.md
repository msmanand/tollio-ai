# TOL-ADR-003: Gantry Intelligence Engine

## Status

Accepted

## Decision

Use a deterministic gantry scoring engine for Tollio AI's first gantry and segment decisions.

## Why

Core Tollio IP should be explainable and testable, not LLM-invented. A deterministic engine lets the product compare toll avoided, added minutes, signal penalty, budget remaining, and urgency mode in a way that can be reviewed, tested, and improved as route data becomes richer.

## Alternatives Considered

- LLM-only scoring: rejected for the first engine because outputs would be harder to verify and explain.
- Static rules in the commute planner: rejected because gantry scoring is a core domain boundary and should not be buried in endpoint orchestration.
- Mobile-side scoring: rejected because gantry intelligence should be reusable by API, agent, and future clients.

## Future Migration Path

Enrich engine inputs with live Google Routes tollInfo, traffic, toll provider APIs, and more detailed gantry metadata. Future versions can improve candidate generation while preserving deterministic scoring and keeping LLMs in an explanatory or orchestration role.
