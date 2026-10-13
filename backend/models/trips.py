from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


@dataclass
class Distance:
    distance_km: float
    distance_min: float

@dataclass
class Location:
    latitude: float
    longitude: float

    def __post_init__(self):
        if not (-90 <= self.latitude <= 90):
            raise ValueError("Latitude must be between -90 and 90")

        if not (-180 <= self.longitude <= 180):
            raise ValueError("Longitude must be between -180 and 180")

@dataclass
class UserTripHistory:
    user_id: str
    vehicle_id: str
    trip_id: str
    timestamp: datetime
    start_location: Location
    end_location: Location
    cost_per_km: float
    distance: Distance


class TripStatus(StrEnum):
    """
    Different status types for a trip
    """
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class Route:
    distance_km: float
    duration_minutes: float
    geometry: list[Location]

@dataclass(frozen=True)
class RouteCandidate:
    """Raw route values needed by the feature-building stage."""

    distance_km: float
    duration_min: float
    has_tolls: bool
    geometry: Any
    properties: dict[str, Any]

@dataclass
class Trip:
    """
    Represents a trip entity from the db
    """
    user_id: str
    vehicle_id: str
    trip_id: str
    created_at: datetime
    origin: Location
    destination: Location
    route: Route
    cost_per_km: float
    status: TripStatus = TripStatus.PLANNED
    route_options: list[Route] | None = None
    route_origin: Location | None = None
