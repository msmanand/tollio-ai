# Tollio AI Hackathon Demo Script

## 60-Second Pitch

Tollio AI is a budget-aware toll routing agent built by Anand Meenakshi Sundaram. Instead of asking drivers to choose only "use tolls" or "avoid tolls," Tollio asks which tolls are actually worth paying.

The core innovation is the Gantry Intelligence Engine with Route Value Optimization. Tollio evaluates full toll, delayed toll entry, early toll exit, service-road continuation, connector/bridge avoidance, and budget-pressure strategies. It shows paid tolls, avoided tolls, toll-road minutes, service-road minutes, savings, added time, and budget impact.

For the demo, the driver wants to go from Frisco to Downtown Dallas by 8:30 while staying under an $8 daily toll budget. Tollio returns a route value recommendation and a mock map-style dashboard. Google Routes, Gemini, and MongoDB are readiness-enabled and live-gated; mock mode is the safe default.

## 3-Minute Walkthrough

1. Start the API:

```sh
cd services/api
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

2. Start the demo dashboard in another terminal:

```sh
cd apps/demo
npm install
npm run dev
```

3. Open `http://localhost:5173`.

4. Click `Frisco to Downtown Dallas under $8`.

5. Click `Plan Commute`.

6. Walk through the top metrics:
   - toll-road minutes
   - service-road minutes
   - route value score
   - natural cost
   - optimized cost
   - savings
   - budget remaining

7. Show the `Route Value Intelligence` panel:
   - recommended strategy
   - tolls paid
   - tolls avoided
   - why the route wins

8. Show the mock map:
   - blue toll segments
   - green service-road segments
   - origin, gantry, exit, reentry, and destination markers

9. Scroll to raw debug lists:
   - gantry decisions
   - route segments
   - map markers
   - explanation

10. Close with the live-readiness story:
    - Google Routes can provide live route geometry and tollInfo when enabled.
    - Gemini can explain deterministic outputs without changing them.
    - MongoDB/MCP can store commute memory, budgets, and savings history.

## Closing Line

Tollio turns toll routing from a blunt setting into a budget-aware route value decision.
