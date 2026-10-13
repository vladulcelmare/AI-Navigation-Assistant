from datetime import datetime
from typing import Annotated
from pydantic import AwareDatetime, BaseModel, Field
from backend.schemas.trips import LocationSchema

from backend.models.vehicles import EngineType


# Telemetry values received from and returned to vehicle clients
class VehicleTelemetry(BaseModel):
    current_fuel: Annotated[
        float,
        Field(ge=0,le=100,description="The current fuel or battery level"),
    ]

    avg_consumption: Annotated[
        float,
        Field(ge=0,description="The average fuel consumption"),
    ]

    service_due_km: Annotated[
        float,
        Field(ge=0,description="The kilometers remaining until service"),
    ]

    service_due_date: Annotated[
        datetime,
        Field(description="The date of the next service"),
    ]


class VehicleInputOutput(BaseModel):
    vehicle_id: Annotated[str,Field(description="The ID of the vehicle")]

    owner_id: Annotated[str,Field(description="The ID of the vehicle owner")]

    engine_type: Annotated[EngineType, Field(description="The engine type of the vehicle")]

    nickname: Annotated[str, Field(description="The nickname of the vehicle")]
    total_capacity: Annotated[float, Field(description="The total fuel or battery capacity")]

    telemetry: Annotated[VehicleTelemetry, Field(description="The telemetry data of the vehicle")]


class VehicleCreateInput(BaseModel):
    engine_type: Annotated[EngineType, Field(description="The engine type of the vehicle")]
    nickname: Annotated[str, Field(description="The nickname of the vehicle")]
    total_capacity: Annotated[
        float,
        Field(gt=0,le=10000, description="The total fuel or battery capacity")]

    telemetry: Annotated[VehicleTelemetry, Field(description="The initial telemetry data of the vehicle")]


class VehicleUpdateInput(BaseModel):
    # Optional fields make this schema suitable for partial updates
    engine_type: Annotated[
        EngineType | None,
        Field(description="The updated engine type"),
    ] = None
    nickname: Annotated[
        str | None,
        Field(description="The updated nickname of the vehicle"),
    ] = None
    total_capacity: Annotated[
        float | None,
        Field(gt=0, le=10000, description="The updated fuel or battery capacity"),
    ] = None


class VehicleStatusOutput(BaseModel):
    vehicle_id: Annotated[str, Field(description="The ID of the vehicle")]
    nickname: Annotated[str, Field(description="The nickname of the vehicle")]

    current_fuel: Annotated[float, Field(description="The current fuel or battery level")]

    avg_consumption: Annotated[float, Field(description="The average fuel consumption")]

    service_due_km: Annotated[float, Field(description="The kilometers remaining until service")]

    service_due_date: Annotated[datetime, Field(description="The date of the next service")]
