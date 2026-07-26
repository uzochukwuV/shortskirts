# Dysentry Frontend

React frontend for the Dysentry story creation platform.

## Prerequisites

1. Node.js 18+ and npm/pnpm
2. The StoryForge backend running (default: `http://localhost:3001`)

## Run Locally

```bash
pnpm install
pnpm run dev
```

The frontend dev server starts on `http://localhost:5000` by default.

## Environment Variables

Create a `.env` file in the `web/` directory:

```bash
VITE_API_BASE_URL=http://localhost:3001
```

`VITE_API_BASE_URL` points the frontend at the backend API. If not set, requests fall back to the same origin.

## Build

```bash
pnpm run build
```

## Project Structure

- `src/api/` — API clients (`base44Client.js` for raw HTTP, `dysentryClient.js` for domain mapping)
- `src/pages/` — Route-level pages
- `src/components/` — Reusable UI components
- `src/lib/` — Auth context, query client, utilities
