from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EngineType(Enum):
    """
    Different types of engines
    """
    INTERNAL_COMBUSTION = "internal_combustion"
    ELECTRIC = "electric"





@dataclass
class VehicleTelemetry:
    vehicle_id: str
    current_fuel: float
    avg_consumption: float
    service_due_km: float
    service_due_date: datetime | None = None

    def __post_init__(self):
        if self.current_fuel < 0:
            raise ValueError("Current fuel cannot be negative")

        if self.avg_consumption < 0 or self.avg_consumption > 99.9:
            raise ValueError("Average consumption must be between 0 and 99.9")

        if self.service_due_km < 0:
            raise ValueError("Service due kilometers cannot be negative")


@dataclass
class Vehicle:
    """
    Represents a vehicle entity from the db
    """
    owner_id: str
    vehicle_id: str
    vehicle_nickname: str
    engine_type: EngineType
    total_capacity: float
    telemetry: VehicleTelemetry

    def __post_init__(self):
        if self.total_capacity < 0 or self.total_capacity > 10000:
            raise ValueError("Total capacity must be between 0 and 10000")

        self.total_capacity = float(self.total_capacity)
