# TTC Delay Prediction — Web client

React + TypeScript + Vite + Tailwind CSS + MapLibre GL. Single-page app: filters (vehicle, month, day, hour), heatmap, KPIs.

## Prerequisites

- **Node.js** 18+ (recommended; Vite 5 is pinned for broad compatibility)
- The **API** running (see [`../server/README.md`](../server/README.md)) — default `http://localhost:8000`

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

Opens the Vite dev server (default **http://localhost:5173**).

### Point the UI at a different API

By default the app calls `http://localhost:8000` (see `src/lib/api.ts`). To override:

```bash
VITE_API_URL=http://127.0.0.1:8000 npm run dev
```

Create a `.env` or `.env.local` in `client/` if you prefer:

```env
VITE_API_URL=http://localhost:8000
```

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
