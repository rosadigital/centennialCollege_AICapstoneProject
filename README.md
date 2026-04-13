# AI Capstone Project - TTC Delay Prediction SaaS

**Course:** AI Capstone Project - COMP385402.12558.2026W  
**Professor:** Hakim Klif  
**Institution:** Centennial College

## Overview

This repository contains a complete TTC delay prediction workflow:

- **Data & ML:** exploratory analysis and model training in [`aiProject/`](aiProject/)
- **API:** FastAPI backend in [`server/`](server/)
- **UI:** React + Tailwind + MapLibre heatmap client in [`client/`](client/)

Users select **vehicle type**, **month**, **day of week**, and **hour**; the app shows predicted delay intensity on a map and summary KPIs computed **on each request** by the backend model (`model.pkl`). The heatmap uses only bins listed for that exact context in `heatmap_inference_config.json` (training export: `context_bin_indices` keyed as `vehicle_type|month|day_of_week|hour`, built from **train+validation+test** rows so coverage matches historical data, not the test split alone). Point-level scoring remains available via `POST /predict`.

## Architecture

Logical view of the stack: the SPA calls **REST** endpoints (`fetch` in `client/src/lib/api.ts`). The labels below mirror **MCP-style tools** for documentation only; the wire protocol is plain HTTP JSON.

```mermaid
flowchart TB
    subgraph Browser
        U[User]
    end

    subgraph Client["Client — Vite + React + MapLibre"]
        CP[ControlPanel — filters]
        HM[HeatmapMap — basemap + heat layer]
        APIc["fetch — api.ts"]
        CP --> APIc
        HM --> APIc
    end

    subgraph Server["Server — FastAPI"]
        R1["GET /metadata"]
        R2["GET /heatmap"]
        R3["POST /predict"]
        HS[HeatmapService — bin grid + orchestration]
        MS[ModelService — batch inference from model.pkl]
        R1 --> HS
        R2 --> HS
        HS --> MS
        R3 --> MS
    end

    subgraph Artifacts["Artifacts (see server/model_artifacts or aiProject/outputs/model_artifacts)"]
        CFG["heatmap_inference_config.json — bins + domains + context_bin_indices"]
        PKL["model.pkl — preprocessor + regressor bundle"]
    end

    U --> CP
    U --> HM
    APIc -->|"GET /metadata"| R1
    R1 -->|"JSON domains"| APIc
    APIc -->|"GET /heatmap?…"| R2
    R2 -->|"JSON {points[], kpis}"| APIc
    HS -.->|"startup: load grid + domains"| CFG
    MS -->|"load once + infer"| PKL
```

**Dev runtime (ports and CORS):** Vite may serve on **5173** or **5174**; opening the app as `http://localhost:…` vs `http://127.0.0.1:…` is a **different browser origin** and must be listed in `CORS_ORIGINS`. If another app already uses **8000**, run Uvicorn on **8001** and set `VITE_API_URL` or rely on the client’s built-in fallback (see [`client/README.md`](client/README.md)).

```mermaid
flowchart LR
    subgraph Origins["Vite dev origins (examples)"]
        O1["http://localhost:5173"]
        O2["http://localhost:5174"]
        O3["http://127.0.0.1:5173"]
        O4["http://127.0.0.1:5174"]
    end
    subgraph API["FastAPI"]
        EP["/metadata · /heatmap · /predict · /health"]
    end
    Origins -->|"fetch + CORS allowlist"| API
```

### Architecture steps

1. **`GET /metadata`** — Returns valid domains for vehicle, month, weekday, and hour (loaded at startup from `heatmap_inference_config.json`).
2. **`GET /heatmap`** — With query parameters for filters, the server runs **batch inference** only on bins indexed for that exact filter tuple (`context_bin_indices`) and returns map points plus KPI aggregates (`avg_delay`, `p90`, `point_count`).
3. **Bin index** — `HeatmapService` loads the full coordinate list from `heatmap_inference_config.json`, but each request selects the subset for `vehicle_type|month|day_of_week|hour`. **No CSV legado** is used for heatmap selection or inference.
4. **Model artifact** — `ModelService` loads `model.pkl` (preprocessor + regressor) once at startup and reuses it for every heatmap and `POST /predict` call.

## Sequence diagram (typical UI session)

How the SPA loads options and refreshes the map when filters change, with explicit tool invocations/results and resource interactions (`include_time_decay` is supported by the API; the current UI sends `false`).

