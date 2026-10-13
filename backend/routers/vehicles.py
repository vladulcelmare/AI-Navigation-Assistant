from typing import Annotated
from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user_id
from backend.schemas.vehicles import (
    VehicleCreateInput,
    VehicleInputOutput,
    VehicleStatusOutput,
    VehicleUpdateInput,
)
from backend.schemas.vehicles import VehicleTelemetry as VehicleTelemetrySchema
from backend.services import vehicles as service

router = APIRouter(prefix='/vehicles', tags=['Vehicles'])


@router.post('', response_model=VehicleInputOutput, status_code=status.HTTP_201_CREATED)
def create_vehicle(payload: VehicleCreateInput, current_user_id: Annotated[str, Depends(get_current_user_id)], db: Annotated[Session, Depends(get_db)]) -> VehicleInputOutput:
    return service.create_vehicle(payload, current_user_id, db)


@router.get('', response_model=list[VehicleInputOutput], status_code=status.HTTP_200_OK)
def list_my_vehicles(current_user_id: Annotated[str, Depends(get_current_user_id)], db: Annotated[Session, Depends(get_db)]) -> list[VehicleInputOutput]:
    return service.list_my_vehicles(current_user_id, db)


@router.get('/{vehicle_id}', response_model=VehicleInputOutput, status_code=status.HTTP_200_OK)
def get_vehicle(vehicle_id: Annotated[str, Path(min_length=1, description='The ID of the vehicle to retrieve')], current_user_id: Annotated[str, Depends(get_current_user_id)], db: Annotated[Session, Depends(get_db)]) -> VehicleInputOutput:
    return service.get_vehicle(vehicle_id, current_user_id, db)


@router.patch('/{vehicle_id}', response_model=VehicleInputOutput, status_code=status.HTTP_200_OK)
def update_vehicle(payload: VehicleUpdateInput, vehicle_id: Annotated[str, Path(min_length=1, description='The ID of the vehicle to update')], current_user_id: Annotated[str, Depends(get_current_user_id)], db: Annotated[Session, Depends(get_db)]) -> VehicleInputOutput:
    return service.update_vehicle(payload, vehicle_id, current_user_id, db)


@router.delete('/{vehicle_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(vehicle_id: Annotated[str, Path(min_length=1, description='The ID of the vehicle to delete')], current_user_id: Annotated[str, Depends(get_current_user_id)], db: Annotated[Session, Depends(get_db)]) -> None:
    return service.delete_vehicle(vehicle_id, current_user_id, db)


@router.post('/{vehicle_id}/telemetry', response_model=VehicleInputOutput, status_code=status.HTTP_200_OK)
def record_telemetry(payload: VehicleTelemetrySchema, vehicle_id: Annotated[str, Path(min_length=1, description='The ID of the vehicle')], current_user_id: Annotated[str, Depends(get_current_user_id)], db: Annotated[Session, Depends(get_db)]) -> VehicleInputOutput:
    return service.record_telemetry(payload, vehicle_id, current_user_id, db)


@router.get('/{vehicle_id}/status', response_model=VehicleStatusOutput, status_code=status.HTTP_200_OK)
def get_vehicle_status(vehicle_id: Annotated[str, Path(min_length=1, description='The ID of the vehicle')], current_user_id: Annotated[str, Depends(get_current_user_id)], db: Annotated[Session, Depends(get_db)]) -> VehicleStatusOutput:
    return service.get_vehicle_status(vehicle_id, current_user_id, db)
