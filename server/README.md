# TTC Delay Prediction — API server

FastAPI service: model inference, heatmap data, and metadata for the web client.

## Prerequisites

- **Python** 3.10+ recommended  
- **Model artifacts** (from the EDA notebook / OOP pipeline) under `server/model_artifacts/`:
  - `model.pkl`
  - `heatmap_inference_config.json` (bin grid + filter domains for the heatmap API)
  - Optional: `heatmap_predictions_test_agg.csv` — used only if the JSON is missing, to **migrate** bin coordinates/metadata; heatmap **values** are always computed from `model.pkl` at request time.

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

The Python package is **`app`** inside the **`server/`** folder. You must put **`server` on `PYTHONPATH`** (or run from inside `server/` with `PYTHONPATH=.`).  
**Do not** use `PYTHONPATH=.` from the **repository root** — that breaks imports (`No module named 'app'`).

**Recommended — from the repository root:**

```bash
cd /path/to/centennialCollege_AICapstoneProject
source .venv/bin/activate
PYTHONPATH=server uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Artifacts only under `aiProject/outputs/model_artifacts/` (not copied into `server/model_artifacts/`):**

```bash
export ARTIFACTS_DIR="$(pwd)/aiProject/outputs/model_artifacts"
PYTHONPATH=server uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

(On Windows PowerShell, set `ARTIFACTS_DIR` to an absolute path to that folder.)

**From the `server/` directory:**

```bash
cd server
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
| `HEATMAP_FILE` | Path to legacy `heatmap_predictions_test_agg.csv` (optional migration source) |
| `HEATMAP_INFERENCE_CONFIG` | Path to `heatmap_inference_config.json` (preferred) |
| `CORS_ORIGINS` | Comma-separated allowed browser origins (default includes `http://localhost:5173`) |

Example when running only from `server/` with relative paths:

```bash
export ARTIFACTS_DIR=./model_artifacts
export CORS_ORIGINS=http://localhost:5173
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

Or copy `server/.env.example` to `server/.env` and load it with your process manager / `python-dotenv` if you add that.

## Troubleshooting

- **`ModuleNotFoundError: No module named 'app'`** — You ran `uvicorn` with the wrong `PYTHONPATH`. From the **repo root**, use `PYTHONPATH=server` (not `PYTHONPATH=.`). Or `cd server` and use `PYTHONPATH=.`.
- **`FileNotFoundError: Model file not found: .../server/model_artifacts/model.pkl`** — Either copy your training outputs into `server/model_artifacts/`, or set **`ARTIFACTS_DIR`** before starting (see example above) so it points at the folder that contains `model.pkl` (and ideally `heatmap_inference_config.json`, or the legacy CSV for bin migration).
- **`ModuleNotFoundError: No module named 'lightgbm'`** — Install dependencies with `pip install -r server/requirements.txt` inside the **same** virtualenv you use to run `uvicorn`.
- **Wrong working directory** — If artifact paths fail, run from repo root or set `ARTIFACTS_DIR` / `MODEL_FILE` / `HEATMAP_FILE` / `HEATMAP_INFERENCE_CONFIG` explicitly.

## Client

Start the React app from [`../client/README.md`](../client/README.md) (default **http://localhost:5173**).
