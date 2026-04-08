"""LightGBM / XGBoost training and artifact export (notebook section 13)."""

from __future__ import annotations

import json
import warnings
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, median_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder
from xgboost import XGBRegressor

from .config import PipelineConfig

warnings.filterwarnings("ignore")


def regression_metrics(y_true: pd.Series | np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    medae = float(median_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))
    p90 = float(np.percentile(np.abs(np.asarray(y_true) - y_pred), 90))
    return {
        "rmse": rmse,
        "mae": mae,
        "medae": medae,
        "r2": r2,
        "abs_error_p90": p90,
    }


class ModelTrainingPipeline:
    """
    Stages 2–9 from the notebook: modeling frame → split → preprocess → train → export ``model.pkl``.
    """

    CANDIDATE_FEATURES = [
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

    def __init__(self, config: PipelineConfig) -> None:
        self._config = config
        self.model_df: Optional[pd.DataFrame] = None
        self.train_df: Optional[pd.DataFrame] = None
        self.val_df: Optional[pd.DataFrame] = None
        self.test_df: Optional[pd.DataFrame] = None
        self.features: list[str] = []
        self.categorical_features: list[str] = []
        self.numeric_features: list[str] = []
        self.preprocessor: Optional[ColumnTransformer] = None
        self.lgbm: Optional[LGBMRegressor] = None
        self.xgb: Optional[XGBRegressor] = None
        self.best_model_name: str = ""
        self.best_model: Any = None
        self.metrics: dict[str, Any] = {}
        self._X_train_t: Optional[np.ndarray] = None
        self._X_val_t: Optional[np.ndarray] = None
        self._X_test_t: Optional[np.ndarray] = None
        self._y_train: Optional[pd.Series] = None
        self._y_val: Optional[pd.Series] = None
        self._y_test: Optional[pd.Series] = None

    def load_modeling_dataframe(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        if df is not None:
            self.model_df = df.copy()
        else:
            path = self._config.processed_file
            if not path.exists():
                raise FileNotFoundError(
                    f"Processed dataset not found: {path}. Run the EDA phase first."
                )
            self.model_df = pd.read_csv(path)
        print(f"Model base shape: {self.model_df.shape}")
        print(self.model_df["Vehicle_Type"].value_counts(dropna=False))
        return self.model_df

    def clean_target_and_time(self) -> pd.DataFrame:
        assert self.model_df is not None
        mdf = self.model_df
        if "Date" not in mdf.columns or "Time" not in mdf.columns:
            raise ValueError("Expected columns `Date` and `Time`.")
        raw_target = pd.to_numeric(mdf["Min Delay"], errors="coerce")
        negative_target_rows = int((raw_target < 0).sum())
        mdf = mdf.copy()
        mdf["EventDateTime"] = pd.to_datetime(
            mdf["Date"].astype(str) + " " + mdf["Time"].astype(str),
            errors="coerce",
        )
        mdf["Min Delay"] = raw_target
        mdf = mdf.dropna(subset=["EventDateTime", "Min Delay"]).copy()
        mdf["Min Delay"] = mdf["Min Delay"].clip(lower=0)
        mdf["Year"] = mdf["EventDateTime"].dt.year
        mdf["Month"] = mdf["EventDateTime"].dt.month
        mdf["DayOfWeek"] = mdf["EventDateTime"].dt.dayofweek
        mdf["Hour"] = mdf["EventDateTime"].dt.hour
        if "Min Gap" in mdf.columns:
            min_gap_num = pd.to_numeric(mdf["Min Gap"], errors="coerce")
            mdf["Min Gap"] = min_gap_num
            mdf["Delay_Ratio"] = mdf["Min Delay"] / (min_gap_num.fillna(0) + 1)
        else:
            mdf["Min Gap"] = np.nan
            mdf["Delay_Ratio"] = np.nan
        print(f"Negative delay rows (clipped): {negative_target_rows:,}; shape after clean: {mdf.shape}")
        self.model_df = mdf
        return mdf

    def temporal_split_and_cap(self) -> None:
        assert self.model_df is not None
        mdf = self.model_df
        train_df = mdf[mdf["Year"] <= 2023].copy()
        val_df = mdf[mdf["Year"] == 2024].copy()
        test_df = mdf[mdf["Year"] == 2025].copy()
        if len(train_df) == 0 or len(val_df) == 0 or len(test_df) == 0:
            mdf = mdf.sort_values("EventDateTime").reset_index(drop=True)
            n = len(mdf)
            train_end = int(n * 0.70)
            val_end = int(n * 0.85)
            train_df = mdf.iloc[:train_end].copy()
            val_df = mdf.iloc[train_end:val_end].copy()
            test_df = mdf.iloc[val_end:].copy()
            print("Fallback chronological split used (70/15/15).")
        upper_cap = float(train_df["Min Delay"].quantile(0.995))
        for d in (train_df, val_df, test_df):
            d["Min Delay"] = d["Min Delay"].clip(upper=upper_cap)
        self.train_df, self.val_df, self.test_df = train_df, val_df, test_df
        print(f"Train {train_df.shape} | Val {val_df.shape} | Test {test_df.shape} | cap={upper_cap:.2f}")

    def build_preprocessor(self) -> ColumnTransformer:
        assert self.train_df is not None and self.val_df is not None and self.test_df is not None
        mdf = self.model_df
        assert mdf is not None
        features = [c for c in self.CANDIDATE_FEATURES if c in mdf.columns]
        categorical = [c for c in ["Vehicle_Type"] if c in features]
        numeric = [c for c in features if c not in categorical]
        self.features = features
        self.categorical_features = categorical
        self.numeric_features = numeric
        pre = ColumnTransformer(
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
        X_train = self.train_df[features].copy()
        y_train = self.train_df["Min Delay"].copy()
        X_val = self.val_df[features].copy()
        y_val = self.val_df["Min Delay"].copy()
        X_test = self.test_df[features].copy()
        y_test = self.test_df["Min Delay"].copy()
        pre.fit(X_train)
        self._X_train_t = pre.transform(X_train)
        self._X_val_t = pre.transform(X_val)
        self._X_test_t = pre.transform(X_test)
        self._y_train = y_train
        self._y_val = y_val
        self._y_test = y_test
        self.preprocessor = pre
        print(f"Inference-safe features: {len(features)}")
        return pre

    def train_lightgbm(self) -> LGBMRegressor:
        assert self._X_train_t is not None
        lgbm = LGBMRegressor(
            n_estimators=700,
            learning_rate=0.03,
            num_leaves=63,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=self._config.random_seed,
            objective="regression",
            n_jobs=-1,
        )
        lgbm.fit(self._X_train_t, self._y_train)
        self.lgbm = lgbm
        print("LightGBM trained.")
        return lgbm

    def train_xgboost(self) -> XGBRegressor:
        assert self._X_train_t is not None
        xgb = XGBRegressor(
            n_estimators=700,
            learning_rate=0.03,
            max_depth=8,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_lambda=1.0,
            random_state=self._config.random_seed,
            objective="reg:squarederror",
            n_jobs=-1,
        )
        xgb.fit(self._X_train_t, self._y_train)
        self.xgb = xgb
        print("XGBoost trained.")
        return xgb

    def compare_and_select_best(self) -> str:
        assert self.lgbm is not None and self.xgb is not None
        lgbm_val = self.lgbm.predict(self._X_val_t)
        lgbm_test = self.lgbm.predict(self._X_test_t)
        xgb_val = self.xgb.predict(self._X_val_t)
        xgb_test = self.xgb.predict(self._X_test_t)
        self.metrics = {
            "lightgbm": {
                "val": regression_metrics(self._y_val, lgbm_val),
                "test": regression_metrics(self._y_test, lgbm_test),
            },
            "xgboost": {
                "val": regression_metrics(self._y_val, xgb_val),
                "test": regression_metrics(self._y_test, xgb_test),
            },
        }
        self.best_model_name = min(self.metrics.keys(), key=lambda m: self.metrics[m]["val"]["rmse"])
        self.best_model = self.lgbm if self.best_model_name == "lightgbm" else self.xgb
        print(json.dumps(self.metrics, indent=2))
        print(f"Best model (val RMSE): {self.best_model_name}")
        return self.best_model_name

    def export_production_bundle(self) -> None:
        assert (
            self.train_df is not None
            and self.val_df is not None
            and self.test_df is not None
            and self.best_model is not None
        )
        art = self._config.artifacts_dir
        art.mkdir(parents=True, exist_ok=True)
        trainval_df = pd.concat([self.train_df, self.val_df], axis=0, ignore_index=True)
        X_trainval = trainval_df[self.features].copy()
        y_trainval = trainval_df["Min Delay"].copy()
        X_test_final = self.test_df[self.features].copy()
        y_test_final = self.test_df["Min Delay"].copy()
        final_preprocessor = ColumnTransformer(
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
                    self.categorical_features,
                ),
                (
                    "num",
                    Pipeline([("imputer", SimpleImputer(strategy="median"))]),
                    self.numeric_features,
                ),
            ],
            remainder="drop",
        )
        X_trainval_t = final_preprocessor.fit_transform(X_trainval)
        X_test_final_t = final_preprocessor.transform(X_test_final)
        final_model = self.best_model.__class__(**self.best_model.get_params())
        final_model.fit(X_trainval_t, y_trainval)
        final_test_pred = final_model.predict(X_test_final_t)
        final_test_metrics = regression_metrics(y_test_final, final_test_pred)
        production_bundle = {
            "model": final_model,
            "preprocessor": final_preprocessor,
            "features": self.features,
            "categorical_features": self.categorical_features,
            "numeric_features": self.numeric_features,
            "target_name": "Min Delay",
            "vehicle_scope": ["BUS", "STREETCAR", "SUBWAY"],
            "best_model_name": self.best_model_name,
            "validation_metrics": self.metrics[self.best_model_name]["val"],
            "test_metrics_before_refit": self.metrics[self.best_model_name]["test"],
            "test_metrics_after_refit": final_test_metrics,
        }
        joblib.dump(self.preprocessor, art / "preprocessor_all_modes.joblib")
        joblib.dump(self.lgbm, art / "lgbm_all_modes.joblib")
        joblib.dump(self.xgb, art / "xgb_all_modes.joblib")
        joblib.dump(self.best_model, art / "best_model_all_modes.joblib")
        joblib.dump(production_bundle, art / "model.pkl")
        export_metrics = {
            **self.metrics,
            "production_bundle": {
                "best_model_name": self.best_model_name,
                "test_metrics_after_refit": final_test_metrics,
                "features": self.features,
            },
        }
        with open(art / "metrics_all_modes.json", "w", encoding="utf-8") as f:
            json.dump(export_metrics, f, indent=2)
        test_df = self.test_df
        heatmap_df = test_df[["EventDateTime", "Latitude", "Longitude", "Vehicle_Type", "Month"]].copy()
        heatmap_df["pred_delay_min"] = final_test_pred
        heatmap_df["Hour"] = heatmap_df["EventDateTime"].dt.hour
        heatmap_df["DayOfWeek"] = heatmap_df["EventDateTime"].dt.dayofweek
        heatmap_df["Latitude_Bin"] = heatmap_df["Latitude"].round(3)
        heatmap_df["Longitude_Bin"] = heatmap_df["Longitude"].round(3)
        heatmap_agg = (
            heatmap_df.dropna(subset=["Latitude", "Longitude"])
            .groupby(
                ["Vehicle_Type", "Month", "DayOfWeek", "Hour", "Latitude_Bin", "Longitude_Bin"],
                as_index=False,
            )
            .agg(
                pred_delay_mean=("pred_delay_min", "mean"),
                pred_delay_p90=("pred_delay_min", lambda x: np.percentile(x, 90)),
                n_events=("pred_delay_min", "size"),
            )
        )
        heatmap_agg.to_csv(art / "heatmap_predictions_test_agg.csv", index=False)
        gcfg = heatmap_df.dropna(subset=["Latitude", "Longitude"])
        meta_out = {
            "vehicle_types": sorted(gcfg["Vehicle_Type"].dropna().unique().tolist()),
            "months": sorted(gcfg["Month"].dropna().astype(int).unique().tolist()),
            "days_of_week": sorted(gcfg["DayOfWeek"].dropna().astype(int).unique().tolist()),
            "hours": sorted(gcfg["Hour"].dropna().astype(int).unique().tolist()),
        }
        bins_unique = gcfg[["Latitude_Bin", "Longitude_Bin"]].drop_duplicates()
        bins_out = [
            {"latitude_bin": float(r["Latitude_Bin"]), "longitude_bin": float(r["Longitude_Bin"])}
            for _, r in bins_unique.iterrows()
        ]
        with open(art / "heatmap_inference_config.json", "w", encoding="utf-8") as f:
            json.dump({"metadata": meta_out, "bins": bins_out}, f, indent=2)
        print(f"Artifacts written to {art}")
        for p in sorted(art.glob("*")):
            print(f" - {p.name}")

    def run_full_training(self, df: Optional[pd.DataFrame] = None) -> None:
        self.load_modeling_dataframe(df)
        self.clean_target_and_time()
        self.temporal_split_and_cap()
        self.build_preprocessor()
        self.train_lightgbm()
        self.train_xgboost()
        self.compare_and_select_best()
        self.export_production_bundle()