```mermaid
sequenceDiagram
    actor User
    participant App as React App
    participant API as FastAPI
    participant CFG as heatmap_inference_config.json
    participant MFile as model.pkl
    participant HSvc as HeatmapService
    participant MSvc as ModelService

    User->>App: Open app
    App->>API: GET /metadata
    API->>HSvc: metadata()
    Note over HSvc: Domains + bins + context index loaded at startup from CFG
    HSvc-->>API: metadata domains
    API-->>App: 200 JSON {vehicle_types, months, days_of_week, hours}
    App->>App: Initialize filter defaults

    User->>App: Adjust vehicle / month / day / hour
    App->>API: GET /heatmap?vehicle_type&month&day_of_week&hour&include_time_decay
    API->>HSvc: query(filters)
    HSvc->>MSvc: predict_batch(context bins × filters)
    MSvc->>MFile: in-memory model + preprocessor
    MFile-->>MSvc: vector predictions
    MSvc-->>HSvc: delay per bin
    HSvc-->>API: points + KPI aggregates
    API-->>App: 200 JSON {points[], kpis}
    App->>User: Update MapLibre heatmap + KPI cards

    opt Point-level prediction
        App->>API: POST /predict {lat, lon, vehicle_type, ...}
        API->>MSvc: predict_single(...)
        MSvc->>MFile: same loaded bundle
        MSvc-->>API: predicted_delay_minutes
        API-->>App: 200 JSON {predicted_delay_minutes, model_name}
    end
```

### Sequence steps

1. **Metadata** — `GET /metadata` bootstraps filter options from `heatmap_inference_config.json`.
2. **Heatmap** — `GET /heatmap` runs whenever filters change. `HeatmapService` resolves the bin subset for the exact tuple and invokes **batch prediction** via `ModelService`.
3. **Model-backed map** — Predictions come from `model.pkl` for each selected bin; weights and KPIs are derived from those scores.
4. **Optional point prediction** — `POST /predict` scores a single coordinate and time context using the same loaded model bundle.

### Heatmap request latency (reference)

Measured locally with the project `.venv` and a full-grid export: one heatmap query was on the order of **tens of ms** after model load; first-time `model.pkl` load was **~1–2 s** (I/O + unpickle). With `context_bin_indices`, **fewer bins per request** usually means lower latency. Your numbers will vary with CPU, disk, and subset size.

## Quick start (run the full stack)

