from datetime import UTC, date, datetime, time
import json
from typing import Protocol, override
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.vehicles import EngineType, Vehicle, VehicleTelemetry


class VehicleRepository(Protocol):
    def get_vehicle_by_id(self, vehicle_id: str) -> Vehicle | None:
        """
        Fetch a vehicle by its ID
        """

    def get_vehicle_by_owner_id(self, owner_id: str) -> list[Vehicle]:
        """
        Fetch all vehicles owned by a specific user
        """

    def create_vehicle(self, vehicle: Vehicle) -> Vehicle:
        """
        Create a new vehicle
        """

    def update_vehicle(self, vehicle: Vehicle) -> Vehicle:
        """
        Update an existing vehicle
        """

    def update_partial_vehicle(self, vehicle: Vehicle, fields: dict) -> Vehicle:
        """
        Updates specific fields of an existing vehicle
        """

    def delete_vehicle(self, vehicle_id: str) -> None:
        """
        Deletes an existing vehicle
        """

    def delete_user_vehicles(self, user_id: str) -> None:
        """
        Delete all vehicles owned by a specific user
        """

    def update_telemetry(self, vehicle_id: str, telemetry: VehicleTelemetry,) -> Vehicle:
        """
        Update the telemetry data for a vehicle
        """


ENGINE_TYPE_TO_DB = {
    EngineType.INTERNAL_COMBUSTION: "Internal_Combustion",
    EngineType.ELECTRIC: "Electric",
}

DB_TO_ENGINE_TYPE = {
    "Internal_Combustion": EngineType.INTERNAL_COMBUSTION,
    "Electric": EngineType.ELECTRIC,
}


