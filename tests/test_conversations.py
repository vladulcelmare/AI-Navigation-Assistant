from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.database import get_db
from backend.dependencies import get_current_user_id
from backend.main import app
from backend.models.conversations import Conversation, Message
from backend.services import conversations as conversation_service

USER_ID = "user-1"
client = TestClient(app)


class ConversationRepositoryStub:
    def __init__(self) -> None:
        self.conversations: dict[str, Conversation] = {}

    def create_user_conversation(self, user_id: str, title: str) -> Conversation:
        conversation = Conversation(
            conversation_id=str(uuid4()),
            user_id=user_id,
            title=title,
            creation_date=datetime.now(UTC),
            messages=[],
        )
        self.conversations[conversation.conversation_id] = conversation
        return conversation

    def load_user_conversation(self, user_id: str, conversation_id: str) -> Conversation | None:
        conversation = self.conversations.get(conversation_id)

        if conversation is None or conversation.user_id != user_id:
            return None

        return conversation

    def load_user_conversations(self, user_id: str) -> list[Conversation]:
        return [
            conversation
            for conversation in self.conversations.values()
            if conversation.user_id == user_id
        ]

    def log_user_message(self, user_id: str, conversation_id: str, message: str, role: str) -> None:
        conversation = self.load_user_conversation(user_id, conversation_id)

        if conversation is None:
            raise ValueError("Conversation was not found for this user")

        conversation.messages.append(
            Message(
                conversation_id=conversation_id,
                message_id=len(conversation.messages) + 1,
                content=message,
                chat_role=role,
            )
        )

    def delete_user_conversation(self, user_id: str, conversation_id: str) -> None:
        if self.load_user_conversation(user_id, conversation_id) is None:
            raise ValueError("Conversation was not found for this user")

        del self.conversations[conversation_id]


@pytest.fixture
def conversation_repository(monkeypatch: pytest.MonkeyPatch) -> Generator[ConversationRepositoryStub]:
    repository = ConversationRepositoryStub()
    monkeypatch.setattr(conversation_service, "SqlConversationRepository", lambda db: repository)
    monkeypatch.setattr(conversation_service, "_load_trip_history", lambda user_id, db: [])
    monkeypatch.setattr(conversation_service, "load_route_context",
                        lambda user_id, vehicle_id, current_location, db: {})
    app.dependency_overrides[get_current_user_id] = lambda: USER_ID
    app.dependency_overrides[get_db] = lambda: object()
    yield repository
    app.dependency_overrides.clear()


def test_user_can_create_list_and_read_conversation(conversation_repository: ConversationRepositoryStub) -> None:
    create_response = client.post(
        "/users/me/conversations",
        json={"title": "Road trip"},
    )

    conversation_id = next(iter(conversation_repository.conversations))
    list_response = client.get("/users/me/conversations")
    get_response = client.get(f"/users/me/conversations/{conversation_id}")

    assert create_response.status_code == 200
    assert list_response.status_code == 200
    assert get_response.status_code == 200
    assert list_response.json()["conversations"][0]["conversation_id"] == conversation_id
    assert get_response.json()["conversation_title"] == "Road trip"
    assert get_response.json()["messages"] == []


def test_user_message_is_saved_with_assistant_response(
    conversation_repository: ConversationRepositoryStub,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conversation = conversation_repository.create_user_conversation(
        USER_ID,
        "Road trip",
    )

    class LLMStub:
        async def generate_response(self, context: list[dict[str, str]]) -> str:
            return "Assistant response"

    monkeypatch.setattr(conversation_service, "LLM_Agent", LLMStub)

    response = client.post(
        f"/users/me/conversations/{conversation.conversation_id}/messages",
        json={"content": "Find a route"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": conversation.conversation_id,
        "response": "Assistant response",
        "recommendations": [],
    }
    assert [message.chat_role for message in conversation.messages] == [
        "user",
        "assistant",
    ]


def test_user_can_delete_own_conversation(conversation_repository: ConversationRepositoryStub) -> None:
    conversation = conversation_repository.create_user_conversation(
        USER_ID,
        "Road trip",
    )

    response = client.delete(
        f"/users/me/conversations/{conversation.conversation_id}"
    )

    assert response.status_code == 204
    assert conversation.conversation_id not in conversation_repository.conversations


def test_user_cannot_read_or_delete_another_users_conversation(
    conversation_repository: ConversationRepositoryStub,
) -> None:
    conversation = conversation_repository.create_user_conversation(
        "user-2",
        "Private trip",
    )

    get_response = client.get(
        f"/users/me/conversations/{conversation.conversation_id}"
    )
    delete_response = client.delete(
        f"/users/me/conversations/{conversation.conversation_id}"
    )

    assert get_response.status_code == 404
    assert delete_response.status_code == 404
    assert conversation.conversation_id in conversation_repository.conversations


def test_nonexistent_conversation_returns_not_found(
    conversation_repository: ConversationRepositoryStub,
) -> None:
    missing_conversation_id = "missing-conversation"

    get_response = client.get(
        f"/users/me/conversations/{missing_conversation_id}"
    )
    delete_response = client.delete(
        f"/users/me/conversations/{missing_conversation_id}"
    )
    message_response = client.post(
        f"/users/me/conversations/{missing_conversation_id}/messages",
        json={"content": "Test message"},
    )

    assert get_response.status_code == 404
    assert delete_response.status_code == 404
    assert message_response.status_code == 404


def test_conversation_endpoints_require_authentication(
    conversation_repository: ConversationRepositoryStub,
) -> None:
    app.dependency_overrides.pop(get_current_user_id)

    response = client.get("/users/me/conversations")

    assert response.status_code == 401