1. **Generate model artifacts** (if not already present): run [`aiProject/01_EDA_TTC_Delay_Prediction.ipynb`](aiProject/01_EDA_TTC_Delay_Prediction.ipynb) **or** the OOP pipeline (see [OOP Python pipeline](#oop-python-pipeline-uml)) so the following exist under `server/model_artifacts/` (or set `ARTIFACTS_DIR`):
   - `model.pkl`
   - `heatmap_inference_config.json` — **required** for the API: includes `metadata`, `bins`, and `context_bin_indices` (keys `vehicle_type|month|day_of_week|hour`). Regenerate with `python -m aiProject.ttc_pipeline training` if the server reports a missing or outdated config.
   - Optional: `heatmap_predictions_test_agg.csv` — offline aggregate from training; **not** used by the heatmap API for bin selection or inference.

2. **Start the API** (terminal 1) — see [`server/README.md`](server/README.md) for details.

3. **Start the web client** (terminal 2) — see [`client/README.md`](client/README.md) for details.

Default URLs (typical):

- API: `http://localhost:8000` (if that port is already used by another app, use **8001** and point the client — see [`server/README.md`](server/README.md) / [`client/README.md`](client/README.md))
- Client: `http://localhost:5173` — Vite may pick **5174** if 5173 is busy; use **`localhost` vs `127.0.0.1` consistently** with your API URL so CORS matches (`server/app/config.py` defaults include both hostnames for 5173/5174)

## Notebook pipeline (import → `model.pkl`)

Steps follow [`aiProject/01_EDA_TTC_Delay_Prediction.ipynb`](aiProject/01_EDA_TTC_Delay_Prediction.ipynb), one line each from loading data through saving the production bundle.

### EDA and processed dataset

1. **Setup** — Import pandas, NumPy, visualization libraries, define paths to `dataset/` and `outputs/`, and set a random seed for reproducibility.
2. **Unified import** — Load `dataset/ttc_delays_2017_2025_unified_with_coords_corrected.csv` with `read_csv`.
3. **Schema & validation** — Check dtypes, parse `Date`/`Time` into datetimes, and confirm 2017–2025 coverage and column consistency.
4. **Baseline exploration** — Plot quick counts and relationships on the raw unified table before heavy cleaning.
5. **Missing values** — Impute categoricals (e.g., `Unknown`), fill numerics with sensible defaults or medians by vehicle type, and drop rows missing essential timestamps.
6. **Feature engineering** — Derive hour, month, day-of-week, cyclical encodings, seasonality, and set **Min Delay** as the regression target.
7. **Normalization / transformation** — Apply log or scaling to skewed columns where the EDA recommends it.
8. **Imbalance** — Analyze record counts by year and vehicle type to understand sampling bias.
9. **Processed summary** — Review the cleaned frame before persisting.
10. **Save treated dataset** — Write the engineered table (e.g., `aiProject/outputs/ttc_delays_2017_2025_unified_with_coords_corrected_treated.csv`) for the modeling section.

### Modeling section (training pipeline → artifacts)

11. **Modeling dataframe** — Reload the treated CSV and build the tabular base used for train/validation/test.
12. **Target & time features** — Clean **Min Delay**, drop invalid targets, and align calendar features used at inference.
13. **Temporal split & outliers** — Split by time (train / validation / test) and cap extreme delays using statistics computed **only on training** to limit leakage.
14. **Inference-only features** — Build a sklearn `Pipeline` with columns available in production (e.g., vehicle, month, weekday, hour, latitude, longitude), **excluding** leakage-prone fields such as `Delay_Ratio`, `Min Gap`, raw vehicle id, delay codes, and station text.
15. **Train LightGBM** — Fit the gradient-boosting regressor inside the preprocessing pipeline.
16. **Train XGBoost** — Fit an alternative booster for comparison on the same feature matrix.
17. **Model selection** — Compare LightGBM vs. XGBoost on validation and test metrics and record the winner.
18. **Production bundle & heatmap export** — Retrain the best model on train+validation, serialize the **preprocessor + regressor** bundle with `joblib.dump` to **`server/model_artifacts/model.pkl`**, write **`heatmap_inference_config.json`** (bins, domains, and `context_bin_indices` per filter tuple), and optionally keep **`heatmap_predictions_test_agg.csv`** as an offline aggregate only.

## OOP Python pipeline (UML)

The notebook is also available as an **object-oriented** package under [`aiProject/ttc_pipeline/`](aiProject/ttc_pipeline/): stage classes in [`eda_stages.py`](aiProject/ttc_pipeline/eda_stages.py), training in [`training_stages.py`](aiProject/ttc_pipeline/training_stages.py), and a façade [`TTCDelayPipeline`](aiProject/ttc_pipeline/orchestrator.py) in [`orchestrator.py`](aiProject/ttc_pipeline/orchestrator.py). Training dependencies match [`server/requirements.txt`](server/requirements.txt) / [`aiProject/requirements.txt`](aiProject/requirements.txt) (`lightgbm`, `xgboost`, etc.).

**Run from the repository root** (install `aiProject` requirements first; use `--no-plots` in headless environments):

```bash
python -m aiProject.ttc_pipeline           # EDA + training (same end state as full notebook)
python -m aiProject.ttc_pipeline eda       # only treated CSV
python -m aiProject.ttc_pipeline training  # only models (expects treated CSV on disk)
python -m aiProject.ttc_pipeline all --no-plots
```

### UML (classes and relationships)

`TTCDelayPipeline` owns a `PipelineConfig` and delegates each notebook block to a small class; `ModelTrainingPipeline` is created only for the training phase so importing the package does not require `lightgbm` until you train.

```mermaid
classDiagram
    direction TB
    class PipelineConfig {
        +Path repo_root
        +Path unified_file
        +Path processed_file
        +Path artifacts_dir
        +bool show_plots
    }
    class TTCDelayPipeline {
        +run_eda_phase() DataFrame
        +run_training_phase(df?)
        +run_all()
        +dataframe DataFrame?
    }
    class UnifiedDataLoader {
        +load() DataFrame
    }
    class DatasetValidator {
        +validate_columns(df)
        +parse_and_filter_years(df) DataFrame
    }
    class BaselineExplorer {
        +explore(df)
    }
    class MissingDelayRecoverabilityAudit {
        +audit(df)
    }
    class MissingValueAnalyzer {
        +report(df)
    }
    class MissingValueHandler {
        +transform(df) DataFrame
    }
    class GeoMissingSummary {
        +summarize(df) DataFrame
    }
    class FeatureEngineer {
        +transform(df) DataFrame
    }
    class TargetVariableBuilder {
        +add_categories(df) DataFrame
        +plot_distributions(df)
    }
    class NormalizationTransformer {
        +assess(df) DataFrame
        +transform(df) DataFrame
    }
    class ImbalanceAnalyzer {
        +print_tables(df)
        +plot_imbalance(df)
        +plot_imbalance_secondary(df)
    }
    class ProcessedSummaryReporter {
        +summarize(df)
    }
    class ProcessedDatasetWriter {
        +save(df) Path
    }
    class ProcessedEDAExplorer {
        +correlation_processed(df)
        +temporal_patterns(df)
        +appendix_correlation_raw_numerics(df)
    }
    class ModelTrainingPipeline {
        +run_full_training(df?)
        +load_modeling_dataframe(df?)
        +clean_target_and_time() DataFrame
        +temporal_split_and_cap()
        +build_preprocessor() ColumnTransformer
        +train_lightgbm()
        +train_xgboost()
        +compare_and_select_best() str
        +export_production_bundle()
    }

    TTCDelayPipeline *-- PipelineConfig
    ModelTrainingPipeline *-- PipelineConfig
    TTCDelayPipeline ..> UnifiedDataLoader : uses
    TTCDelayPipeline ..> DatasetValidator : uses
    TTCDelayPipeline ..> BaselineExplorer : uses
    TTCDelayPipeline ..> MissingDelayRecoverabilityAudit : uses
    TTCDelayPipeline ..> MissingValueAnalyzer : uses
    TTCDelayPipeline ..> MissingValueHandler : uses
    TTCDelayPipeline ..> GeoMissingSummary : uses
    TTCDelayPipeline ..> FeatureEngineer : uses
    TTCDelayPipeline ..> TargetVariableBuilder : uses
    TTCDelayPipeline ..> NormalizationTransformer : uses
    TTCDelayPipeline ..> ImbalanceAnalyzer : uses
    TTCDelayPipeline ..> ProcessedSummaryReporter : uses
    TTCDelayPipeline ..> ProcessedDatasetWriter : uses
    TTCDelayPipeline ..> ProcessedEDAExplorer : uses
    TTCDelayPipeline ..> ModelTrainingPipeline : creates when training
```

### UML steps

1. **Pipeline configuration** — `PipelineConfig` centralizes paths (`dataset`, treated CSV, `server/model_artifacts`) and runtime flags. Every stage receives consistent location and behavior settings.
2. **EDA orchestration** — `TTCDelayPipeline` delegates each notebook phase to focused classes (`Loader`, `Validator`, `FeatureEngineer`, etc.). The output is a treated dataset that matches the training contract.
3. **Training orchestration** — `TTCDelayPipeline` creates `ModelTrainingPipeline` only when training is requested. This keeps EDA-only runs decoupled from heavy model dependencies.
4. **Artifact production** — `ModelTrainingPipeline` trains/compares models and exports `model.pkl` and heatmap aggregates to `server/model_artifacts`. The server can immediately consume those files without extra path remapping.

## Project structure

```text
centennialCollege_AICapstoneProject/
├── aiProject/
│   ├── 01_EDA_TTC_Delay_Prediction.ipynb
│   ├── ttc_pipeline/       # OOP port of the notebook (see README UML)
│   │   ├── config.py
│   │   ├── eda_stages.py
│   │   ├── training_stages.py
│   │   ├── orchestrator.py
│   │   └── __main__.py
│   └── requirements.txt
├── server/                 # FastAPI — see server/README.md
│   ├── model_artifacts/
│   │   ├── model.pkl
│   │   ├── heatmap_inference_config.json
│   │   └── heatmap_predictions_test_agg.csv
│   └── app/
├── client/                 # React + Vite — see client/README.md
├── dataset/
└── README.md               # this file
```

## Dataset

TTC historical delay data (2017–2025) for bus, streetcar, and subway.

**Source:** [Toronto Open Data Portal](https://open.toronto.ca/)

## Documentation

| Topic | File |
|--------|------|
| Run the API | [`server/README.md`](server/README.md) |
| Run the web app | [`client/README.md`](client/README.md) |
| OOP ML pipeline | [`aiProject/ttc_pipeline/`](aiProject/ttc_pipeline/) |

## Team

1. Absar Siddiqui-Atta  
2. Bruna De Fatima Miranda Figueiredo Cruz  
3. Felipe Rosa  
4. Krishan Singh  
5. Marco Favaretto  
