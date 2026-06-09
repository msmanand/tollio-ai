# Runtime Modes

Tollio AI defaults to mock mode for every external integration.

## Status Endpoint

Run the API and inspect readiness:

```sh
curl http://localhost:8000/api/v1/system/status
```

The response includes:

```json
{
  "api_status": "ok",
  "routes_mode": "mock",
  "mongodb_mode": "mock",
  "agent_mode": "mock",
  "google_routes_ready": false,
  "mongodb_ready": false,
  "gemini_ready": false,
  "warnings": []
}
```

## Mock Mode

Use mock mode for local development, tests, and demos without live API calls:

```sh
ENABLE_LIVE_ROUTES=false
TOLLIO_STORAGE_MODE=mock
TOLLIO_AGENT_MODE=mock
```

## Live Readiness

Google Routes is ready when:

```sh
ENABLE_LIVE_ROUTES=true
GOOGLE_MAPS_API_KEY=...
```

MongoDB is ready when:

```sh
TOLLIO_STORAGE_MODE=mongodb
MONGODB_URI=...
```

Gemini is ready when:

```sh
TOLLIO_AGENT_MODE=live
GEMINI_API_KEY=...
```

Readiness does not mean the app should automatically make paid calls. Live integrations should be enabled only in the specific future prompts that intentionally wire them.
