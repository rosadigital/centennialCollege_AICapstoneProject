"""High-level orchestration: EDA phase + optional training phase."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from .config import PipelineConfig
from .eda_stages import (
    BaselineExplorer,
    DatasetValidator,
    FeatureEngineer,
    GeoMissingSummary,
    ImbalanceAnalyzer,
    MissingDelayRecoverabilityAudit,
    MissingValueAnalyzer,
    MissingValueHandler,
    NormalizationTransformer,
    ProcessedDatasetWriter,
    ProcessedEDAExplorer,
    ProcessedSummaryReporter,
    TargetVariableBuilder,
    UnifiedDataLoader,
)
class TTCDelayPipeline:
    """
    Facade over EDA components and :class:`ModelTrainingPipeline`.

    Mirrors the notebook flow: import → clean → features → save CSV → train → ``model.pkl``.
    """

    def __init__(self, config: Optional[PipelineConfig] = None) -> None:
        self.config = config or PipelineConfig()
        self._loader = UnifiedDataLoader(self.config)
        self._validator = DatasetValidator()
        self._baseline = BaselineExplorer()
        self._delay_audit = MissingDelayRecoverabilityAudit()
        self._missing_report = MissingValueAnalyzer(self.config)
        self._missing_handler = MissingValueHandler()
        self._geo = GeoMissingSummary()
        self._features = FeatureEngineer()
        self._target = TargetVariableBuilder(self.config)
        self._norm = NormalizationTransformer(self.config)
        self._imbalance = ImbalanceAnalyzer(self.config)
        self._summary = ProcessedSummaryReporter()
        self._writer = ProcessedDatasetWriter(self.config)
        self._processed_eda = ProcessedEDAExplorer(self.config)
        self._df: Optional[pd.DataFrame] = None

    def run_eda_phase(self) -> pd.DataFrame:
        """Execute sections 1–10 (+ appendix plots) and write the treated CSV."""
        print("=" * 70 + "\nUNIFIED DATA IMPORT\n" + "=" * 70)
        df = self._loader.load()
        print("=" * 70 + "\nSCHEMA VALIDATION\n" + "=" * 70)
        self._validator.print_dtypes(df)
        self._validator.validate_columns(df)
        df = self._validator.parse_and_filter_years(df)
        print("=" * 70 + "\nBASELINE EXPLORATION\n" + "=" * 70)
        self._baseline.explore(df)
        self._delay_audit.audit(df)
        print("=" * 70 + "\nMISSING VALUES (before)\n" + "=" * 70)
        self._missing_report.report(df)
        df = self._missing_handler.transform(df)
        print("=" * 70 + "\nGEO MISSING BY VEHICLE\n" + "=" * 70)
        print(self._geo.summarize(df).to_string(index=False))
        print("=" * 70 + "\nFEATURE ENGINEERING\n" + "=" * 70)
        df = self._features.transform(df)
        print("=" * 70 + "\nTARGET\n" + "=" * 70)
        df = self._target.add_categories(df)
        self._target.plot_distributions(df)
        print("=" * 70 + "\nNORMALIZATION ASSESSMENT\n" + "=" * 70)
        print(self._norm.assess(df).to_string(index=False))
        df = self._norm.transform(df)
        print("=" * 70 + "\nIMBALANCE\n" + "=" * 70)
        self._imbalance.print_tables(df)
        self._imbalance.plot_imbalance(df)
        print("=" * 70 + "\nPROCESSED SUMMARY\n" + "=" * 70)
        self._summary.summarize(df)
        self._imbalance.plot_imbalance_secondary(df)
        print("=" * 70 + "\nSAVE PROCESSED\n" + "=" * 70)
        self._writer.save(df)
        print("=" * 70 + "\nEDA ON PROCESSED\n" + "=" * 70)
        self._processed_eda.correlation_processed(df)
        self._processed_eda.temporal_patterns(df)
        print("=" * 70 + "\nNORMALIZATION CHECK (processed)\n" + "=" * 70)
        print(self._norm.assess(df).to_string(index=False))
        self._processed_eda.appendix_correlation_raw_numerics(df)
        self._df = df
        return df

    def run_training_phase(self, df: Optional[pd.DataFrame] = None) -> None:
        """Train models and write ``model.pkl`` + heatmap CSV (uses treated file if ``df`` is None)."""
        from .training_stages import ModelTrainingPipeline

        ModelTrainingPipeline(self.config).run_full_training(df)

    def run_all(self) -> None:
        df = self.run_eda_phase()
        self.run_training_phase(df)

    @property
    def dataframe(self) -> Optional[pd.DataFrame]:
        """Last dataframe produced by :meth:`run_eda_phase`."""
        return self._df
