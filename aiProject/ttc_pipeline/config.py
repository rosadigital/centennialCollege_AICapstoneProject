"""Paths and toggles for the TTC delay analysis pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


def default_repo_root() -> Path:
    """Repository root: parent of ``aiProject`` (this file lives in ``aiProject/ttc_pipeline``)."""
    return Path(__file__).resolve().parents[2]


@dataclass
class PipelineConfig:
    """Central configuration for loaders, writers, and training artifacts."""

    repo_root: Path = field(default_factory=default_repo_root)
    unified_csv_name: str = "ttc_delays_2017_2025_unified_with_coords_corrected.csv"
    processed_csv_name: str = "ttc_delays_2017_2025_unified_with_coords_corrected_treated.csv"
    show_plots: bool = True
    random_seed: int = 42

    @property
    def dataset_dir(self) -> Path:
        return self.repo_root / "dataset"

    @property
    def unified_file(self) -> Path:
        return self.dataset_dir / self.unified_csv_name

    @property
    def output_dir(self) -> Path:
        return self.repo_root / "aiProject" / "outputs"

    @property
    def processed_file(self) -> Path:
        return self.output_dir / self.processed_csv_name

    @property
    def artifacts_dir(self) -> Path:
        return self.output_dir / "model_artifacts"