class SqlVehicleRepository(VehicleRepository):
    def __init__(self, db: Session):
        """
        Store sqlalchemy session
        """
        self.db = db

    @staticmethod
    def _to_datetime(value: date | datetime | None) -> datetime:
        """
        Normalise into datetime
        """
        if value is None:
            return datetime.combine(date.min, time.min)

        if isinstance(value, datetime):
            return value

        return datetime.combine(value, datetime.min.time())

    @classmethod
    def _row_to_vehicle(cls, row) -> Vehicle:
        """
        Transform a SQL row and its telemetry into a Vehicle entity.
        """
        engine_type_value = row["engine_type"]

        if engine_type_value not in DB_TO_ENGINE_TYPE:
            raise ValueError(
                f"Unsupported engine type: {engine_type_value}"
            )

        telemetry = VehicleTelemetry(
            vehicle_id=row["vehicle_id"],
            current_fuel=float(row["current_fuel"] or 0),
            avg_consumption=float(row["avg_consumption"] or 0),
            service_due_km=float(row["service_due_km"] or 0),
            service_due_date=cls._to_datetime(
                row["service_due_date"]
            ),
        )

        return Vehicle(
            owner_id=row["user_unique_id"],
            vehicle_id=row["vehicle_id"],
            vehicle_nickname=row["vehicle_nickname"],
            engine_type=DB_TO_ENGINE_TYPE[engine_type_value],
            total_capacity=float(row["total_capacity"]),
            telemetry=telemetry,
        )

    def _get_vehicle_row(self, vehicle_id: str, lock: bool = False):
        """
        Get vehicle id and telemetry using left join
        """
        query = text(f"""
            SELECT
                v.user_unique_id,
                v.vehicle_id,
                v.vehicle_nickname,
                v.engine_type,
                v.total_capacity,
                t.current_fuel,
                t.avg_consumption,
                t.service_due_km,
                t.service_due_date
            FROM Users_Vehicles.vehicle AS v {"WITH (UPDLOCK, HOLDLOCK)" if lock else ""}
            LEFT JOIN Users_Vehicles.vehicle_telemetry AS t
                ON v.vehicle_id = t.vehicle_id
            WHERE v.vehicle_id = :vehicle_id
        """)

        return self.db.execute(
            query,
            {"vehicle_id": vehicle_id},
        ).mappings().first()

    @override
    def get_vehicle_by_id(self, vehicle_id: str, lock: bool = False) -> Vehicle | None:
        """
        Search for a vehicle by ID
        """
        row = self._get_vehicle_row(vehicle_id, lock)

        if row is None:
            return None

        return self._row_to_vehicle(row)

    @override
    def get_vehicle_by_owner_id(self, owner_id: str) -> list[Vehicle]:
        """
        Fetch all vehicles associated with an user
        """
        query = text("""
            SELECT
                v.user_unique_id,
                v.vehicle_id,
                v.vehicle_nickname,
                v.engine_type,
                v.total_capacity,
                t.current_fuel,
                t.avg_consumption,
                t.service_due_km,
                t.service_due_date
            FROM Users_Vehicles.vehicle AS v
            LEFT JOIN Users_Vehicles.vehicle_telemetry AS t
                ON v.vehicle_id = t.vehicle_id
            WHERE v.user_unique_id = :owner_id
        """)

        rows = self.db.execute(
            query,
            {"owner_id": owner_id},
        ).mappings().all()

        return [self._row_to_vehicle(row) for row in rows]

    @override
    def update_telemetry(self, vehicle_id: str, telemetry: VehicleTelemetry) -> Vehicle:
        """
        Update the telemetry data for a vehicle
        """

        service_due_date = telemetry.service_due_date

        if isinstance(service_due_date, datetime):
            service_due_date = service_due_date.date()

        query = text("""
            UPDATE Users_Vehicles.vehicle_telemetry
            SET
                current_fuel = :current_fuel,
                avg_consumption = :avg_consumption,
                service_due_km = :service_due_km,
                service_due_date = :service_due_date
            WHERE vehicle_id = :vehicle_id
        """)

        try:
            result = self.db.execute(
                query,
                {
                    "vehicle_id": vehicle_id,
                    "current_fuel": telemetry.current_fuel,
                    "avg_consumption": telemetry.avg_consumption,
                    "service_due_km": telemetry.service_due_km,
                    "service_due_date": service_due_date,
                },
            )

            if result.rowcount == 0:
                self.db.rollback()
                raise ValueError(
                    "Vehicle telemetry was not found"
                )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return self.get_vehicle_by_id(vehicle_id)

    @override
    def create_vehicle(self, vehicle: Vehicle) -> Vehicle:
        """
        Create a new vehicle
        """
        engine_type = ENGINE_TYPE_TO_DB.get(
            vehicle.engine_type
        )

        if engine_type is None:
            raise ValueError(
                f"Unsupported engine type: {vehicle.engine_type}"
            )

        insert_vehicle = text("""
            INSERT INTO Users_Vehicles.vehicle
            (
                user_unique_id,
                vehicle_nickname,
                engine_type,
                total_capacity,
                vehicle_id
            )
            VALUES
            (
                :owner_id,
                :vehicle_nickname,
                :engine_type,
                :total_capacity,
                :vehicle_id
            )
        """)

        insert_telemetry = text("""
            INSERT INTO Users_Vehicles.vehicle_telemetry
            (
                vehicle_id,
                current_fuel,
                avg_consumption,
                service_due_km,
                service_due_date
            )
            VALUES
            (
                :vehicle_id,
                :current_fuel,
                :avg_consumption,
                :service_due_km,
                :service_due_date
            )
        """)

        try:
            self.db.execute(
                insert_vehicle,
                {
                    "owner_id": vehicle.owner_id,
                    "vehicle_nickname": vehicle.vehicle_nickname,
                    "engine_type": engine_type,
                    "total_capacity": vehicle.total_capacity,
                    "vehicle_id": vehicle.vehicle_id,
                },
            )

            self.db.execute(
                insert_telemetry,
                {
                    "vehicle_id": vehicle.vehicle_id,
                    "current_fuel": vehicle.telemetry.current_fuel,
                    "avg_consumption": (
                        vehicle.telemetry.avg_consumption
                    ),
                    "service_due_km": (
                        vehicle.telemetry.service_due_km
                    ),
                    "service_due_date": (
                        vehicle.telemetry.service_due_date.date()
                    ),
                },
            )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return self.get_vehicle_by_id(vehicle.vehicle_id)

    @override
    def update_vehicle(self, vehicle: Vehicle) -> Vehicle:
        """
        Update a vehicle
        """
        engine_type = ENGINE_TYPE_TO_DB.get(
            vehicle.engine_type
        )

        if engine_type is None:
            raise ValueError(
                f"Unsupported engine type: {vehicle.engine_type}"
            )

        update_vehicle = text("""
            UPDATE Users_Vehicles.vehicle
            SET
                user_unique_id = :owner_id,
                vehicle_nickname = :vehicle_nickname,
                engine_type = :engine_type,
                total_capacity = :total_capacity
            WHERE vehicle_id = :vehicle_id
        """)

        update_telemetry = text("""
            UPDATE Users_Vehicles.vehicle_telemetry
            SET
                current_fuel = :current_fuel,
                avg_consumption = :avg_consumption,
                service_due_km = :service_due_km,
                service_due_date = :service_due_date
            WHERE vehicle_id = :vehicle_id
        """)

        try:
            result = self.db.execute(
                update_vehicle,
                {
                    "owner_id": vehicle.owner_id,
                    "vehicle_nickname": vehicle.vehicle_nickname,
                    "engine_type": engine_type,
                    "total_capacity": vehicle.total_capacity,
                    "vehicle_id": vehicle.vehicle_id,
                },
            )

            if result.rowcount == 0:
                self.db.rollback()
                raise ValueError("Vehicle was not found")

            self.db.execute(
                update_telemetry,
                {
                    "current_fuel": vehicle.telemetry.current_fuel,
                    "avg_consumption": (
                        vehicle.telemetry.avg_consumption
                    ),
                    "service_due_km": (
                        vehicle.telemetry.service_due_km
                    ),
                    "service_due_date": (
                        vehicle.telemetry.service_due_date.date()
                    ),
                    "vehicle_id": vehicle.vehicle_id,
                },
            )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return self.get_vehicle_by_id(vehicle.vehicle_id)

    @override
    def update_partial_vehicle(self, vehicle: Vehicle, fields: dict) -> Vehicle:
        """
        Update only the allowed vehicle fields in the repository
        """
        allowed_fields = {
            "engine_type",
            "total_capacity",
        }

        invalid_fields = set(fields) - allowed_fields

        if invalid_fields:
            raise ValueError(
                f"Unsupported fields: {invalid_fields}"
            )

        if not fields:
            return self.get_vehicle_by_id(vehicle.vehicle_id)

        values = dict(fields)

        if "engine_type" in values:
            values["engine_type"] = ENGINE_TYPE_TO_DB.get(
                values["engine_type"]
            )

        set_clause = ", ".join(
            f"{field} = :{field}"
            for field in values
        )

        values["vehicle_id"] = vehicle.vehicle_id

        query = text(f"""
            UPDATE Users_Vehicles.vehicle
            SET {set_clause}
            WHERE vehicle_id = :vehicle_id
        """)

        try:
            result = self.db.execute(query, values)

            if result.rowcount == 0:
                self.db.rollback()
                raise ValueError("Vehicle was not found")

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return self.get_vehicle_by_id(vehicle.vehicle_id)

    @override
    def delete_vehicle(self, vehicle_id: str) -> None:
        """
        Delete a vehicle
        """
        try:
            self.db.execute(
                text("""
                    DELETE FROM Users_Vehicles.vehicle_telemetry
                    WHERE vehicle_id = :vehicle_id
                """),
                {"vehicle_id": vehicle_id},
            )

            result = self.db.execute(
                text("""
                    DELETE FROM Users_Vehicles.vehicle
                    WHERE vehicle_id = :vehicle_id
                """),
                {"vehicle_id": vehicle_id},
            )

            if result.rowcount == 0:
                self.db.rollback()
                raise ValueError("Vehicle was not found")

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

    @override
    def delete_user_vehicles(self, user_id: str) -> None:
        """
        Delete the vehicles of an user
        """
        try:
            self.db.execute(
                text("""
                    DELETE FROM Users_Vehicles.vehicle_telemetry
                    WHERE vehicle_id IN (
                        SELECT vehicle_id
                        FROM Users_Vehicles.vehicle
                        WHERE user_unique_id = :user_id
                    )
                """),
                {"user_id": user_id},
            )

            self.db.execute(
                text("""
                    DELETE FROM Users_Vehicles.vehicle
                    WHERE user_unique_id = :user_id
                """),
                {"user_id": user_id},
            )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise
