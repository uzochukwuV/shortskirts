# Dysentry Frontend

## Project Context

This is the Dysentry frontend app. Treat it as user-owned application code, keep changes focused on the user's request, and preserve existing project conventions.

## Key Files

- `src/`: frontend application source.
- `src/api/base44Client.js`: frontend HTTP API client.
- `src/api/dysentryClient.js`: domain-level API mappings and helpers.
- `vite.config.js`: Vite config and dev server setup.

## Working Notes

- Use `pnpm run dev` as the default local development command.
- The backend API base URL is configured via `VITE_API_BASE_URL`.
- Prefer the existing `dysentryClient.js` mappings for domain operations.
- Reuse the existing `base44Client.js` HTTP client for new API calls.
