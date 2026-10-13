from fastapi import HTTPException, status
from openai import APIConnectionError, APIStatusError, RateLimitError
from sqlalchemy.orm import Session

from backend.integrations.openai_client import LLM_Agent
from backend.repositories.conversations import (
    SqlConversationRepository,
)
from backend.schemas.conversations import ConversationCreate, MessageLog, ResponseLog
from backend.repositories.trips import SqlTripRepository
from backend.models.trips import TripStatus
from backend.services.assistant_trips import load_route_context, make_recommendation, describe_recommendation


def _load_trip_history(current_user_id: str, db: Session) -> list[dict]:
    trips = SqlTripRepository(db).get_trips_by_user_id(current_user_id)
    return [
        {"origin": vars(trip.origin), "destination": vars(trip.destination),
         "distance_km": trip.route.distance_km,
         "duration_minutes": trip.route.duration_minutes,
         "cost_per_km": trip.cost_per_km}
        for trip in trips if trip.status == TripStatus.COMPLETED
    ][:20]


def create_user_conversation(payload: ConversationCreate, current_user_id: str, db: Session):
    repository = SqlConversationRepository(db)

    conversation = repository.create_user_conversation(
        current_user_id,
        payload.title,
    )

    return {"conversation_title": conversation.title,
            "conversation_id": conversation.conversation_id,
            "detail": "Conversation created successfully"}


def get_user_conversation(current_user_id: str, conversation_id: str, db: Session):
    repository = SqlConversationRepository(db)

    conversation = repository.load_user_conversation(
        current_user_id,
        conversation_id,
    )

    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Conversation not found')

    return {"conversation_title": conversation.title,
            "messages": [{"role": message.chat_role, "content": message.content} for message in conversation.messages],
            "recommendations": conversation.recommendations,
            "detail": "Conversation retrieved successfully"}


def delete_user_conversation(current_user_id: str, conversation_id: str, db: Session) -> None:
    repository = SqlConversationRepository(db)

    conversation = repository.load_user_conversation(
        current_user_id,
        conversation_id,
    )

    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Conversation not found')

    repository.delete_user_conversation(
        current_user_id,
        conversation_id,
    )


async def log_my_message(conversation_id: str, payload: MessageLog, current_user_id: str, db: Session):
    repository = SqlConversationRepository(db)

    conversation = repository.load_user_conversation(
        current_user_id,
        conversation_id,
    )

    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Conversation not found')

    repository.log_user_message(
        current_user_id,
        conversation_id,
        payload.content,
        "user"
    )

    conversation = repository.load_user_conversation(
            current_user_id,
            conversation_id,
        )

    history = [{"role": message.chat_role,
                "content": message.content}
                for message in conversation.messages]

    agent = LLM_Agent()
    agent.trip_history = _load_trip_history(current_user_id, db)
    vehicle_id = payload.vehicle_id
    if not vehicle_id and conversation.recommendations:
        vehicle_id = conversation.recommendations[-1]["vehicle_id"]
    agent.route_context = load_route_context(current_user_id, vehicle_id, payload.current_location, db)
    try:
        assistant_response = await agent.generate_response(
            history
        )
    except RateLimitError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='AI service is temporarily unavailable') from error
    except APIConnectionError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Could not connect to AI service') from error
    except APIStatusError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='AI service returned an error') from error

    recommendations = []
    if isinstance(assistant_response, list):
        recommendations = [await make_recommendation(result, selected, agent.route_context)
                           for result, selected in assistant_response]
        repository.save_recommendations(current_user_id, conversation_id, recommendations)
        assistant_response = "\n\n".join(describe_recommendation(item) for item in recommendations)
    repository.log_user_message(
        current_user_id,
        conversation_id,
        assistant_response,
        "assistant",
    )

    return ResponseLog(
        conversation_id=conversation_id,
        response=assistant_response,
        recommendations=recommendations,
    )


def get_user_conversations(current_user_id: str, db: Session):
    repository = SqlConversationRepository(db)

    conversations = repository.load_user_conversations(current_user_id)

    return {"conversations": [{"conversation_id": conversation.conversation_id, "title": conversation.title} for conversation in conversations],
            "detail": "Conversations retrieved successfully"}

