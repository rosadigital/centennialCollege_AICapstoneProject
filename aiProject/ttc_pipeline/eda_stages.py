"""EDA, cleaning, feature engineering, and processed export (notebook sections 1–10 + appendix)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.preprocessing import RobustScaler, StandardScaler

from .config import PipelineConfig


class UnifiedDataLoader:
    """Load the unified TTC CSV from ``PipelineConfig.unified_file``."""

    def __init__(self, config: PipelineConfig) -> None:
        self._config = config

    def load(self) -> pd.DataFrame:
        path = self._config.unified_file
        if not path.exists():
            raise FileNotFoundError(f"Unified file not found: {path}")
        df = pd.read_csv(path)
        print(f"Loaded {path.name}: {df.shape[0]:,} rows × {df.shape[1]} columns")
        return df


class DatasetValidator:
    """Schema checks and datetime parsing (years 2017–2025)."""

    REQUIRED_COLUMNS = [
        "Vehicle_Type",
        "Date",
        "Line",
        "Time",
        "Day",
        "Station",
        "Code",
        "Description",
        "Min Delay",
        "Min Gap",
        "Bound",
        "Vehicle",
        "Latitude",
        "Longitude",
    ]

    def validate_columns(self, df: pd.DataFrame) -> list[str]:
        missing = [c for c in self.REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            print(f"⚠ Missing required columns: {missing}")
        else:
            print("✓ All required columns are present")
        return missing

    def print_dtypes(self, df: pd.DataFrame) -> None:
        print("\nColumns and dtypes:")
        for col, dt in df.dtypes.items():
            print(f"  {col:24s} -> {dt}")

    def parse_and_filter_years(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        date_parsed = pd.to_datetime(out["Date"], errors="coerce")
        time_parsed = pd.to_datetime(out["Time"], errors="coerce")
        out["Date"] = date_parsed
        print(f"\nDate parse rate: {date_parsed.notna().mean():.4f}")
        print(f"Time parse rate: {time_parsed.notna().mean():.4f}")
        if date_parsed.notna().any():
            print(f"  Min date: {date_parsed.min()}  Max date: {date_parsed.max()}")
        out = out[(out["Date"].dt.year >= 2017) & (out["Date"].dt.year <= 2025)]
        print(f"✓ Filtered to 2017–2025: {len(out):,} records")
        return out


class BaselineExplorer:
    """Lightweight counts on raw / partially cleaned data."""

    def explore(self, df: pd.DataFrame) -> None:
        print("\nTop 20 stations overall:")
        print(df["Station"].value_counts(dropna=False).head(20))
        print("\nTop 20 descriptions:")
        print(df["Description"].value_counts(dropna=False).head(20))
        for vt in sorted(df["Vehicle_Type"].dropna().unique()):
            print(f"\n{vt} — top 10 stations:")
            print(df[df["Vehicle_Type"] == vt]["Station"].value_counts(dropna=False).head(10))


class MissingDelayRecoverabilityAudit:
    """Estimate recoverable missing Min Delay via Line + Station groups."""

    def audit(self, df: pd.DataFrame) -> None:
        missing_delay = df[df["Min Delay"].isna()].copy()
        missing_delay = missing_delay.dropna(subset=["Line", "Station"])
        grouped = df.groupby(["Line", "Station"])["Min Delay"]
        recoverable: list[bool] = []
        for _, row in missing_delay.iterrows():
            key = (row["Line"], row["Station"])
            if key in grouped.groups:
                recoverable.append(grouped.get_group(key).notna().any())
            else:
                recoverable.append(False)
        total_missing = df["Min Delay"].isna().sum()
        total_recoverable = int(pd.Series(recoverable).sum()) if recoverable else 0
        print(f"Total rows with missing Min Delay: {total_missing:,}")
        if total_missing > 0:
            print(
                f"Potentially recoverable via Line+Station: {total_recoverable:,} "
                f"({100 * total_recoverable / total_missing:.2f}%)"
            )


class MissingValueAnalyzer:
    """Report missingness before handling."""

    def __init__(self, config: PipelineConfig) -> None:
        self._config = config

    def report(self, df: pd.DataFrame) -> None:
        missing_data = pd.DataFrame(
            {
                "Column": df.columns,
                "Missing_Count": df.isnull().sum().values,
                "Missing_Percentage": (df.isnull().sum() / len(df) * 100).values,
                "Data_Type": df.dtypes.values,
            }
        )
        missing_data = missing_data[missing_data["Missing_Count"] > 0].sort_values(
            "Missing_Count", ascending=False
        )
        if len(missing_data) == 0:
            print("✅ No missing values found!")
        else:
            print(missing_data.to_string(index=False))
            if self._config.show_plots:
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.barh(missing_data["Column"], missing_data["Missing_Percentage"], color="#e74c3c")
                ax.set_title("Missing Values by Column (%)", fontsize=14, fontweight="bold")
                ax.set_xlabel("Missing Percentage (%)")
                ax.grid(axis="x", alpha=0.3)
                plt.tight_layout()
                plt.show()


class MissingValueHandler:
    """Imputation strategy aligned with the notebook."""

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df_processed = df.copy()
        initial_missing = df_processed.isnull().sum().sum()
        if "Bound" in df_processed.columns:
            df_processed["Bound"] = df_processed["Bound"].fillna("Unknown")
        if "Vehicle" in df_processed.columns:
            for vtype in df_processed["Vehicle_Type"].unique():
                mode_vehicle = df_processed[df_processed["Vehicle_Type"] == vtype]["Vehicle"].mode()
                fill = mode_vehicle[0] if len(mode_vehicle) > 0 else 0
                mask = (df_processed["Vehicle_Type"] == vtype) & (df_processed["Vehicle"].isnull())
                df_processed.loc[mask, "Vehicle"] = fill
        for col in ("Line", "Station"):
            if col in df_processed.columns:
                df_processed[col] = df_processed[col].fillna("Unknown")
        for col in ("Min Delay", "Min Gap"):
            if col in df_processed.columns:
                for vtype in df_processed["Vehicle_Type"].unique():
                    med = df_processed[df_processed["Vehicle_Type"] == vtype][col].median()
                    mask = (df_processed["Vehicle_Type"] == vtype) & (df_processed[col].isnull())
                    df_processed.loc[mask, col] = med
        if "Date" in df_processed.columns:
            df_processed = df_processed.dropna(subset=["Date"])
        print(
            f"Missing values: {initial_missing:,} → {df_processed.isnull().sum().sum():,} "
            "(after handling)"
        )
        return df_processed


class GeoMissingSummary:
    """Latitude / longitude missingness by vehicle type."""

    def summarize(self, df: pd.DataFrame) -> pd.DataFrame:
        rows: list[dict] = []
        for vt, g in df.groupby("Vehicle_Type", dropna=False):
            n = len(g)
            ml = int(g["Latitude"].isna().sum())
            mo = int(g["Longitude"].isna().sum())
            mb = int((g["Latitude"].isna() & g["Longitude"].isna()).sum())
            rows.append(
                {
                    "Vehicle_Type": vt,
                    "n_rows": n,
                    "missing_lat": ml,
                    "missing_lon": mo,
                    "missing_both": mb,
                }
            )
        summary = pd.DataFrame(rows)
        summary["missing_lat_%"] = (summary["missing_lat"] / summary["n_rows"] * 100).round(2)
        summary["missing_lon_%"] = (summary["missing_lon"] / summary["n_rows"] * 100).round(2)
        summary["missing_both_%"] = (summary["missing_both"] / summary["n_rows"] * 100).round(2)
        return summary.sort_values("missing_lat", ascending=False)


class FeatureEngineer:
    """Temporal, cyclical, flags, delay ratio, and vehicle encoding."""

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["Year"] = out["Date"].dt.year
        out["Month"] = out["Date"].dt.month
        out["DayOfWeek"] = out["Date"].dt.dayofweek
        out["DayName"] = out["Date"].dt.day_name()
        out["DayOfMonth"] = out["Date"].dt.day
        out["WeekOfYear"] = out["Date"].dt.isocalendar().week.astype(int)
        t = pd.to_datetime(out["Time"], format="%H:%M:%S", errors="coerce")
        out["Hour"] = t.dt.hour
        out["Minute"] = t.dt.minute
        out["Hour_sin"] = np.sin(2 * np.pi * out["Hour"] / 24)
        out["Hour_cos"] = np.cos(2 * np.pi * out["Hour"] / 24)
        out["DayOfWeek_sin"] = np.sin(2 * np.pi * out["DayOfWeek"] / 7)
        out["DayOfWeek_cos"] = np.cos(2 * np.pi * out["DayOfWeek"] / 7)
        out["Month_sin"] = np.sin(2 * np.pi * out["Month"] / 12)
        out["Month_cos"] = np.cos(2 * np.pi * out["Month"] / 12)
        out["IsWeekend"] = (out["DayOfWeek"] >= 5).astype(int)
        def _hour_flag(h: float, fn) -> int:
            if pd.isna(h):
                return 0
            hi = int(h)
            return 1 if fn(hi) else 0

        out["IsRushHour"] = out["Hour"].apply(
            lambda x: _hour_flag(x, lambda hi: (7 <= hi <= 9) or (17 <= hi <= 19))
        )
        out["IsPeakHour"] = out["Hour"].apply(
            lambda x: _hour_flag(x, lambda hi: (6 <= hi <= 10) or (15 <= hi <= 20))
        )
        out["IsNight"] = out["Hour"].apply(
            lambda x: _hour_flag(x, lambda hi: (22 <= hi <= 23) or (0 <= hi <= 5))
        )
        out["Season"] = out["Month"].apply(
            lambda x: "Spring"
            if 3 <= x <= 5
            else "Summer"
            if 6 <= x <= 8
            else "Fall"
            if 9 <= x <= 11
            else "Winter"
        )
        out["Delay_Ratio"] = out["Min Delay"] / (out["Min Gap"] + 1)
        out["Vehicle_Type_Encoded"] = out["Vehicle_Type"].astype("category").cat.codes
        print(f"Feature-engineered shape: {out.shape}")
        return out


class TargetVariableBuilder:
    """Target stats, categories, and optional distribution plots."""

    def __init__(self, config: PipelineConfig) -> None:
        self._config = config
        self.target_variable = "Min Delay"

    def add_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["Delay_Category"] = pd.cut(
            out[self.target_variable],
            bins=[0, 5, 15, 30, float("inf")],
            labels=["Low (0-5min)", "Medium (5-15min)", "High (15-30min)", "Very High (30+min)"],
        )
        return out

    def plot_distributions(self, df: pd.DataFrame) -> None:
        if not self._config.show_plots:
            return
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        t = self.target_variable
        axes[0].hist(df[t].dropna(), bins=50, color="#3498db", edgecolor="black", alpha=0.7)
        axes[0].set_title("Target: Min Delay", fontweight="bold")
        axes[0].axvline(df[t].mean(), color="red", linestyle="--", label=f"Mean: {df[t].mean():.2f}")
        axes[0].axvline(
            df[t].median(), color="green", linestyle="--", label=f"Median: {df[t].median():.2f}"
        )
        axes[0].legend()
        delay_cat_counts = df["Delay_Category"].value_counts()
        axes[1].bar(
            range(len(delay_cat_counts)),
            delay_cat_counts.values,
            color=["#2ecc71", "#f39c12", "#e67e22", "#e74c3c"],
        )
        axes[1].set_title("Delay categories")
        axes[1].set_xticks(range(len(delay_cat_counts)))
        axes[1].set_xticklabels([str(x) for x in delay_cat_counts.index], rotation=45, ha="right")
        plt.tight_layout()
        plt.show()


class NormalizationTransformer:
    """Log / robust / standard scaling as in the notebook."""

    def assess(self, df: pd.DataFrame) -> pd.DataFrame:
        numerical_features = ["Min Delay", "Min Gap", "Vehicle", "Hour", "Delay_Ratio"]
        rows = []
        for col in numerical_features:
            if col not in df.columns:
                continue
            data = df[col].dropna()
            mean_val = float(data.mean())
            std_val = float(data.std())
            min_val = float(data.min())
            max_val = float(data.max())
            range_val = max_val - min_val
            cv = std_val / mean_val if mean_val != 0 else np.inf
            rows.append(
                {
                    "Feature": col,
                    "Mean": mean_val,
                    "Std": std_val,
                    "Min": min_val,
                    "Max": max_val,
                    "Range": range_val,
                    "CV": cv,
                    "Needs_Normalization": abs(cv) > 1 or range_val > 100,
                }
            )
        return pd.DataFrame(rows)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["Min_Delay_Original"] = out["Min Delay"].copy()
        out["Min_Gap_Original"] = out["Min Gap"].copy()
        out["Min_Delay_Log"] = np.log1p(out["Min Delay"])
        scaler_gap = RobustScaler()
        out["Min_Gap_Scaled"] = scaler_gap.fit_transform(out[["Min Gap"]])
        if "Vehicle" in out.columns:
            scaler_v = StandardScaler()
            out["Vehicle_Scaled"] = scaler_v.fit_transform(out[["Vehicle"]])
        if "Delay_Ratio" in out.columns:
            scaler_r = RobustScaler()
            out["Delay_Ratio_Scaled"] = scaler_r.fit_transform(out[["Delay_Ratio"]])
        if self._show_plots():
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            axes[0, 0].hist(out["Min_Delay_Original"].dropna(), bins=50, color="#3498db", alpha=0.7)
            axes[0, 0].set_title("Original Min Delay")
            axes[0, 1].hist(out["Min_Delay_Log"].dropna(), bins=50, color="#2ecc71", alpha=0.7)
            axes[0, 1].set_title("Log Min Delay")
            axes[1, 0].hist(out["Min_Gap_Original"].dropna(), bins=50, color="#e74c3c", alpha=0.7)
            axes[1, 0].set_title("Original Min Gap")
            axes[1, 1].hist(out["Min_Gap_Scaled"].dropna(), bins=50, color="#9b59b6", alpha=0.7)
            axes[1, 1].set_title("Scaled Min Gap")
            plt.tight_layout()
            plt.show()
        return out

    def __init__(self, config: PipelineConfig) -> None:
        self._config = config

    def _show_plots(self) -> bool:
        return self._config.show_plots


class ImbalanceAnalyzer:
    """Year × vehicle tables and imbalance plots."""

    def __init__(self, config: PipelineConfig) -> None:
        self._config = config

    def print_tables(self, df: pd.DataFrame) -> None:
        imbalance_matrix = pd.crosstab(df["Year"], df["Vehicle_Type"], margins=True)
        print(imbalance_matrix)
        print("\nRow %:")
        print((pd.crosstab(df["Year"], df["Vehicle_Type"], normalize="index") * 100).round(2))

    def plot_imbalance(self, df: pd.DataFrame) -> None:
        if not self._config.show_plots:
            return
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        imbalance_counts = pd.crosstab(df["Year"], df["Vehicle_Type"])
        imbalance_counts.plot(
            kind="bar", ax=axes[0, 0], color=["#3498db", "#e74c3c", "#2ecc71"], width=0.8
        )
        axes[0, 0].set_title("Volume by Year and Vehicle")
        (pd.crosstab(df["Year"], df["Vehicle_Type"], normalize="index") * 100).plot(
            kind="bar", stacked=True, ax=axes[0, 1], color=["#3498db", "#e74c3c", "#2ecc71"], width=0.8
        )
        axes[0, 1].set_title("Distribution % by Year")
        yearly_counts = df.groupby("Year").size()
        growth_rate = yearly_counts.pct_change() * 100
        axes[1, 0].bar(growth_rate.index.astype(str), growth_rate.values)
        axes[1, 0].set_title("YoY growth %")
        vc = df["Vehicle_Type"].value_counts()
        axes[1, 1].bar(vc.index, vc.values, color=["#3498db", "#e74c3c", "#2ecc71"])
        axes[1, 1].set_title("Vehicle type counts")
        plt.tight_layout()
        plt.show()

    def plot_imbalance_secondary(self, df: pd.DataFrame) -> None:
        if not self._config.show_plots:
            return
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        imbalance_counts = pd.crosstab(df["Year"], df["Vehicle_Type"])
        imbalance_counts.plot(
            kind="bar", ax=axes[0, 0], color=["#3498db", "#e74c3c", "#2ecc71"], width=0.8
        )
        (pd.crosstab(df["Year"], df["Vehicle_Type"], normalize="index") * 100).plot(
            kind="bar", stacked=True, ax=axes[0, 1], color=["#3498db", "#e74c3c", "#2ecc71"], width=0.8
        )
        cv_by_year = df.groupby("Year")["Vehicle_Type"].apply(
            lambda x: x.value_counts().std() / x.value_counts().mean()
        )
        axes[1, 0].bar(cv_by_year.index.astype(str), cv_by_year.values, color="#9b59b6")
        axes[1, 0].set_title("CV by year")
        yearly_counts = df.groupby("Year").size()
        growth_rate = yearly_counts.pct_change() * 100
        axes[1, 1].bar(growth_rate.index.astype(str), growth_rate.values)
        plt.tight_layout()
        plt.show()


class ProcessedDatasetWriter:
    """Persist treated columns for the modeling stage."""

    COLUMNS_TO_SAVE = [
        "Vehicle_Type",
        "Date",
        "Time",
        "Day",
        "Line",
        "Station",
        "Code",
        "Bound",
        "Vehicle",
        "Min Delay",
        "Min Gap",
        "Year",
        "Month",
        "DayOfWeek",
        "DayName",
        "DayOfMonth",
        "WeekOfYear",
        "Hour",
        "Minute",
        "Hour_sin",
        "Hour_cos",
        "DayOfWeek_sin",
        "DayOfWeek_cos",
        "Month_sin",
        "Month_cos",
        "IsWeekend",
        "IsRushHour",
        "IsPeakHour",
        "IsNight",
        "Season",
        "Delay_Ratio",
        "Min_Delay_Log",
        "Min_Gap_Scaled",
        "Vehicle_Scaled",
        "Delay_Ratio_Scaled",
        "Vehicle_Type_Encoded",
        "Delay_Category",
        "Latitude",
        "Longitude",
    ]

    def __init__(self, config: PipelineConfig) -> None:
        self._config = config

    def save(self, df: pd.DataFrame) -> Path:
        self._config.output_dir.mkdir(parents=True, exist_ok=True)
        cols = [c for c in self.COLUMNS_TO_SAVE if c in df.columns]
        out_df = df[cols].copy()
        path = self._config.processed_file
        out_df.to_csv(path, index=False)
        mb = path.stat().st_size / (1024 * 1024)
        print(f"✓ Saved {path} ({out_df.shape[0]:,} × {out_df.shape[1]}, {mb:.2f} MB)")
        return path


class ProcessedEDAExplorer:
    """Correlation heatmaps and temporal plots on processed data."""

    def __init__(self, config: PipelineConfig) -> None:
        self._config = config

    def correlation_processed(self, df: pd.DataFrame) -> None:
        corr_features = [
            "Min Delay",
            "Min_Delay_Log",
            "Min_Gap_Scaled",
            "Delay_Ratio_Scaled",
            "Hour_sin",
            "Hour_cos",
            "DayOfWeek_sin",
            "DayOfWeek_cos",
            "IsWeekend",
            "IsRushHour",
            "IsPeakHour",
            "IsNight",
            "Year",
            "Month",
        ]
        corr_features = [f for f in corr_features if f in df.columns]
        if len(corr_features) < 2:
            return
        cm = df[corr_features].corr()
        print("\nCorrelations with Min Delay:\n", cm["Min Delay"].sort_values(ascending=False))
        if self._config.show_plots:
            plt.figure(figsize=(14, 12))
            sns.heatmap(cm, annot=True, fmt=".3f", cmap="coolwarm", center=0, square=True)
            plt.title("Correlation — processed features")
            plt.tight_layout()
            plt.show()

    def temporal_patterns(self, df: pd.DataFrame) -> None:
        if not self._config.show_plots:
            return
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        monthly_avg = df.groupby("Month")["Min Delay"].mean()
        axes[0, 0].bar(range(1, 13), monthly_avg.reindex(range(1, 13)).values, color="#3498db")
        axes[0, 0].set_title("Avg delay by month")
        dow_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        dow_avg = df.groupby("DayName")["Min Delay"].mean().reindex(dow_order)
        axes[0, 1].bar(range(len(dow_order)), dow_avg.values, color="#e74c3c")
        axes[0, 1].set_xticks(range(len(dow_order)))
        axes[0, 1].set_xticklabels([d[:3] for d in dow_order], rotation=45)
        hourly_avg = df.groupby("Hour")["Min Delay"].mean()
        axes[1, 0].plot(hourly_avg.index, hourly_avg.values, marker="o", color="#2ecc71")
        axes[1, 0].set_title("Avg delay by hour")
        dbt = df.groupby("Vehicle_Type")["Min Delay"].mean()
        axes[1, 1].bar(dbt.index, dbt.values, color=["#3498db", "#e74c3c", "#2ecc71"])
        plt.tight_layout()
        plt.show()

    def appendix_correlation_raw_numerics(self, df: pd.DataFrame) -> None:
        corr_cols = ["Min Delay", "Min Gap", "Year", "Month", "DayOfWeek", "Hour", "Vehicle"]
        corr_cols = [c for c in corr_cols if c in df.columns]
        if len(corr_cols) < 2:
            return
        cm = df[corr_cols].corr()
        print(cm.round(3))
        if self._config.show_plots:
            plt.figure(figsize=(12, 10))
            sns.heatmap(cm, annot=True, fmt=".3f", cmap="coolwarm", center=0, square=True)
            plt.title("Appendix A — numeric correlation")
            plt.tight_layout()
            plt.show()


class ProcessedSummaryReporter:
    """Final shape / target stats before or after save."""

    def summarize(self, df: pd.DataFrame, target_variable: str = "Min Delay") -> None:
        print(f"Shape: {df.shape}")
        print(f"Date range: {df['Date'].min()} — {df['Date'].max()}")
        print(df["Vehicle_Type"].value_counts())
        rem = df.isnull().sum()
        rem = rem[rem > 0]
        print("Remaining missing:\n", rem if len(rem) else "None")
