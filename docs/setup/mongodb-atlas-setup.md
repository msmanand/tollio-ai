# MongoDB Atlas Setup

This guide prepares Tollio AI for future MongoDB Atlas and MCP-backed persistence. Do not commit real connection strings.

## Create A Free Cluster

1. Sign in to MongoDB Atlas.
2. Create a project for Tollio AI.
3. Create a free cluster.
4. Add a database user with the least permissions needed for the app.
5. Add a local IP allowlist entry for development, or configure the deployment environment allowlist.

## Generate URI

1. Click Connect on the Atlas cluster.
2. Choose the driver connection option.
3. Copy the connection string.
4. Replace username, password, and database placeholders locally.

Expected environment variables:

```sh
TOLLIO_STORAGE_MODE=mock
MONGODB_URI=
MONGODB_DATABASE=tollio_ai
```

Set `TOLLIO_STORAGE_MODE=mongodb` only when a real Atlas URI is available and live persistence is intended.

## MCP Future Path

Tollio AI will later connect repositories and agent memory tools to the official MongoDB MCP server. Until then, mock mode keeps local development and tests credential-free.
