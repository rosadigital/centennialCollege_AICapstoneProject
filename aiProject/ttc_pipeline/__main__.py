"""CLI entry: run from repository root with ``python -m aiProject.ttc_pipeline``."""

from __future__ import annotations

import argparse

from .config import PipelineConfig
from .orchestrator import TTCDelayPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="TTC delay EDA + training (OOP port of the notebook).")
    parser.add_argument(
        "phase",
        nargs="?",
        default="all",
        choices=("eda", "training", "all"),
        help="eda: clean & save treated CSV; training: fit models (needs treated CSV); all: both",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip matplotlib figures (useful in headless CI).",
    )
    args = parser.parse_args()
    config = PipelineConfig(show_plots=not args.no_plots)
    pipe = TTCDelayPipeline(config)
    if args.phase == "eda":
        pipe.run_eda_phase()
    elif args.phase == "training":
        pipe.run_training_phase()
    else:
        pipe.run_all()


if __name__ == "__main__":
    main()
