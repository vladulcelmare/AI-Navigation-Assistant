from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user_id
from backend.schemas.conversations import ConversationCreate, MessageLog, RecommendationAccept
from backend.schemas.trips import TripOutput
from backend.services.assistant_trips import accept_recommendation
from backend.routers.trips import _to_response
from backend.services import conversations as service

router = APIRouter(prefix='/users', tags=['Users'])


@router.post('/me/conversations/{conversation_id}/recommendations/{recommendation_id}/accept', response_model=TripOutput)
async def accept_route(conversation_id: str, recommendation_id: str, payload: RecommendationAccept,
                 current_user_id: Annotated[str, Depends(get_current_user_id)],
                 db: Annotated[Session, Depends(get_db)]):
    trip = await accept_recommendation(
        current_user_id,
        conversation_id,
        recommendation_id,
        payload.choices,
        payload.current_location,
        db,
    )

    return _to_response(trip)


@router.post('/me/conversations')
def create_user_conversation(payload: ConversationCreate, current_user_id: Annotated[str, Depends(get_current_user_id)], db: Annotated[Session, Depends(get_db)]):
    return service.create_user_conversation(payload, current_user_id, db)


@router.get('/me/conversations/{conversation_id}')
def get_user_conversation(current_user_id: Annotated[str, Depends(get_current_user_id)], conversation_id: str, db: Annotated[Session, Depends(get_db)]):
    return service.get_user_conversation(current_user_id, conversation_id, db)


@router.delete('/me/conversations/{conversation_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_user_conversation(current_user_id: Annotated[str, Depends(get_current_user_id)], conversation_id: str, db: Annotated[Session, Depends(get_db)]) -> None:
    return service.delete_user_conversation(current_user_id, conversation_id, db)


@router.post('/me/conversations/{conversation_id}/messages')
async def log_my_message(conversation_id: str, payload: MessageLog, current_user_id: Annotated[str, Depends(get_current_user_id)], db: Annotated[Session, Depends(get_db)]):
    return await service.log_my_message(conversation_id, payload, current_user_id, db)


@router.get('/me/conversations')
def get_user_conversations(current_user_id: Annotated[str, Depends(get_current_user_id)], db: Annotated[Session, Depends(get_db)]):
    return service.get_user_conversations(current_user_id, db)
