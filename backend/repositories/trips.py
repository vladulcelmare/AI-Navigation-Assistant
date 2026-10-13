import json
from datetime import date, datetime
from typing import Protocol, override
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.trips import Location, Route, Trip, TripStatus


class TripRepository(Protocol):
    def has_active_trip_for_vehicle(self, vehicle_id: str) -> bool:
        """
        Check if there is an active trip
        """

    def delete_user_trips(self, user_id: str) -> None:
        """
        Delete all trips associated with the given user ID
        """

    def create_trip(self, trip: Trip) -> Trip:
        """
        Create a new trip and return the created trip object
        """

    def get_trips_by_user_id(self, user_id: str) -> list[Trip]:
        """
        Retrieve all trips associated with the given user ID
        """

    def get_trip_by_id(self, trip_id: str) -> Trip | None:
        """
        Retrieve a trip by its ID, or return None if not found
        """

    def update_trip(self, trip: Trip) -> Trip:
        """
        Update an existing trip and return the updated trip object
        """


class SqlTripRepository(TripRepository):
    """Persist trips and their route candidates in SQL Server."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _location_to_text(location: Location) -> str:
        return f"{location.latitude:.6f},{location.longitude:.6f}"

    @staticmethod
    def _text_to_location(value: str) -> Location:
        latitude, longitude = value.split(",", maxsplit=1)
        return Location(float(latitude), float(longitude))

    @staticmethod
    def _serialize_route(route: Route) -> dict:
        return {
            "distance_km": route.distance_km,
            "duration_minutes": route.duration_minutes,
            "geometry": [
                {
                    "latitude": point.latitude,
                    "longitude": point.longitude,
                }
                for point in route.geometry
            ],
        }

    @staticmethod
    def _deserialize_route(route_data: dict) -> Route:
        return Route(
            distance_km=float(route_data["distance_km"]),
            duration_minutes=float(route_data["duration_minutes"]),
            geometry=[
                Location(point["latitude"], point["longitude"])
                for point in route_data["geometry"]
            ],
        )

    @classmethod
    def _row_to_trip(cls, row) -> Trip:
        """Convert a database row into a domain trip."""
        raw_route_json = row["route_json"]
        # Older history rows predate route_json. Preserve those trips by
        # reconstructing a minimal route from the persisted distance fields.
        route_data = json.loads(raw_route_json) if raw_route_json else {}
        geometry = route_data.get("geometry", [])
        route_options = [
            cls._deserialize_route(route)
            for route in route_data.get("routes", [])
        ]
        selected_route_data = {
            "distance_km": row["distance_km"],
            "duration_minutes": row["distance_min"],
            "geometry": geometry,
        }
        selected_route = cls._deserialize_route(selected_route_data)
        return Trip(
            user_id=row["user_unique_id"],
            vehicle_id=row["vehicle_id"],
            trip_id=row["trip_id"],
            created_at=datetime.combine(
                row["creation_date"], datetime.min.time()
            )
            if isinstance(row["creation_date"], date)
            and not isinstance(row["creation_date"], datetime)
            else row["creation_date"],
            origin=cls._text_to_location(row["initial_location"]),
            destination=cls._text_to_location(row["destination"]),
            route=selected_route,
            cost_per_km=float(row["cost_per_km"]),
            status=TripStatus(row["trip_status"] or TripStatus.PLANNED.value),
            route_options=route_options or [selected_route],
            route_origin=Location(**route_data["route_origin"]) if route_data.get("route_origin") else None,
        )

    @override
    def has_active_trip_for_vehicle(self, vehicle_id: str) -> bool:
        """Return whether the vehicle has a planned or active trip."""
        row = self.db.execute(
            text("""
                SELECT TOP 1 trip_id
                FROM Users_Trips.history
                WHERE vehicle_id = :vehicle_id
                  AND trip_status IN ('PLANNED', 'IN_PROGRESS')
            """),
            {"vehicle_id": vehicle_id},
        ).first()
        return row is not None

    @override
    def delete_user_trips(self, user_id: str) -> None:
        """Delete all trips belonging to a user."""
        try:
            self.db.execute(
                text("""
                    DELETE FROM Users_Trips.history
                    WHERE user_unique_id = :user_id
                """),
                {"user_id": user_id},
            )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

    @override
    def create_trip(self, trip: Trip, commit: bool = True) -> Trip:
        """Insert a trip and reload it from the database."""
        route_json = json.dumps(
            {
                "geometry": self._serialize_route(trip.route)["geometry"],
                "route_origin": vars(trip.route_origin or trip.origin),
                "routes": [
                    self._serialize_route(route)
                    for route in (trip.route_options or [trip.route])
                ],
            }
        )
        try:
            self.db.execute(
                text("""
                    INSERT INTO Users_Trips.history
                    (
                        user_unique_id, vehicle_id, trip_id,
                        creation_date, initial_location, destination,
                        cost_per_km, distance_km, distance_min,
                        route_json, trip_status
                    )
                    VALUES
                    (
                        :user_id, :vehicle_id, :trip_id,
                        :creation_date, :origin, :destination,
                        :cost_per_km, :distance_km, :distance_min,
                        :route_json, :trip_status
                    )
                """),
                {
                    "user_id": trip.user_id,
                    "vehicle_id": trip.vehicle_id,
                    "trip_id": trip.trip_id,
                    "creation_date": trip.created_at.date(),
                    "origin": self._location_to_text(trip.origin),
                    "destination": self._location_to_text(trip.destination),
                    "cost_per_km": trip.cost_per_km,
                    "distance_km": trip.route.distance_km,
                    "distance_min": trip.route.duration_minutes,
                    "route_json": route_json,
                    "trip_status": trip.status.value,
                },
            )
            if commit:
                self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        created_trip = self.get_trip_by_id(trip.trip_id)
        if created_trip is None:
            raise RuntimeError("Trip was not found after creation")
        return created_trip

    @override
    def get_trips_by_user_id(self, user_id: str) -> list[Trip]:
        """Return all trips belonging to a user, newest first."""
        rows = self.db.execute(
            text("""
                SELECT user_unique_id, vehicle_id, trip_id,
                       creation_date, initial_location, destination,
                       cost_per_km, distance_km, distance_min,
                       route_json, trip_status
                FROM Users_Trips.history
                WHERE user_unique_id = :user_id
                ORDER BY creation_date DESC, trip_id DESC
            """),
            {"user_id": user_id},
        ).mappings().all()
        return [self._row_to_trip(row) for row in rows]

    @override
    def get_trip_by_id(self, trip_id: str) -> Trip | None:
        """Return a trip by ID, or None when it does not exist."""
        row = self.db.execute(
            text("""
                SELECT user_unique_id, vehicle_id, trip_id,
                       creation_date, initial_location, destination,
                       cost_per_km, distance_km, distance_min,
                       route_json, trip_status
                FROM Users_Trips.history
                WHERE trip_id = :trip_id
            """),
            {"trip_id": trip_id},
        ).mappings().first()
        return None if row is None else self._row_to_trip(row)


    @override
    def update_trip(self, trip, commit: bool = True) -> Trip:
        try:
            route_json = json.dumps({
                "geometry": self._serialize_route(trip.route)["geometry"],
                "route_origin": vars(trip.route_origin or trip.origin),
                "routes": [self._serialize_route(route) for route in (trip.route_options or [trip.route])],
            })
            self.db.execute(
                text("""
                    UPDATE Users_Trips.history
                    SET trip_status = :trip_status,
                        route_json = :route_json,
                        distance_km = :distance_km,
                        distance_min = :distance_min,
                        cost_per_km = :cost_per_km,
                        destination = :destination
                    WHERE trip_id = :trip_id
                """),
                {
                    "trip_status": trip.status.value,
                    "route_json": route_json,
                    "distance_km": trip.route.distance_km,
                    "distance_min": trip.route.duration_minutes,
                    "cost_per_km": trip.cost_per_km,
                    "trip_id": trip.trip_id,
                    "destination": self._location_to_text(trip.destination),
                },
            )
            if commit:
                self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        updated_trip = self.get_trip_by_id(trip.trip_id)
        if updated_trip is None:
            raise RuntimeError("Trip was not found after update")
        return updated_trip
