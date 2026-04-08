from __future__ import annotations

import joblib
import numpy as np
import pandas as pd

from app.config import MODEL_FILE


class ModelService:
    def __init__(self) -> None:
        if not MODEL_FILE.exists():
            raise FileNotFoundError(f"Model file not found: {MODEL_FILE}")

        payload = joblib.load(MODEL_FILE)
        self.model = payload["model"]
        self.preprocessor = payload["preprocessor"]
        self.features = payload["features"]
        self.model_name = payload.get("best_model_name", "unknown")

    def predict_single(
        self,
        *,
        vehicle_type: str,
        month: int,
        day_of_week: int,
        hour: int,
        latitude: float,
        longitude: float,
        include_time_decay: bool = False,
    ) -> float:
        is_weekend = 1 if day_of_week in (5, 6) else 0
        is_rush_hour = 1 if hour in (7, 8, 9, 16, 17, 18) else 0
        is_peak_hour = 1 if hour in (6, 7, 8, 9, 15, 16, 17, 18, 19) else 0
        is_night = 1 if hour in (0, 1, 2, 3, 4, 5, 23) else 0

        row = {
            "Vehicle_Type": vehicle_type,
            "Month": month,
            "DayOfWeek": day_of_week,
            "Hour": hour,
            "IsWeekend": is_weekend,
            "IsRushHour": is_rush_hour,
            "IsPeakHour": is_peak_hour,
            "IsNight": is_night,
            "Latitude": latitude,
            "Longitude": longitude,
        }
        frame = pd.DataFrame([row], columns=self.features)
        transformed = self.preprocessor.transform(frame)
        X_out = self._to_feature_frame(transformed)
        prediction = float(self.model.predict(X_out)[0])

        if include_time_decay:
            # Small optional temporal damping to reduce aggressive peaks.
            prediction *= 0.95

        return max(0.0, float(np.round(prediction, 3)))

    def _to_feature_frame(self, transformed: np.ndarray) -> pd.DataFrame:
        names = self.preprocessor.get_feature_names_out()
        return pd.DataFrame(transformed, columns=names)

    def predict_batch(
        self,
        *,
        vehicle_type: str,
        month: int,
        day_of_week: int,
        hour: int,
        latitude_bins: np.ndarray,
        longitude_bins: np.ndarray,
        include_time_decay: bool = False,
    ) -> np.ndarray:
        """Vectorized inference for heatmap: one row per (lat, lon) bin."""
        n = len(latitude_bins)
        if n == 0:
            return np.array([], dtype=float)
        if len(longitude_bins) != n:
            raise ValueError("latitude_bins and longitude_bins must have the same length")

        is_weekend = 1 if day_of_week in (5, 6) else 0
        is_rush_hour = 1 if hour in (7, 8, 9, 16, 17, 18) else 0
        is_peak_hour = 1 if hour in (6, 7, 8, 9, 15, 16, 17, 18, 19) else 0
        is_night = 1 if hour in (0, 1, 2, 3, 4, 5, 23) else 0

        frame = pd.DataFrame(
            {
                "Vehicle_Type": [vehicle_type] * n,
                "Month": [month] * n,
                "DayOfWeek": [day_of_week] * n,
                "Hour": [hour] * n,
                "IsWeekend": [is_weekend] * n,
                "IsRushHour": [is_rush_hour] * n,
                "IsPeakHour": [is_peak_hour] * n,
                "IsNight": [is_night] * n,
                "Latitude": latitude_bins.astype(float),
                "Longitude": longitude_bins.astype(float),
            },
            columns=self.features,
        )
        transformed = self.preprocessor.transform(frame)
        X_out = self._to_feature_frame(transformed)
        preds = np.asarray(self.model.predict(X_out), dtype=float)
        preds = np.maximum(0.0, preds)
        if include_time_decay:
            preds = preds * 0.95
        return np.round(preds, 3)
