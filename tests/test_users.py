from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import jwt
import pytest
from fastapi.testclient import TestClient

from backend.config import JWT_ALGORITHM, JWT_SECRET_KEY
from backend.database import get_db
from backend.dependencies import get_current_user_id
from backend.main import app
from backend.models.conversations import Conversation
from backend.models.users import DriverType, RoadConditions, User, UserPreference
from backend.repositories.conversations import ConversationRepository
from backend.repositories.opportunities import OpportunityRepository
from backend.repositories.trips import TripRepository
from backend.repositories.users import UserRepository
from backend.repositories.vehicles import VehicleRepository
from backend.security import (
    _hash_password,
    _verify_password,
    create_access_token,
    decode_access_token,
)
from backend.services import users as user_service

client = TestClient(app)
PREFERENCES = {"age_group": "adult", "driver_type": "efficient", "road_conditions": ["mixed"], "tolls": True}
PAYLOAD = {"username": "driver", "email": "driver@example.com", "password": "password123", "preferences": PREFERENCES}


@pytest.fixture
def service(monkeypatch):
    repository = Mock(spec=UserRepository)
    user = User(
        "user-1", "driver", "driver@example.com", datetime.now(UTC),
        UserPreference("user-1", "adult", DriverType.EFFICIENT, [RoadConditions.MIXED]), [], [],
    )
    repository.get_user_by_id.return_value = user
    repository.get_user_by_email.return_value = None
    repository.get_user_by_username.return_value = None
    repository.get_password_hash_by_email.return_value = _hash_password("password123")
    repository.create_user.side_effect = lambda created, credentials: created
    repository.update_partial_user.side_effect = lambda updated, fields: updated
    service = SimpleNamespace(
        repository=repository,
        trip_repository=Mock(spec=TripRepository),
        vehicle_repository=Mock(spec=VehicleRepository),
        opportunity_repository=Mock(spec=OpportunityRepository),
        conversation_repository=Mock(spec=ConversationRepository),
    )
    service.conversation_repository.load_user_conversations.return_value = []
    monkeypatch.setattr(user_service, "SqlUserRepository", lambda db: service.repository)
    monkeypatch.setattr(user_service, "SqlTripRepository", lambda db: service.trip_repository)
    monkeypatch.setattr(user_service, "SqlVehicleRepository", lambda db: service.vehicle_repository)
    monkeypatch.setattr(user_service, "SqlOpportunityRepository", lambda db: service.opportunity_repository)
    monkeypatch.setattr(user_service, "SqlConversationRepository", lambda db: service.conversation_repository)
    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    app.dependency_overrides[get_db] = lambda: object()
    yield service
    app.dependency_overrides.clear()


def test_registration_keeps_response_and_password_hash(service):
    response = client.post("/users/register", json=PAYLOAD)
    assert response.status_code == 201
    assert response.json()["preferences"] == PREFERENCES
    assert "password" not in response.json()
    user, credentials = service.repository.create_user.call_args.args
    assert user.user_id == credentials.user_id
    assert credentials.password_hash == _hash_password(PAYLOAD["password"])


def test_registration_rejects_duplicate_username_and_invalid_preferences(service):
    service.repository.get_user_by_username.return_value = service.repository.get_user_by_id.return_value
    assert client.post("/users/register", json=PAYLOAD).status_code == 409
    service.repository.get_user_by_username.return_value = None
    assert client.post("/users/register", json={**PAYLOAD, "preferences": {}}).status_code == 422
    service.repository.create_user.assert_not_called()


def test_login_returns_token_and_rejects_wrong_password(service):
    service.repository.get_user_by_email.return_value = service.repository.get_user_by_id.return_value
    response = client.post("/users/login", json={"email": PAYLOAD["email"], "password": PAYLOAD["password"]})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert decode_access_token(response.json()["access_token"]) == "user-1"
    response = client.post("/users/login", json={"email": PAYLOAD["email"], "password": "wrong-password"})
    assert response.status_code == 401


def test_profile_and_preferences_use_injected_repository(service):
    assert client.get("/users/me").json()["user_id"] == "user-1"
    assert client.patch("/users/me", json={}).status_code == 200
    service.repository.update_partial_user.assert_not_called()
    assert client.patch("/users/me", json={"username": "updated"}).status_code == 200
    assert service.repository.update_partial_user.call_args.args[1] == {"username": "updated"}
    assert client.patch("/users/me/preferences", json={"preferences": PREFERENCES}).status_code == 200
    assert "user_preferences_json" in service.repository.update_partial_user.call_args.args[1]


def test_password_change_and_reset(service):
    response = client.patch("/users/me/password", json={"current_password": "wrong-password", "new_password": "new-password"})
    assert response.status_code == 401
    service.repository.update_partial_user.assert_not_called()
    response = client.patch("/users/me/password", json={"current_password": "password123", "new_password": "new-password"})
    assert response.status_code == 200
    assert service.repository.update_partial_user.call_args.args[1] == {"password_hash": _hash_password("new-password")}
    assert client.patch("/users/me/password/reset", json={"new_password": "reset-password"}).status_code == 200
    assert service.repository.update_partial_user.call_args.args[1] == {"password_hash": _hash_password("reset-password")}


def test_delete_profile_cleans_up_related_data(service):
    service.conversation_repository.load_user_conversations.return_value = [
        Conversation("conversation-1", "user-1", "Trip", datetime.now(UTC), [])
    ]
    response = client.delete("/users/me")
    assert response.status_code == 200
    service.trip_repository.delete_user_trips.assert_called_once_with("user-1")
    service.vehicle_repository.delete_user_vehicles.assert_called_once_with("user-1")
    service.opportunity_repository.delete_user_opportunities.assert_called_once_with("user-1")
    service.conversation_repository.delete_user_conversation.assert_called_once_with("user-1", "conversation-1")
    service.repository.delete_user.assert_called_once_with("user-1")


def test_profile_not_found(service):
    service.repository.get_user_by_id.return_value = None
    assert client.get("/users/me").status_code == 404
    assert client.delete("/users/me").status_code == 404
    service.repository.delete_user.assert_not_called()


def test_password_and_token_helpers():
    assert _verify_password("password123", _hash_password("password123"))
    assert not _verify_password("wrong", _hash_password("password123"))
    assert decode_access_token(create_access_token("user-1")) == "user-1"


@pytest.mark.parametrize("payload", [
    {"sub": "user-1", "exp": datetime.now(UTC) - timedelta(minutes=1)},
    {"sub": "", "exp": datetime.now(UTC) + timedelta(minutes=1)},
    {"exp": datetime.now(UTC) + timedelta(minutes=1)},
])
def test_invalid_tokens_are_rejected(service, payload):
    app.dependency_overrides.pop(get_current_user_id)
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"