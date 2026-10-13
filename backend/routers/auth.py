from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.users import (
    Token,
    UserInput,
    UserLoginInput,
    UserOutput,
)
from backend.services import users as service

router = APIRouter(prefix='/users', tags=['Users'])


@router.post('/register', response_model=UserOutput, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserInput, db: Annotated[Session, Depends(get_db)]) -> UserOutput:
    return service.register_user(payload, db)


@router.post('/login', response_model=Token, status_code=status.HTTP_200_OK)
def login_user(payload: UserLoginInput, db: Annotated[Session, Depends(get_db)]) -> Token:
    return service.login_user(payload, db)
