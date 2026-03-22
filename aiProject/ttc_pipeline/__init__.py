"""
Object-oriented port of ``01_EDA_TTC_Delay_Prediction.ipynb``.

Run: ``python -m aiProject.ttc_pipeline`` from the repository root
(see ``__main__.py``), or import ``TTCDelayPipeline`` from this package.
"""

from .config import PipelineConfig
from .orchestrator import TTCDelayPipeline

__all__ = ["PipelineConfig", "TTCDelayPipeline"]
