"""Small Geoapify adapter used by the route-ingestion pipeline.

This module deliberately does not contain ranking logic.  It only turns a
place name into coordinates and fetches the candidate routes returned by
Geoapify.  Feature extraction and XGBoost input preparation belong to later
pipeline stages.
"""

from __future__ import annotations
from dataclasses import dataclass
import httpx

from backend import config
from backend.services.errors import RouteServiceError, GeoapifyError
from backend.models.trips import Location, Route, RouteCandidate
from backend.services.trips import RoutingService


@dataclass(frozen=True)
class Coordinates:
    latitude: float
    longitude: float

    @property
    def waypoint(self) -> str:
        # Geoapify expects latitude,longitude in the waypoints parameter
        # No spaces between latitude and longitude
        return f"{self.latitude},{self.longitude}"



class GeoapifyClient(RoutingService):
    GEOCODE_URL = config.GEOAPIFY_GEOCODE_URL
    ROUTING_URL = config.GEOAPIFY_ROUTING_URL
    PLACES_URL = config.GEOAPIFY_PLACES_URL

    def __init__(self, api_key: str | None = None, timeout: float = 30.0) -> None:
        self.api_key = api_key or config.GEOAPIFY_API_KEY
        if not self.api_key:
            raise RouteServiceError(
                "GEOAPIFY_API_KEY is not configured"
            )
        
        self.timeout = timeout


    async def count_pois_near_route(
        self, geometry: dict,
        categories: str = (
            "catering,accommodation,"
            "service.vehicle.fuel,"
            "service.vehicle.charging_station"
        ),
        radius_m: int = 5000,
        max_samples: int = 5) -> int:

        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates", [])

        if geometry_type == "LineString":
            points = coordinates
            
        elif geometry_type == "MultiLineString":
            points = [
                point
                for line in coordinates
                for point in line
            ]
        else:
            raise ValueError(
                f"Unsupported geometry type: {geometry_type}"
            )

        if not points:
            return 0

        step = max(1, len(points) // max_samples)
        sampled_points = points[::step]

        if sampled_points[-1] != points[-1]:
            sampled_points.append(points[-1])

        place_ids = set()

        async with httpx.AsyncClient(
            timeout=self.timeout
        ) as client:
            for longitude, latitude in sampled_points:
                params = {
                    "categories": categories,
                    "filter": (
                        f"circle:{longitude},"
                        f"{latitude},{radius_m}"
                    ),
                    "limit": 500,
                    "apiKey": self.api_key,
                }

                response = await client.get(
                    self.PLACES_URL,
                    params=params,
                )

                self._raise_for_status(response)

                for feature in response.json().get(
                    "features",
                    [],
                ):
                    properties = feature.get(
                        "properties",
                        {},
                    )

                    place_id = properties.get(
                        "place_id"
                    )

                    if place_id:
                        place_ids.add(place_id)

        return len(place_ids)

    async def find_stations_near_point(self, latitude: float, longitude: float, *, electric: bool,
        radius_m: int = 5000, limit: int = 5) -> list[dict]:
        category = ("service.vehicle.charging_station"
            if electric else "service.vehicle.fuel"
        )

        params = {
            "categories": category,
            "filter": f"circle:{longitude},{latitude},{radius_m}",
            "limit": limit,
            "apiKey": self.api_key,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.PLACES_URL, params=params)

        self._raise_for_status(response)

        stations = []
        for feature in response.json().get("features", []):
            properties = feature.get("properties", {})
            geometry = feature.get("geometry", {})
            coordinates = geometry.get("coordinates", [])

            if len(coordinates) < 2:
                continue

            stations.append({
                "place_id": properties.get("place_id"),
                "name": properties.get("name") or "Unknown station",
                "address": properties.get("formatted"),
                "location": {
                    "longitude": coordinates[0],
                    "latitude": coordinates[1],
                },
                "type": "charging" if electric else "refueling",
            })

        return stations
        

    async def geocode(self, place: str) -> Coordinates:
        if not place or not place.strip():
            raise ValueError("place must not be empty")

        params = {"text": place.strip(), "limit": 1, "format": "json", "apiKey": self.api_key}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.GEOCODE_URL, params=params)
        self._raise_for_status(response)

        results = response.json().get("results", [])
        if not results:
            raise GeoapifyError(f"No coordinates found for {place!r}")

        result = results[0]
        try:
            return Coordinates(latitude=float(result["lat"]), longitude=float(result["lon"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise GeoapifyError(f"Invalid geocoding response for {place!r}") from exc

    async def get_routes(self, origin: Location, destination: Location) -> list[Route]:
        candidates = await self.get_route_candidates(
            Coordinates(origin.latitude, origin.longitude),
            Coordinates(destination.latitude, destination.longitude),
        )

        return [self._to_route(candidate) for candidate in candidates]


    async def get_route_candidates(self, origin: Coordinates, destination: Coordinates, *,
        via: Coordinates | None = None, alternatives: int = 3, avoid_tolls: bool = False,
    ) -> list[RouteCandidate]:

        if not 1 <= alternatives <= 3:
            raise ValueError("alternatives must be between 1 and 3")

        strategies = ["balanced", "short", "less_maneuvers"][:alternatives]
        waypoints = [origin.waypoint]

        if via is not None:
            waypoints.append(via.waypoint)

        waypoints.append(destination.waypoint)
        features = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for strategy in strategies:
                params = {
                    "waypoints": "|".join(waypoints),
                    "mode": "drive",
                    "type": strategy,
                    "format": "geojson",
                    "details": "route_details",
                    "traffic": "approximated",
                    "lang": "en",
                    "apiKey": self.api_key,
                }

                if avoid_tolls:
                    params["avoid"] = "tolls"

                response = await client.get(self.ROUTING_URL,params=params)
                self._raise_for_status(response)
                features.extend(response.json().get("features",[]))

        routes = []

        for feature in features:
            properties = feature.get("properties") or {}
            distance = properties.get("distance")
            duration = properties.get("time")

            if distance is None or duration is None:
                continue

            routes.append(
                RouteCandidate(
                    distance_km=float(distance) / 1000,
                    duration_min=float(duration) / 60,
                    has_tolls=bool(
                        properties.get("toll", False)
                    ),
                    geometry=feature.get("geometry"),
                    properties=properties,
                )
            )

        if not routes:
            raise GeoapifyError(
                "Geoapify returned no usable routes"
            )

        return routes
    
    @staticmethod
    def _to_route(candidate: RouteCandidate) -> Route:
        geometry = candidate.geometry or {}
        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates", [])

        if geometry_type == "LineString":
            points = coordinates
        elif geometry_type == "MultiLineString":
            points = [point for line in coordinates for point in line]
        else:
            raise GeoapifyError(
                f"Unsupported route geometry type: {geometry_type}"
            )

        if len(points) < 2:
            raise GeoapifyError("Geoapify route has insufficient geometry")

        return Route(
            distance_km=round(candidate.distance_km, 2),
            duration_minutes=round(candidate.duration_min, 2),
            geometry=[
                Location(latitude=latitude, longitude=longitude)
                for longitude, latitude in points
            ],
        )

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.is_success:
            return
        detail = response.text[:500]
        raise GeoapifyError(f"Geoapify request failed ({response.status_code}): {detail}")