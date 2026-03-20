from __future__ import annotations

from functools import lru_cache
import pandas as pd

from app.config import HEATMAP_FILE


@lru_cache(maxsize=1)
def _load_heatmap_df() -> pd.DataFrame:
    if not HEATMAP_FILE.exists():
        raise FileNotFoundError(f"Heatmap file not found: {HEATMAP_FILE}")
    df = pd.read_csv(HEATMAP_FILE)
    required = {
        "Vehicle_Type",
        "Month",
        "DayOfWeek",
        "Hour",
        "Latitude_Bin",
        "Longitude_Bin",
        "pred_delay_mean",
        "pred_delay_p90",
        "n_events",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Heatmap file missing columns: {sorted(missing)}")
    return df


class HeatmapService:
    def __init__(self) -> None:
        self.df = _load_heatmap_df()

    def metadata(self) -> dict:
        return {
            "vehicle_types": sorted(self.df["Vehicle_Type"].dropna().unique().tolist()),
            "months": sorted(self.df["Month"].dropna().astype(int).unique().tolist()),
            "days_of_week": sorted(
                self.df["DayOfWeek"].dropna().astype(int).unique().tolist()
            ),
            "hours": sorted(self.df["Hour"].dropna().astype(int).unique().tolist()),
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
        filtered = self.df[
            (self.df["Vehicle_Type"] == vehicle_type)
            & (self.df["Month"] == month)
            & (self.df["DayOfWeek"] == day_of_week)
            & (self.df["Hour"] == hour)
        ].copy()

        if filtered.empty:
            return {"points": [], "kpis": {"point_count": 0, "avg_delay": 0.0, "p90": 0.0}}

        if include_time_decay:
            filtered["pred_delay_mean"] = filtered["pred_delay_mean"] * 0.95
            filtered["pred_delay_p90"] = filtered["pred_delay_p90"] * 0.95

        max_delay = float(filtered["pred_delay_mean"].max()) or 1.0
        filtered["weight"] = (filtered["pred_delay_mean"] / max_delay).clip(0, 1)

        points = [
            {
                "latitude_bin": float(row["Latitude_Bin"]),
                "longitude_bin": float(row["Longitude_Bin"]),
                "pred_delay_mean": float(row["pred_delay_mean"]),
                "pred_delay_p90": float(row["pred_delay_p90"]),
                "n_events": int(row["n_events"]),
                "weight": float(row["weight"]),
            }
            for _, row in filtered.iterrows()
        ]

        kpis = {
            "point_count": int(len(filtered)),
            "avg_delay": float(filtered["pred_delay_mean"].mean()),
            "p90": float(filtered["pred_delay_p90"].quantile(0.9)),
        }
        return {"points": points, "kpis": kpis}
