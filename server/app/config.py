from pathlib import Path
import os


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACTS_DIR = ROOT_DIR / "aiProject" / "outputs" / "model_artifacts"

ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", str(DEFAULT_ARTIFACTS_DIR)))
MODEL_FILE = Path(os.getenv("MODEL_FILE", str(ARTIFACTS_DIR / "model.pkl")))
HEATMAP_FILE = Path(
    os.getenv("HEATMAP_FILE", str(ARTIFACTS_DIR / "heatmap_predictions_test_agg.csv"))
)

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
