from datetime import datetime
from typing import Annotated, Any
from pydantic import BaseModel, Field, model_validator

from backend.models.trips import TripStatus


# Coordinates are validated here before they reach the routing service
class LocationSchema(BaseModel):
    latitude: Annotated[float, Field(ge=-90, le=90)]
    longitude: Annotated[float, Field(ge=-180, le=180)]


class TripCreateInput(BaseModel):
    vehicle_id: Annotated[str, Field(min_length=1, max_length=64)]
    origin: LocationSchema
    destination: LocationSchema

    @model_validator(mode="after")
    def validate_different_locations(self) -> "TripCreateInput":

        if self.origin == self.destination:
            raise ValueError("Origin and destination must be different")
        
        return self

class RouteOutput(BaseModel):
    distance_km: float
    duration_minutes: float
    geometry: list[LocationSchema]

class TripStatusChange(BaseModel):
    status: TripStatus

class TripOutput(BaseModel):
    trip_id: str
    user_id: str
    vehicle_id: str
    created_at: datetime
    origin: LocationSchema
    destination: LocationSchema
    route: RouteOutput
    route_options: list[RouteOutput] = Field(default_factory=list)
    cost_per_km: float
    status: TripStatus
    route_origin: LocationSchema | None = None


class TripRecalculateInput(BaseModel):
    current_location: LocationSchema

class TripRecalculateOutput(BaseModel):
    trip: TripOutput
    stop_recommendations: dict[str, Any] = Field(default_factory=dict)
    partner_route: dict[str, Any] | None = None

