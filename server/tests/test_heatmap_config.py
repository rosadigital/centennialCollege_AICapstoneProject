"""Inference config loading (no FastAPI app import)."""

import json
from pathlib import Path

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
        "context_bin_indices": {"BUS|1|0|0": [0]},
    }
    cfg_path.write_text(json.dumps(payload), encoding="utf-8")
    meta, bins, context_bin_indices = load_inference_config(cfg_path)
    assert meta["vehicle_types"] == ["BUS"]
    assert bins == [{"latitude_bin": 1.0, "longitude_bin": 2.0}]
    assert context_bin_indices["BUS|1|0|0"] == [0]


def test_load_inference_config_missing_json_raises(tmp_path: Path) -> None:
    missing_json = tmp_path / "nope.json"
    with pytest.raises(FileNotFoundError):
        load_inference_config(missing_json)


def test_load_inference_config_missing_index_maps_raises(tmp_path: Path) -> None:
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
    with pytest.raises(ValueError, match="outdated"):
        load_inference_config(cfg_path)
