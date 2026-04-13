from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from app.config import HEATMAP_INFERENCE_CONFIG
from app.services.model_service import ModelService


def _ctx_key(vehicle_type: str, month: int, day_of_week: int, hour: int) -> str:
    return f"{vehicle_type}|{month}|{day_of_week}|{hour}"


def load_inference_config(path: Path) -> tuple[dict, list[dict[str, float]], dict[str, list[int]]]:
    """Load inference metadata + bin index maps from training JSON export only."""
    if not path.exists():
        raise FileNotFoundError(f"Heatmap inference config not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    required = {"metadata", "bins", "context_bin_indices"}
    missing = required - set(raw.keys())
    if missing:
        raise ValueError(
            "heatmap_inference_config.json is outdated; missing keys: "
            f"{sorted(missing)}. Re-run training export to regenerate artifacts."
        )
    meta = raw["metadata"]
    bins = raw["bins"]
    context_bin_indices = raw["context_bin_indices"]
    return meta, bins, context_bin_indices


class HeatmapService:
    """
    Heatmap points are computed at request time via ``model.pkl``.
    Bins and domains come from ``heatmap_inference_config.json`` exported at training.
    """

    def __init__(self, model_service: ModelService) -> None:
        self._model = model_service
        (
            self._metadata,
            self._bins,
            self._context_bin_indices,
        ) = load_inference_config(HEATMAP_INFERENCE_CONFIG)

    def metadata(self) -> dict:
        return {
            "vehicle_types": self._metadata["vehicle_types"],
            "months": self._metadata["months"],
            "days_of_week": self._metadata["days_of_week"],
            "hours": self._metadata["hours"],
        }

    def query(
        self,
        *,
        vehicle_type: str,
        month: int,
        day_of_week: int,
        hour: int,
        include_time_decay: bool = False,
    ) -> dict:
        if vehicle_type not in set(self._metadata["vehicle_types"]):
            raise ValueError(f"Unknown vehicle_type: {vehicle_type}")

        if not self._bins:
            return {"points": [], "kpis": {"point_count": 0, "avg_delay": 0.0, "p90": 0.0}}

        selected_idx = self._context_bin_indices.get(_ctx_key(vehicle_type, month, day_of_week, hour), [])
        if not selected_idx:
            return {"points": [], "kpis": {"point_count": 0, "avg_delay": 0.0, "p90": 0.0}}

        selected_bins = [self._bins[i] for i in selected_idx]
        lats = np.array([b["latitude_bin"] for b in selected_bins], dtype=float)
        lons = np.array([b["longitude_bin"] for b in selected_bins], dtype=float)
        preds = self._model.predict_batch(
            vehicle_type=vehicle_type,
            month=month,
            day_of_week=day_of_week,
            hour=hour,
            latitude_bins=lats,
            longitude_bins=lons,
            include_time_decay=include_time_decay,
        )

        max_delay = float(np.max(preds)) if len(preds) else 1.0
        if max_delay <= 0:
            max_delay = 1.0
        weights = np.clip(preds / max_delay, 0.0, 1.0)

        points = [
            {
                "latitude_bin": float(lats[i]),
                "longitude_bin": float(lons[i]),
                "pred_delay_mean": float(preds[i]),
                # Single prediction per bin: align with prior schema (p90 ~= mean at point level).
                "pred_delay_p90": float(preds[i]),
                "n_events": 1,
                "weight": float(weights[i]),
            }
            for i in range(len(preds))
        ]

        kpis = {
            "point_count": int(len(preds)),
            "avg_delay": float(np.mean(preds)) if len(preds) else 0.0,
            "p90": float(np.percentile(preds, 90)) if len(preds) else 0.0,
        }
        return {"points": points, "kpis": kpis}
