from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS, HEATMAP_FILE, HEATMAP_INFERENCE_CONFIG, MODEL_FILE
from app.schemas.types import PredictRequest, PredictResponse
from app.services.heatmap_service import HeatmapService
from app.services.model_service import ModelService


app = FastAPI(title="TTC Delay Heatmap API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model_service = ModelService()
heatmap_service = HeatmapService(model_service)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model_file": str(MODEL_FILE),
        "heatmap_file": str(HEATMAP_FILE),
        "heatmap_inference_config": str(HEATMAP_INFERENCE_CONFIG),
    }


@app.get("/metadata")
def metadata() -> dict:
    return heatmap_service.metadata()


@app.get("/heatmap")
def heatmap(
    vehicle_type: str = Query(...),
    month: int = Query(..., ge=1, le=12),
    day_of_week: int = Query(..., ge=0, le=6),
    hour: int = Query(..., ge=0, le=23),
    include_time_decay: bool = Query(False),
) -> dict:
    try:
        return heatmap_service.query(
            vehicle_type=vehicle_type,
            month=month,
            day_of_week=day_of_week,
            hour=hour,
            include_time_decay=include_time_decay,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest) -> PredictResponse:
    try:
        pred = model_service.predict_single(
            vehicle_type=payload.vehicle_type,
            month=payload.month,
            day_of_week=payload.day_of_week,
            hour=payload.hour,
            latitude=payload.latitude,
            longitude=payload.longitude,
            include_time_decay=payload.include_time_decay,
        )
        return PredictResponse(
            predicted_delay_minutes=pred,
            model_name=model_service.model_name,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
