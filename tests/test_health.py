import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from backend.main import app
from backend.routers import health as health_router

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_health_endpoint_reports_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health_router, "test_connection", lambda: 1)

    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_database_health_endpoint_handles_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_connection() -> int:
        raise SQLAlchemyError("Database unavailable")

    monkeypatch.setattr(health_router, "test_connection", failing_connection)

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unavailable"}
