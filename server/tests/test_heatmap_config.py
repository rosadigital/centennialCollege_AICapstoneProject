"""Inference config loading (no FastAPI app import)."""

import json
from pathlib import Path

import pandas as pd
import pytest

from app.services.heatmap_service import load_inference_config


def test_load_inference_config_from_json(tmp_path: Path) -> None:
    cfg_path = tmp_path / "heatmap_inference_config.json"
    payload = {
        "metadata": {
            "vehicle_types": ["BUS"],
            "months": [1],
            "days_of_week": [0],
            "hours": [0],
        },
        "bins": [{"latitude_bin": 1.0, "longitude_bin": 2.0}],
    }
    cfg_path.write_text(json.dumps(payload), encoding="utf-8")
    meta, bins = load_inference_config(cfg_path)
    assert meta["vehicle_types"] == ["BUS"]
    assert bins == [{"latitude_bin": 1.0, "longitude_bin": 2.0}]


def test_load_inference_config_legacy_csv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.heatmap_service as heatmap_service

    missing_json = tmp_path / "nope.json"
    csv_path = tmp_path / "heatmap_predictions_test_agg.csv"
    df = pd.DataFrame(
        {
            "Vehicle_Type": ["BUS"],
            "Month": [1],
            "DayOfWeek": [0],
            "Hour": [8],
            "Latitude_Bin": [43.0],
            "Longitude_Bin": [-79.0],
        }
    )
    df.to_csv(csv_path, index=False)
    monkeypatch.setattr(heatmap_service, "HEATMAP_FILE", csv_path)
    meta, bins = load_inference_config(missing_json)
    assert "BUS" in meta["vehicle_types"]
    assert len(bins) == 1
    assert bins[0]["latitude_bin"] == 43.0
