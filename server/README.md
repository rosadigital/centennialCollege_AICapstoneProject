# TTC Delay Prediction — API server

FastAPI service: model inference, heatmap data, and metadata for the web client.

## Prerequisites

- **Python** 3.10+ recommended  
- **Model artifacts** (from the EDA notebook / OOP pipeline) under `server/model_artifacts/`:
  - `model.pkl`
  - `heatmap_predictions_test_agg.csv`

Paths are resolved from the **repository root** by default (see `app/config.py`).

## Install

Use a **virtual environment** at the repo root (recommended so `lightgbm` and other deps match what loads `model.pkl`):

```bash
cd /path/to/centennialCollege_AICapstoneProject
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r server/requirements.txt
```

## Run (development)

The app package is `app` under `server/`, so Python must see the `server` directory on the path.

**From the repository root:**

```bash
source .venv/bin/activate
PYTHONPATH=server uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**From the `server/` directory:**

```bash
source ../.venv/bin/activate
PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API docs: **http://localhost:8000/docs**  
- Health: **GET** `http://localhost:8000/health`

## Environment variables

Optional overrides (see `server/.env.example`):

| Variable | Purpose |
|----------|---------|
| `ARTIFACTS_DIR` | Folder containing artifacts (default: `<repo>/server/model_artifacts`) |
| `MODEL_FILE` | Path to `model.pkl` |
| `HEATMAP_FILE` | Path to `heatmap_predictions_test_agg.csv` |
| `CORS_ORIGINS` | Comma-separated allowed browser origins (default includes `http://localhost:5173`) |

Example when running only from `server/` with relative paths:

```bash
export ARTIFACTS_DIR=./model_artifacts
export CORS_ORIGINS=http://localhost:5173
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

Or copy `server/.env.example` to `server/.env` and load it with your process manager / `python-dotenv` if you add that.

## Troubleshooting

- **`ModuleNotFoundError: No module named 'lightgbm'`** — Install dependencies with `pip install -r server/requirements.txt` inside the **same** virtualenv you use to run `uvicorn`.
- **Wrong working directory** — If artifact paths fail, run from repo root or set `ARTIFACTS_DIR` / `MODEL_FILE` / `HEATMAP_FILE` explicitly.

## Client

Start the React app from [`../client/README.md`](../client/README.md) (default **http://localhost:5173**).
