from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import HEATMAP_FILE, HEATMAP_INFERENCE_CONFIG
from app.services.model_service import ModelService


def _legacy_csv_bins_and_metadata() -> tuple[dict, list[dict[str, float]]]:
    """Derive bin grid + filter domains from legacy aggregate CSV (coordinates/metadata only)."""
    if not HEATMAP_FILE.exists():
        raise FileNotFoundError(f"Heatmap file not found: {HEATMAP_FILE}")
    df = pd.read_csv(HEATMAP_FILE)
    required = {"Vehicle_Type", "Month", "DayOfWeek", "Hour", "Latitude_Bin", "Longitude_Bin"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Legacy heatmap file missing columns: {sorted(missing)}")
    metadata = {
        "vehicle_types": sorted(df["Vehicle_Type"].dropna().unique().tolist()),
        "months": sorted(df["Month"].dropna().astype(int).unique().tolist()),
        "days_of_week": sorted(df["DayOfWeek"].dropna().astype(int).unique().tolist()),
        "hours": sorted(df["Hour"].dropna().astype(int).unique().tolist()),
    }
    bins_df = df[["Latitude_Bin", "Longitude_Bin"]].drop_duplicates()
    bins = [
        {"latitude_bin": float(r["Latitude_Bin"]), "longitude_bin": float(r["Longitude_Bin"])}
        for _, r in bins_df.iterrows()
    ]
    return metadata, bins


def load_inference_config(path: Path) -> tuple[dict, list[dict[str, float]]]:
    """Load bin grid and filter domains; prefer JSON from training, else legacy CSV."""
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        meta = raw["metadata"]
        bins = raw["bins"]
        return meta, bins
    return _legacy_csv_bins_and_metadata()


class HeatmapService:
    """
    Heatmap points are computed at request time via ``model.pkl`` (batch inference over a fixed bin grid).

    Bin coordinates and filter domains come from ``heatmap_inference_config.json`` (training export),
    or from the legacy aggregate CSV (same columns, values no longer used for delay — only grid/metadata).
    """

    def __init__(self, model_service: ModelService) -> None:
        self._model = model_service
        self._metadata, self._bins = load_inference_config(HEATMAP_INFERENCE_CONFIG)

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
        if not self._bins:
            return {"points": [], "kpis": {"point_count": 0, "avg_delay": 0.0, "p90": 0.0}}

        lats = np.array([b["latitude_bin"] for b in self._bins], dtype=float)
        lons = np.array([b["longitude_bin"] for b in self._bins], dtype=float)
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
