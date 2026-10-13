import json
from datetime import UTC, datetime
from uuid import uuid4
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.models.users import (
    DriverType,
    RoadConditions,
    User,
    UserCredentials,
    UserPreference,
)
from backend.repositories.conversations import (
    SqlConversationRepository,
)
from backend.repositories.opportunities import (
    SqlOpportunityRepository,
)
from backend.repositories.trips import SqlTripRepository
from backend.repositories.users import SqlUserRepository
from backend.repositories.vehicles import SqlVehicleRepository
from backend.schemas.users import (
    Token,
    UserInput,
    UserLoginInput,
    UserOutput,
    UserPasswordReset,
    UserPasswordUpdate,
    UserPreferencesUpdate,
    UserProfileUpdate,
)
from backend.security import _hash_password, _verify_password, create_access_token


# Convert API preferences into the domain value object.
def _to_domain_preferences(preferences: dict, user_id: str) -> UserPreference:
    try:
        return UserPreference(
            user_id=user_id,
            age_group=preferences["age_group"],
            driver_type=DriverType(
                preferences["driver_type"]
            ),
            road_conditions=[
                RoadConditions(item)
                for item in preferences["road_conditions"]
            ],
            tolls=bool(preferences["tolls"]),
        )

    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f'Invalid preferences: {error}') from error




# Convert domain preferences into the public API format.
def _preferences_to_dict(preferences: UserPreference) -> dict:
    return {
        "age_group": preferences.age_group,
        "driver_type": preferences.driver_type.value,
        "road_conditions": [
            condition.value
            for condition in preferences.road_conditions
        ],
        "tolls": preferences.tolls,
    }




# Convert a domain User entity into a public API response.
def _to_user_response(user: User) -> UserOutput:
    return UserOutput(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        preferences=_preferences_to_dict(
            user.preferences
        ),
        created_at=user.created_at,
    )


# Miro: register_user()
# Repository: SqlUserRepository.create_user()
def register_user(payload: UserInput, db: Session) -> UserOutput:
    repository = SqlUserRepository(db)

    existing_username = repository.get_user_by_username(
        payload.username
    )

    if existing_username is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Username already exists')

    email = str(payload.email)

    existing_email = repository.get_user_by_email(email)

    if existing_email is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email already exists')

    user_id = str(uuid4())
    created_at = datetime.now(UTC)

    preferences = _to_domain_preferences(payload.preferences, user_id)

    user = User(
        user_id=user_id,
        username=payload.username,
        email=email,
        created_at=created_at,
        preferences=preferences,
        trip_history=[],
        conversations=[],
    )

    credentials = UserCredentials(
        user_id=user_id,
        password_hash=_hash_password(payload.password),
    )

    created_user = repository.create_user(user,credentials)

    return _to_user_response(created_user)


# Miro: login_user()
# Repository: get_password_hash_by_email()
# Repository: get_user_by_email()
def login_user(payload: UserLoginInput, db: Session) -> Token:
    repository = SqlUserRepository(db)

    email = str(payload.email)

    stored_hash = repository.get_password_hash_by_email(email)

    if stored_hash is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid email or password')

    if not _verify_password(payload.password,stored_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid email or password')

    user = repository.get_user_by_email(email)

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    # Generate a JWT after verifying the user's credentials.
    access_token = create_access_token(user.user_id)

    return Token(access_token=access_token, token_type="bearer")


# Miro: get_my_profile()
# Repository: SqlUserRepository.get_user_by_id()
def get_my_profile(current_user_id: str, db: Session) -> UserOutput:
    repository = SqlUserRepository(db)

    user = repository.get_user_by_id(current_user_id)

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    return _to_user_response(user)


# Miro: update_my_profile()
# Repository: SqlUserRepository.update_partial_user()
def update_my_profile(payload: UserProfileUpdate, current_user_id: str, db: Session) -> UserOutput:
    repository = SqlUserRepository(db)

    user = repository.get_user_by_id(current_user_id)

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    fields = payload.model_dump(
        exclude_unset=True,
        exclude_none=True,
    )

    if not fields:
        return _to_user_response(user)

    if "username" in fields:
        existing_username = repository.get_user_by_username(fields["username"])

        if (
            existing_username is not None
            and existing_username.user_id != current_user_id
        ):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Username already exists')

    if "email" in fields:
        fields["email"] = str(fields["email"])
        existing_email = repository.get_user_by_email(fields["email"])

        if (
            existing_email is not None
            and existing_email.user_id != current_user_id
        ):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email already exists')

    updated_user = repository.update_partial_user(
        user,
        fields,
    )

    return _to_user_response(updated_user)


# Miro: update_my_preferences()
# Repository: SqlUserRepository.update_partial_user()
def update_my_preferences(payload: UserPreferencesUpdate, current_user_id: str, db: Session) -> UserOutput:
    repository = SqlUserRepository(db)

    user = repository.get_user_by_id(current_user_id)

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    preferences = _to_domain_preferences(payload.preferences, current_user_id)

    fields = {
        "user_preferences_json": json.dumps(
            _preferences_to_dict(preferences)
        ),
    }

    updated_user = repository.update_partial_user(user,fields)

    return _to_user_response(updated_user)


def delete_my_profile(user: str, db: Session):
    repository = SqlUserRepository(db)
    trip_repository = SqlTripRepository(db)
    opportunity_repository = SqlOpportunityRepository(db)
    vehicle_repository = SqlVehicleRepository(db)

    user_obj = repository.get_user_by_id(user)

    if user_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    trip_repository.delete_user_trips(user_obj.user_id)
    opportunity_repository.delete_user_opportunities(user_obj.user_id)
    vehicle_repository.delete_user_vehicles(user_obj.user_id)
    for conversation in SqlConversationRepository(db).load_user_conversations(user_obj.user_id):
        SqlConversationRepository(db).delete_user_conversation(user_obj.user_id, conversation.conversation_id)
    repository.delete_user(user_obj.user_id)

    return {"detail": "User deleted successfully"}


def change_my_password(payload: UserPasswordUpdate, current_user_id: str, db: Session):
    repository = SqlUserRepository(db)

    user = repository.get_user_by_id(current_user_id)

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    stored_hash = repository.get_password_hash_by_email(user.email)

    if stored_hash is None or not _verify_password(
        payload.current_password,
        stored_hash,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Current password is incorrect')

    repository.update_partial_user(
        user,
        {"password_hash": _hash_password(payload.new_password)},
    )

    return {"detail": "Password changed successfully"}


def reset_my_password(payload: UserPasswordReset, current_user_id: str, db: Session):
    repository = SqlUserRepository(db)

    user = repository.get_user_by_id(current_user_id)

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    repository.update_partial_user(
        user,
        {"password_hash": _hash_password(payload.new_password)},
    )

    return {"detail": "Password reset successfully"}

