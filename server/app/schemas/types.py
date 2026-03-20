from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class PredictRequest(BaseModel):
    vehicle_type: Literal["BUS", "STREETCAR", "SUBWAY"]
    month: int = Field(ge=1, le=12)
    day_of_week: int = Field(ge=0, le=6)
    hour: int = Field(ge=0, le=23)
    latitude: float
    longitude: float
    include_time_decay: bool = False


class PredictResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    predicted_delay_minutes: float
    model_name: str
