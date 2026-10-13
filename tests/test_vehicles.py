from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from backend.database import get_db
from backend.dependencies import get_current_user_id
from backend.main import app
from backend.models.vehicles import EngineType, Vehicle, VehicleTelemetry
from backend.repositories.vehicles import VehicleRepository
from backend.services import vehicles as vehicle_service

client = TestClient(app)
PAYLOAD = {
    "engine_type": "electric",
    "nickname": "Daily driver",
    "total_capacity": 75,
    "telemetry": {
        "current_fuel": 50,
        "avg_consumption": 18,
        "service_due_km": 10000,
        "service_due_date": "2027-01-01T00:00:00Z",
    },
}


@pytest.fixture
def repository(monkeypatch):
    repository = Mock(spec=VehicleRepository)
    vehicle = Vehicle(
        owner_id="user-1",
        vehicle_id="vehicle-1",
        vehicle_nickname="Daily driver",
        engine_type=EngineType.ELECTRIC,
        total_capacity=75,
        telemetry=VehicleTelemetry("vehicle-1", 50, 18, 10000, datetime(2027, 1, 1, tzinfo=UTC)),
    )
    repository.get_vehicle_by_id.return_value = vehicle
    repository.get_vehicle_by_owner_id.return_value = [vehicle]
    repository.create_vehicle.side_effect = lambda created: created
    repository.update_partial_vehicle.return_value = vehicle
    repository.update_telemetry.return_value = vehicle
    monkeypatch.setattr(vehicle_service, "SqlVehicleRepository", lambda db: repository)
    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    app.dependency_overrides[get_db] = lambda: object()
    yield repository
    app.dependency_overrides.clear()


def test_vehicle_create_list_read_and_status(repository):
    response = client.post("/vehicles", json=PAYLOAD)
    assert response.status_code == 201
    assert response.json()["owner_id"] == "user-1"
    assert response.json()["nickname"] == "Daily driver"
    created = repository.create_vehicle.call_args.args[0]
    assert created.vehicle_id == created.telemetry.vehicle_id
    assert client.get("/vehicles").json()[0]["vehicle_id"] == "vehicle-1"
    assert client.get("/vehicles/vehicle-1").status_code == 200
    assert client.get("/vehicles/vehicle-1/status").json()["current_fuel"] == 50


def test_vehicle_create_preserves_capacity_validation(repository):
    response = client.post("/vehicles", json={**PAYLOAD, "total_capacity": 25})
    assert response.status_code == 400
    assert response.json()["detail"] == "Current fuel cannot exceed total capacity"
    repository.create_vehicle.assert_not_called()


@pytest.mark.parametrize("missing, expected_status", [(True, 404), (False, 403)])
def test_vehicle_access_checks_apply_to_all_operations(repository, missing, expected_status):
    if missing:
        repository.get_vehicle_by_id.return_value = None
    else:
        repository.get_vehicle_by_id.return_value.owner_id = "user-2"
    responses = [
        client.get("/vehicles/vehicle-1"),
        client.get("/vehicles/vehicle-1/status"),
        client.patch("/vehicles/vehicle-1", json={"nickname": "Changed"}),
        client.post("/vehicles/vehicle-1/telemetry", json=PAYLOAD["telemetry"]),
        client.delete("/vehicles/vehicle-1"),
    ]
    assert all(response.status_code == expected_status for response in responses)
    repository.update_partial_vehicle.assert_not_called()
    repository.update_telemetry.assert_not_called()
    repository.delete_vehicle.assert_not_called()


def test_vehicle_update_telemetry_and_delete(repository):
    assert client.patch("/vehicles/vehicle-1", json={}).status_code == 200
    repository.update_partial_vehicle.assert_not_called()
    assert client.patch("/vehicles/vehicle-1", json={"nickname": "Changed"}).status_code == 200
    assert repository.update_partial_vehicle.call_args.args[1] == {"nickname": "Changed"}
    assert client.post("/vehicles/vehicle-1/telemetry", json=PAYLOAD["telemetry"]).status_code == 200
    assert repository.update_telemetry.call_args.args[1].vehicle_id == "vehicle-1"
    assert client.delete("/vehicles/vehicle-1").status_code == 204
    repository.delete_vehicle.assert_called_once_with("vehicle-1")


def test_vehicle_endpoints_require_authentication(repository):
    app.dependency_overrides.pop(get_current_user_id)
    assert client.get("/vehicles").status_code == 401