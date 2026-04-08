# TTC Delay Prediction — Web client

React + TypeScript + Vite + Tailwind CSS + MapLibre GL. Single-page app: filters (vehicle, month, day, hour), heatmap, KPIs.

## Prerequisites

- **Node.js** 18+ (recommended; Vite 5 is pinned for broad compatibility)
- The **API** running (see [`../server/README.md`](../server/README.md))

## How the client finds the API

| Situation | Behaviour |
|-----------|------------|
| **`VITE_API_URL` is set** (e.g. in `.env.local`) | All requests use that base URL only. |
| **Not set** (default dev) | Tries **`http://localhost:8000`**, then **`http://127.0.0.1:8001`**. Use this when port **8000** is occupied by another app and you run this project’s FastAPI on **8001**. |

Set `VITE_API_URL` explicitly in production or when you want a single predictable URL (no fallback).

**CORS:** The browser origin must match what the API allows (`localhost` vs `127.0.0.1` are different origins). The server defaults include `http://localhost:5173`, `http://localhost:5174`, `http://127.0.0.1:5173`, and `http://127.0.0.1:5174` — see `server/app/config.py`.

## Install

From the **repository root**:

```bash
cd client
npm install
```

## Run (development)

```bash
npm run dev
```

Vite prints the local URL (often **http://localhost:5173**; if 5173 is in use it may use **5174** or another free port).

### Point the UI at a specific API

Create **`.env`** or **`.env.local`** in `client/` (restart `npm run dev` after changes):

```env
VITE_API_URL=http://127.0.0.1:8001
```

Or one-off:

```bash
VITE_API_URL=http://localhost:8000 npm run dev
```

If you see **Unable to fetch heatmap data**, something on **8000** may not be this project’s FastAPI (HTML error pages instead of JSON), or CORS does not include your exact dev origin. Fix by running Uvicorn on a free port, setting `VITE_API_URL`, and ensuring `CORS_ORIGINS` on the server matches how you open the app (`localhost` vs `127.0.0.1`).

## Build for production

```bash
npm run build
```

Output is in `dist/`. Serve `dist/` with any static host; set `VITE_API_URL` at **build time** to your production API URL.

Preview the production build locally:

```bash
npm run preview
```

## Lint

```bash
npm run lint
```
