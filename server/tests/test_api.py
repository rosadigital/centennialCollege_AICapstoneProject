"""HTTP-level tests against the FastAPI app (uses session artifacts from ``conftest``)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "model_file" in body


def test_metadata_shape() -> None:
    r = client.get("/metadata")
    assert r.status_code == 200
    data = r.json()
    for key in ("vehicle_types", "months", "days_of_week", "hours"):
        assert key in data
        assert isinstance(data[key], list)
        assert len(data[key]) > 0


def test_heatmap_success() -> None:
    r = client.get(
        "/heatmap",
        params={
            "vehicle_type": "BUS",
            "month": 6,
            "day_of_week": 3,
            "hour": 14,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "points" in data and "kpis" in data
    assert data["kpis"]["point_count"] == len(data["points"])


def test_heatmap_validation_error_month() -> None:
    r = client.get(
        "/heatmap",
        params={
            "vehicle_type": "BUS",
            "month": 13,
            "day_of_week": 1,
            "hour": 10,
        },
    )
    assert r.status_code == 422


def test_predict_success() -> None:
    r = client.post(
        "/predict",
        json={
            "vehicle_type": "STREETCAR",
            "month": 4,
            "day_of_week": 5,
            "hour": 9,
            "latitude": 43.65,
            "longitude": -79.38,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "predicted_delay_minutes" in body
    assert isinstance(body["predicted_delay_minutes"], (int, float))
    assert body["predicted_delay_minutes"] >= 0


def test_predict_validation_invalid_vehicle() -> None:
    r = client.post(
        "/predict",
        json={
            "vehicle_type": "FERRY",
            "month": 4,
            "day_of_week": 1,
            "hour": 10,
            "latitude": 43.0,
            "longitude": -79.0,
        },
    )
    assert r.status_code == 422
