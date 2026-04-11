"""
Session bootstrap: real ``ModelService`` loads ``model.pkl`` at import time, so we build a
minimal sklearn bundle in a temp directory and set ``ARTIFACTS_DIR`` before any ``app`` import.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import joblib
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

# Same feature order as ``aiProject/ttc_pipeline/training_stages.py`` (CANDIDATE_FEATURES).
FEATURES = [
    "Vehicle_Type",
    "Month",
    "Hour",
    "DayOfWeek",
    "IsWeekend",
    "IsRushHour",
    "IsPeakHour",
    "IsNight",
    "Latitude",
    "Longitude",
]


def _write_minimal_artifacts(artifacts_dir: Path) -> None:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    X_fit = pd.DataFrame(
        {
            "Vehicle_Type": ["BUS", "STREETCAR", "SUBWAY"],
            "Month": [1, 6, 12],
            "Hour": [0, 12, 23],
            "DayOfWeek": [0, 3, 6],
            "IsWeekend": [0, 0, 1],
            "IsRushHour": [0, 1, 0],
            "IsPeakHour": [0, 1, 0],
            "IsNight": [1, 0, 1],
            "Latitude": [43.65, 43.70, 43.75],
            "Longitude": [-79.38, -79.40, -79.42],
        }
    )
    y_fit = pd.Series([2.5, 5.0, 1.0])
    categorical = ["Vehicle_Type"]
    numeric = [c for c in FEATURES if c not in categorical]
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "encoder",
                            OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
                        ),
                    ]
                ),
                categorical,
            ),
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), numeric),
        ],
        remainder="drop",
    )
    Xt = preprocessor.fit_transform(X_fit)
    model = LinearRegression()
    model.fit(Xt, y_fit)
    bundle = {
        "model": model,
        "preprocessor": preprocessor,
        "features": FEATURES,
        "best_model_name": "pytest-linear-dummy",
    }
    joblib.dump(bundle, artifacts_dir / "model.pkl")

    cfg = {
        "metadata": {
            "vehicle_types": ["BUS", "STREETCAR", "SUBWAY"],
            "months": list(range(1, 13)),
            "days_of_week": list(range(7)),
            "hours": list(range(24)),
        },
        "bins": [
            {"latitude_bin": 43.65, "longitude_bin": -79.38},
            {"latitude_bin": 43.66, "longitude_bin": -79.39},
        ],
    }
    (artifacts_dir / "heatmap_inference_config.json").write_text(
        json.dumps(cfg), encoding="utf-8"
    )


def pytest_configure(config: pytest.Config) -> None:
    if os.environ.get("ARTIFACTS_DIR"):
        return
    tmp = Path(tempfile.mkdtemp(prefix="ttc_pytest_artifacts_"))
    _write_minimal_artifacts(tmp)
    os.environ["ARTIFACTS_DIR"] = str(tmp)
