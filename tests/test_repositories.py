"""
Integration scenario for the SQL repositories.

The scenario creates and reads test data, then removes it safely.
"""

from datetime import UTC, date, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from backend.models.opportunities import Opportunities
from backend.models.users import (
    DriverType,
    RoadConditions,
    User,
    UserCredentials,
    UserPreference,
)
from backend.models.vehicles import (
    EngineType,
    Vehicle,
    VehicleTelemetry,
)
from backend.repositories.conversations import SqlConversationRepository
from backend.repositories.opportunities import (
    SqlOpportunityRepository,
)
from backend.repositories.users import (
    SqlUserRepository,
)
from backend.repositories.vehicles import (
    SqlVehicleRepository,
)


def run_repository_scenario() -> None:
    from backend.database import SessionLocal

    db = SessionLocal()

    user_id = str(uuid4())
    vehicle_id = str(uuid4())

    user = User(
        user_id=user_id,
        username=f"test_user_{user_id[:8]}",
        email=f"{user_id[:8]}@example.com",
        created_at=datetime.now(UTC),
        preferences=UserPreference(
            user_id=user_id,
            age_group="adult",
            driver_type=DriverType.EFFICIENT,
            road_conditions=[RoadConditions.MIXED],
            tolls=True,
        ),
        trip_history=[],
        conversations=[],
    )

    credentials = UserCredentials(
        user_id=user_id,
        password_hash="test_hash",
    )

    vehicle = Vehicle(
        owner_id=user_id,
        vehicle_id=vehicle_id,
        vehicle_nickname="Test vehicle",
        engine_type=EngineType.ELECTRIC,
        total_capacity=75.0,
        telemetry=VehicleTelemetry(
            vehicle_id=vehicle_id,
            current_fuel=80.0,
            avg_consumption=18.5,
            service_due_km=12000.0,
            service_due_date=datetime.now(UTC),
        ),
    )

    opportunity = Opportunities(
        user_id=user_id,
        partner_name="Enel X Charging Station",
        partner_type="charging_station",
        partner_offers={
            "discount_percent": 10,
            "free_minutes": 30,
        },
        partner_criteria={
            "engine_type": "Electric",
            "minimum_battery_percent": 20,
        },
    )

    user_repository = SqlUserRepository(db)
    vehicle_repository = SqlVehicleRepository(db)
    opportunity_repository = SqlOpportunityRepository(db)

    created_user = None
    created_vehicle = None
    created_opportunity = None

    try:
        created_user = user_repository.create_user(
            user,
            credentials,
        )

        print(
            "Created user:",
            created_user.user_id,
        )

        found_user = user_repository.get_user_by_email(
            user.email,
        )

        print(
            "Found user:",
            found_user.email,
        )

        created_vehicle = vehicle_repository.create_vehicle(
            vehicle,
        )

        print(
            "Created vehicle:",
            created_vehicle.vehicle_id,
        )

        owner_vehicles = (
            vehicle_repository.get_vehicle_by_owner_id(
                user_id,
            )
        )

        print(
            "Owner vehicles:",
            len(owner_vehicles),
        )

        created_opportunity = (
            opportunity_repository.create_opportunity(
                opportunity,
            )
        )

        print(
            "Created opportunity:",
            created_opportunity.partner_name,
        )

        user_opportunity = (
            opportunity_repository.get_opportunity_for_user(
                user_id,
                opportunity.partner_name,
            )
        )

        print(
            "User opportunity:",
            user_opportunity.partner_type,
        )

        updated_opportunity = (
            opportunity_repository.update_partial_opportunity(
                opportunity,
                {
                    "partner_name": "Updated Charging Station",
                    "partner_offers": {
                        "discount_percent": 15,
                        "free_minutes": 45,
                    },
                },
            )
        )

        print(
            "Updated opportunity:",
            updated_opportunity.partner_name,
        )

    finally:
        if created_opportunity is not None:
            opportunity_repository.delete_opportunity(
                user_id,
            )

        if created_vehicle is not None:
            vehicle_repository.delete_vehicle(
                vehicle_id,
            )

        if created_user is not None:
            user_repository.delete_user(
                user_id,
            )

        db.close()
        print("Test data deleted")


def test_conversation_repository_creates_conversation():
    session = Mock()
    repository = SqlConversationRepository(session)
    conversation = repository.create_user_conversation("user-1", "Road trip")
    assert conversation.user_id == "user-1"
    assert conversation.title == "Road trip"
    assert conversation.messages == []
    assert session.execute.call_args.args[1]["conversation_id"] == conversation.conversation_id
    session.commit.assert_called_once()


def test_conversation_repository_rolls_back_on_failure():
    session = Mock()
    session.execute.side_effect = RuntimeError("Database unavailable")
    repository = SqlConversationRepository(session)
    with pytest.raises(RuntimeError, match="Database unavailable"):
        repository.create_user_conversation("user-1", "Road trip")
    session.rollback.assert_called_once()
    session.commit.assert_not_called()


def test_conversation_lookup_is_scoped_to_owner():
    session = Mock()
    session.execute.return_value.mappings.return_value.first.return_value = None
    repository = SqlConversationRepository(session)
    assert repository.load_user_conversation("user-1", "conversation-1") is None
    query, parameters = session.execute.call_args.args
    assert "user_unique_id = :user_id" in str(query)
    assert parameters == {"user_id": "user-1", "conversation_id": "conversation-1"}


def test_vehicle_row_mapping_preserves_nickname_and_telemetry():
    vehicle = SqlVehicleRepository._row_to_vehicle({
        "user_unique_id": "user-1",
        "vehicle_id": "vehicle-1",
        "vehicle_nickname": "Daily driver",
        "engine_type": "Electric",
        "total_capacity": 75,
        "current_fuel": 50,
        "avg_consumption": 18,
        "service_due_km": 10000,
        "service_due_date": date(2027, 1, 1),
    })
    assert vehicle.vehicle_nickname == "Daily driver"
    assert vehicle.engine_type is EngineType.ELECTRIC
    assert vehicle.telemetry.vehicle_id == vehicle.vehicle_id
    assert vehicle.telemetry.current_fuel == 50
    assert vehicle.telemetry.service_due_date.date() == date(2027, 1, 1)


def test_preferences_round_trip():
    preferences = UserPreference("user-1", "adult", DriverType.EFFICIENT, [RoadConditions.MIXED])
    encoded = SqlUserRepository._serialize_preferences(preferences)
    assert SqlUserRepository._deserialize_preferences(encoded, "user-1") == preferences


if __name__ == "__main__":
    run_repository_scenario()
