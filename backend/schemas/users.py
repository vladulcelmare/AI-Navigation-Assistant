from datetime import datetime
from typing import Annotated, Any
from pydantic import BaseModel, EmailStr, Field


# Request and response models used by the user and authentication endpoints
class UserInput(BaseModel):
    username: Annotated[str, Field(description="The username of the user")]
    email: Annotated[EmailStr, Field(description="The email of the user")]
    password: Annotated[str, Field(description="The password of the user")]
    preferences: Annotated[dict, Field(description="The preferences of the user")]

class UserOutput(BaseModel):
    user_id: Annotated[str, Field(description="The ID of the user")]
    username: Annotated[str, Field(description="The username of the user")]
    email: Annotated[EmailStr, Field(description="The email of the user")]
    preferences: Annotated[dict, Field(description="The preferences of the user")]
    created_at: Annotated[datetime, Field(description="The creation date of the user")]

class UserLoginInput(BaseModel):
    email: Annotated[EmailStr, Field(description="The email of the user")]
    password: Annotated[str, Field(min_length=8, description="The password of the user")]

class Token(BaseModel):
    access_token: Annotated[str, Field(description="The JWT access token")]
    token_type: Annotated[str, Field(description="The authentication scheme")] = "bearer"

class UserPreferencesUpdate(BaseModel):
    preferences: Annotated[dict[str, Any], Field(description="The updated preferences of the user")]

class UserProfileUpdate(BaseModel):
    username: Annotated[str | None, Field(description="The updated username of the user")] = None
    email: Annotated[EmailStr | None, Field(description="The updated email of the user")] = None

class UserPasswordUpdate(BaseModel):
    current_password: Annotated[str, Field(min_length=8, description="The current password of the user")]
    new_password: Annotated[str, Field(min_length=8, description="The new password of the user")]

class UserPasswordReset(BaseModel):
    new_password: Annotated[str, Field(min_length=8, description="The new password of the user")]



