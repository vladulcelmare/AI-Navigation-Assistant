from __future__ import annotations
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from backend.models.trips import Location, Trip, Route
from backend.repositories.opportunities import OpportunityRepository
from backend.repositories.trips import TripRepository
from backend.repositories.users import UserRepository
from backend.repositories.vehicles import VehicleRepository

class RoutingService(Protocol):
    async def get_routes(self, origin: Location, destination: Location) -> list[Route]:
        """
        Get a list of possible routes from the origin to the destination
        """




class OpportunityRanker(Protocol):
    def predict(self, preferences: Any, vehicle: Any, opportunities: list[Any]) -> list[tuple[Any, float]]:
        pass


class ResponseGenerator(Protocol):
    def generate_response(self, context: list[dict[str, str]]) -> str:
        pass


@dataclass(frozen=True)
class TripRecommendationResult:
    trip: Trip
    ranked_opportunities: list[tuple[Any, float]]
    response: str

