# Automated tests (pytest) — guide for review

This folder contains **automated tests** for the TTC Delay Prediction **FastAPI** backend. They run with **[pytest](https://docs.pytest.org/)**, a standard Python test framework. The same scenarios are also described in the capstone **test case spreadsheet** (manual traceability).

---

## Why we test

- **Regression:** Changes to the API or model loading are less likely to break existing behaviour if tests fail immediately.
- **Documentation:** Each test states an expected outcome (status code, JSON shape, validation rules).
- **Course deliverable:** Automated checks complement the professor’s **test case template** (Excel).

---

## How pytest uses `conftest.py`

**`conftest.py` is not imported by our test files.** Pytest discovers it automatically and runs special functions (called **hooks**) inside it.

Our backend loads **`model.pkl`** when `app.main` is imported (`ModelService`). That file is often **not** in the repository. To avoid test failures:

1. **`pytest_configure`** runs at the very start of a test session.
2. If the environment variable **`ARTIFACTS_DIR`** is **not** set, it creates a **temporary folder**, writes a **small dummy** `model.pkl` (sklearn linear model + preprocessor) and a minimal **`heatmap_inference_config.json`**, then sets `ARTIFACTS_DIR` to that folder.
3. If **`ARTIFACTS_DIR` is already set**, nothing is changed — tests use **your real** model artifacts (e.g. after training).

So: **`conftest.py` = shared setup** so the API tests can import the app without committing a large model file.

---

## File overview

| File | Role |
|------|------|
| **`conftest.py`** | Session setup: optional temp ML artifacts + `ARTIFACTS_DIR`. |
| **`test_api.py`** | End-to-end HTTP tests via FastAPI **`TestClient`** (no live server required). |
| **`test_schemas.py`** | Unit tests for **Pydantic** request validation (`PredictRequest`). |
| **`test_heatmap_config.py`** | Unit tests for **heatmap config loading** (JSON vs legacy CSV). |

---

## What each test does

### `test_api.py` — REST API

| Test | What it checks |
|------|----------------|
| **`test_health_ok`** | `GET /health` returns **200**, JSON has `status == "ok"` and reports artifact paths. |
| **`test_metadata_shape`** | `GET /metadata` returns **200** and non-empty lists for `vehicle_types`, `months`, `days_of_week`, `hours`. |
| **`test_heatmap_success`** | `GET /heatmap` with valid query params returns **200**, response has **`points`** and **`kpis`**, and `point_count` matches the number of points. |
| **`test_heatmap_validation_error_month`** | `GET /heatmap` with **invalid** `month=13` returns **422** (FastAPI/Pydantic validation). |
| **`test_predict_success`** | `POST /predict` with a **valid** JSON body returns **200**, includes `predicted_delay_minutes` ≥ 0. |
| **`test_predict_validation_invalid_vehicle`** | `POST /predict` with invalid `vehicle_type` (**FERRY**) returns **422**. |

### `test_schemas.py` — input validation (no HTTP)

| Test | What it checks |
|------|----------------|
| **`test_predict_request_accepts_valid_payload`** | A valid **`PredictRequest`** builds successfully; default `include_time_decay` is **False**. |
| **`test_predict_request_rejects_invalid_vehicle`** | Invalid vehicle type raises **`ValidationError`**. |
| **`test_predict_request_range_constraints`** (4 cases) | Out-of-range **`month`**, **`day_of_week`**, or **`hour`** each raise **`ValidationError`** (parametrized test). |

### `test_heatmap_config.py` — configuration loading

| Test | What it checks |
|------|----------------|
| **`test_load_inference_config_from_json`** | When a **`heatmap_inference_config.json`** exists, **`load_inference_config`** returns metadata and bins matching the file (uses pytest **`tmp_path`**). |
| **`test_load_inference_config_legacy_csv`** | When the JSON path does **not** exist, the code falls back to the **legacy CSV**; **`HEATMAP_FILE`** is **monkeypatched** to a small temp CSV so the test does not depend on the real artifact directory. |

**Total:** 6 + 6 + 2 = **14** automated test cases (6 API + 6 schema + 2 config).

---

## How to run the tests

From the **`server`** directory, using the project virtual environment (Python 3.10+ recommended; **3.12** is used in development):

```powershell
cd D:\Centennial\6_Semester\COMP_385-402\Group3_Project\centennialCollege_AICapstoneProject\server
..\.venv\Scripts\python.exe -m pytest tests -v
```

Run a single file:

```powershell
..\.venv\Scripts\python.exe -m pytest tests\test_api.py -v
```

**Dependencies:** `pytest` and `httpx` are listed in `server/requirements.txt` (TestClient uses them under the hood).

---

## Relation to the Excel test case template

The spreadsheet lists **test case IDs**, **steps**, **inputs**, **expected results**, and maps them to these pytest tests. The filled workbook is saved next to the college template (filename includes **Group3 Filled**). The spreadsheet is for **human review**; this folder is for **repeatable automated** checks.

---

## Summary for a short oral explanation

“We use **pytest** to test the **FastAPI** service: **health**, **metadata**, **heatmap**, and **predict** endpoints, plus **Pydantic** validation and **heatmap config** loading. **`conftest.py`** prepares a **dummy model** in a temp folder when the real **`model.pkl`** is not configured, so **CI and classmates** can run tests without copying artifacts. **TestClient** sends fake HTTP requests **in-process**, so we do not need Uvicorn running during the test run.”
