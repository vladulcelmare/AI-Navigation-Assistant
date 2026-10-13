from uuid import uuid4
from datetime import UTC, datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.models.vehicles import Vehicle, VehicleTelemetry
from backend.repositories.vehicles import SqlVehicleRepository, VehicleRepository
from backend.schemas.vehicles import (
    VehicleCreateInput,
    VehicleInputOutput,
    VehicleStatusOutput,
    VehicleUpdateInput,
)
from backend.schemas.vehicles import VehicleTelemetry as VehicleTelemetrySchema


# Convert API telemetry into the domain telemetry value object.
def _to_domain_telemetry(telemetry: VehicleTelemetrySchema, vehicle_id: str) -> VehicleTelemetry:
    return VehicleTelemetry(
        vehicle_id=vehicle_id,
        current_fuel=telemetry.current_fuel,
        avg_consumption=telemetry.avg_consumption,
        service_due_km=telemetry.service_due_km,
        service_due_date=telemetry.service_due_date,
    )




# Convert a domain Vehicle entity into the API response schema.
def _to_vehicle_response(vehicle: Vehicle) -> VehicleInputOutput:
    return VehicleInputOutput(
        vehicle_id=vehicle.vehicle_id,
        owner_id=vehicle.owner_id,
        engine_type=vehicle.engine_type,
        nickname=vehicle.vehicle_nickname,
        total_capacity=vehicle.total_capacity,
        telemetry=VehicleTelemetrySchema(
            current_fuel=vehicle.telemetry.current_fuel,
            avg_consumption=vehicle.telemetry.avg_consumption,
            service_due_km=vehicle.telemetry.service_due_km,
            service_due_date=vehicle.telemetry.service_due_date,
        ),
    )




# Make sure the requested vehicle belongs to the current user.
def _get_owned_vehicle(repository: VehicleRepository, vehicle_id: str, owner_id: str) -> Vehicle:
    vehicle = repository.get_vehicle_by_id(vehicle_id)

    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Vehicle not found')

    if vehicle.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You do not have access to this vehicle')

    return vehicle


# Miro: create_vehicle()
# Repository: VehicleRepository.create_vehicle()
def create_vehicle(payload: VehicleCreateInput, current_user_id: str, db: Session) -> VehicleInputOutput:
    repository = SqlVehicleRepository(db)

    vehicle_id = str(uuid4())

    telemetry = _to_domain_telemetry(payload.telemetry, vehicle_id)

    if telemetry.current_fuel > payload.total_capacity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Current fuel cannot exceed total capacity')

    vehicle = Vehicle(
        owner_id=current_user_id,
        vehicle_id=vehicle_id,
        vehicle_nickname=payload.nickname,
        engine_type=payload.engine_type,
        total_capacity=payload.total_capacity,
        telemetry=telemetry
    )

    created_vehicle = repository.create_vehicle(vehicle)

    return _to_vehicle_response(created_vehicle)


# Miro: list_my_vehicles()
# Repository: VehicleRepository.get_vehicle_by_owner_id()
def list_my_vehicles(current_user_id: str, db: Session) -> list[VehicleInputOutput]:
    repository = SqlVehicleRepository(db)

    vehicles = repository.get_vehicle_by_owner_id(current_user_id)

    return [
        _to_vehicle_response(vehicle)
        for vehicle in (vehicles or [])
    ]


# Miro: get_vehicle()
# Repository: VehicleRepository.get_vehicle_by_id()
def get_vehicle(vehicle_id: str, current_user_id: str, db: Session) -> VehicleInputOutput:
    repository = SqlVehicleRepository(db)

    vehicle = _get_owned_vehicle(repository, vehicle_id, current_user_id)

    return _to_vehicle_response(vehicle)


# Miro: update_vehicle()
# Repository: VehicleRepository.update_partial_vehicle()
def update_vehicle(payload: VehicleUpdateInput, vehicle_id: str, current_user_id: str, db: Session) -> VehicleInputOutput:
    repository = SqlVehicleRepository(db)

    vehicle = _get_owned_vehicle(repository, vehicle_id, current_user_id)

    fields = payload.model_dump(exclude_unset=True, exclude_none=True)

    if not fields:
        return _to_vehicle_response(vehicle)

    updated_vehicle = repository.update_partial_vehicle(vehicle,fields)

    return _to_vehicle_response(updated_vehicle)


# Miro: delete_vehicle()
# Repository: VehicleRepository.delete_vehicle()
def delete_vehicle(vehicle_id: str, current_user_id: str, db: Session) -> None:
    repository = SqlVehicleRepository(db)

    vehicle = _get_owned_vehicle(
        repository,
        vehicle_id,
        current_user_id,
    )

    repository.delete_vehicle(vehicle.vehicle_id)


# Miro: record_telemetry()
# Repository: VehicleRepository.update_telemetry()
def record_telemetry(payload: VehicleTelemetrySchema, vehicle_id: str, current_user_id: str, db: Session) -> VehicleInputOutput:
    repository = SqlVehicleRepository(db)

    vehicle = _get_owned_vehicle(repository, vehicle_id, current_user_id)
    telemetry = _to_domain_telemetry(payload, vehicle_id)

    try:
        updated_vehicle = repository.update_telemetry(vehicle.vehicle_id, telemetry)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return _to_vehicle_response(updated_vehicle)


# Miro: get_vehicle_status()
# Repository: get_vehicle_by_id(), using the current telemetry data.
def get_vehicle_status(vehicle_id: str, current_user_id: str, db: Session) -> VehicleStatusOutput:
    repository = SqlVehicleRepository(db)

    vehicle = _get_owned_vehicle(repository, vehicle_id, current_user_id)

    return VehicleStatusOutput(
        vehicle_id=vehicle.vehicle_id,
        nickname=vehicle.vehicle_nickname,
        current_fuel=vehicle.telemetry.current_fuel,
        avg_consumption=vehicle.telemetry.avg_consumption,
        service_due_km=vehicle.telemetry.service_due_km,
        service_due_date=vehicle.telemetry.service_due_date,
    )

