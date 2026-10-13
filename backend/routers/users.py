from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user_id
from backend.schemas.users import (
    UserOutput,
    UserPasswordReset,
    UserPasswordUpdate,
    UserPreferencesUpdate,
    UserProfileUpdate,
)
from backend.services import users as service

router = APIRouter(prefix='/users', tags=['Users'])


@router.get('/me', response_model=UserOutput, status_code=status.HTTP_200_OK)
def get_my_profile(current_user_id: Annotated[str, Depends(get_current_user_id)], db: Annotated[Session, Depends(get_db)]) -> UserOutput:
    return service.get_my_profile(current_user_id, db)


@router.patch('/me', response_model=UserOutput, status_code=status.HTTP_200_OK)
def update_my_profile(payload: UserProfileUpdate, current_user_id: Annotated[str, Depends(get_current_user_id)], db: Annotated[Session, Depends(get_db)]) -> UserOutput:
    return service.update_my_profile(payload, current_user_id, db)


@router.patch('/me/preferences', response_model=UserOutput, status_code=status.HTTP_200_OK)
def update_my_preferences(payload: UserPreferencesUpdate, current_user_id: Annotated[str, Depends(get_current_user_id)], db: Annotated[Session, Depends(get_db)]) -> UserOutput:
    return service.update_my_preferences(payload, current_user_id, db)


@router.delete('/me')
def delete_my_profile(user: Annotated[str, Depends(get_current_user_id)], db: Annotated[Session, Depends(get_db)]):
    return service.delete_my_profile(user, db)


@router.patch('/me/password', status_code=status.HTTP_200_OK)
def change_my_password(payload: UserPasswordUpdate, current_user_id: Annotated[str, Depends(get_current_user_id)], db: Annotated[Session, Depends(get_db)]):
    return service.change_my_password(payload, current_user_id, db)


@router.patch('/me/password/reset', status_code=status.HTTP_200_OK)
def reset_my_password(payload: UserPasswordReset, current_user_id: Annotated[str, Depends(get_current_user_id)], db: Annotated[Session, Depends(get_db)]):
    return service.reset_my_password(payload, current_user_id, db)
