"""Pydantic request validation (no API or model load beyond schema import)."""

import pytest
from pydantic import ValidationError

from app.schemas.types import PredictRequest


def test_predict_request_accepts_valid_payload() -> None:
    req = PredictRequest(
        vehicle_type="BUS",
        month=3,
        day_of_week=2,
        hour=14,
        latitude=43.65,
        longitude=-79.38,
    )
    assert req.include_time_decay is False


def test_predict_request_rejects_invalid_vehicle() -> None:
    with pytest.raises(ValidationError):
        PredictRequest(
            vehicle_type="TRAIN",  # type: ignore[arg-type]
            month=3,
            day_of_week=2,
            hour=14,
            latitude=43.65,
            longitude=-79.38,
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("month", 0),
        ("month", 13),
        ("day_of_week", 7),
        ("hour", 24),
    ],
)
def test_predict_request_range_constraints(field: str, value: int) -> None:
    base = dict(
        vehicle_type="SUBWAY",
        month=6,
        day_of_week=3,
        hour=10,
        latitude=43.7,
        longitude=-79.4,
    )
    base[field] = value
    with pytest.raises(ValidationError):
        PredictRequest(**base)
