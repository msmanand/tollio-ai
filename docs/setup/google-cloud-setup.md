# Google Cloud Setup

This guide prepares Tollio AI for future Google Routes and Gemini use. Do not commit real keys.

## Google Routes

1. Open the Google Cloud Console.
2. Create or select a project for Tollio AI.
3. Enable billing only when you are ready for live route calls.
4. Enable the Routes API.
5. Create an API key under APIs & Services > Credentials.
6. Restrict the key to the Routes API and appropriate app or server origins.

Expected environment variables:

```sh
ENABLE_LIVE_ROUTES=false
GOOGLE_MAPS_API_KEY=
```

Set `ENABLE_LIVE_ROUTES=true` only when you intentionally want live Google Routes calls and have a valid API key.

## Gemini

1. Open Google AI Studio or the Google Cloud console path used by the project.
2. Create an API key for Gemini.
3. Keep the key in local environment configuration only.

Expected environment variables:

```sh
TOLLIO_AGENT_MODE=mock
GEMINI_API_KEY=
GOOGLE_CLOUD_PROJECT=your-google-cloud-project-id
GOOGLE_APPLICATION_CREDENTIALS=
```

Set `TOLLIO_AGENT_MODE=live` only when live Gemini calls are intentionally enabled.
