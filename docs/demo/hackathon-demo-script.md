# Tollio AI Hackathon Demo Script

## 60-Second Pitch

Tollio AI is a budget-aware toll routing agent built by Anand Meenakshi Sundaram. Most navigation apps treat toll roads as a binary choice: use tolls or avoid tolls. Tollio asks a sharper question: which toll gantries are actually worth paying today?

The core innovation is the Gantry Intelligence Engine. It looks at toll roads at the gantry and segment level, compares toll avoided, added minutes, signal penalty, urgency, and the driver's daily, weekly, or monthly toll budget, then recommends where to stay on toll, where to exit, and where to re-enter.

For the demo, the driver asks: "Get me from Frisco to Downtown Dallas by 8:30, but keep me under my $8 daily toll budget." Tollio returns a structured commute plan with route segments, map markers, gantry decisions, budget impact, and an explanation. Google Routes, Gemini, and MongoDB are live-gated/readiness-enabled; mock mode is the safe default for judging and local demos.

## 3-Minute Demo Script

1. Start with the problem: Dallas-area drivers can spend heavily on tolls without knowing which individual scanners are worth paying.
2. Show the API status endpoint to confirm safe mock mode:
   `GET /api/v1/system/status`
3. Send the commute request:
   Frisco to Downtown Dallas, arrival by 8:30, balanced urgency, $8 daily toll budget.
4. Highlight the response:
   route segments, map markers, natural toll cost, optimized toll cost, estimated savings, added minutes, and gantry decisions.
5. Explain the Gantry Intelligence Engine:
   it scores segment-level strategies instead of only saying "use toll" or "avoid toll."
6. Show that the trip can be saved:
   `POST /api/v1/trips/save`
7. Show budget status:
   `GET /api/v1/budget/status`
8. Close with the roadmap:
   live Google Routes, live MongoDB Atlas, and live Gemini can be enabled behind explicit readiness gates.

## Problem

Drivers need toll decisions that are budget-aware, time-aware, and specific to the gantries they will actually pass.

## Solution

Tollio AI produces a commute recommendation that explains which toll segments to pay, which gantries to skip, how many minutes are added, and how the route affects the selected toll budget.

## Why Google / Agentic AI

Google Routes is the natural source for route geometry, travel time, distance, and future tollInfo. Gemini can explain deterministic route and gantry decisions in driver-friendly language. The agent layer coordinates tools while preserving Tollio's deterministic engine as the source of truth.

## Where Gemini Fits

Gemini is intended to explain the route and budget tradeoffs. It must not invent route data or change toll decisions. The current explanation layer is mock-first and live-gated.

## Where MCP / MongoDB Fits

MongoDB is the future memory layer for saved commutes, budget profiles, and savings history. MCP can expose those memory tools to the agent. Current persistence is mock-first or live-ready depending on branch integration state.

## Where Google Routes Fits

Google Routes provides the future live route adapter for driving routes, traffic-aware duration, distance, polyline, and tollInfo. Mock mode is the default; live calls require explicit environment gates and credentials.

## Core Innovation

The Gantry Intelligence Engine analyzes toll gantries and route segments individually, comparing toll avoided, added minutes, estimated signal penalty, budget pressure, urgency mode, and value score.

## Closing Line

Tollio AI turns toll routing from a blunt setting into a budget-aware driving decision.
