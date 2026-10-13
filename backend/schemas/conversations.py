from typing import Annotated
from pydantic import BaseModel, Field

from backend.schemas.trips import LocationSchema


class MessageLog(BaseModel):
    content: Annotated[str, Field(description="The content of the message", min_length = 1)]
    vehicle_id: str | None = Field(default=None, min_length=1, max_length=64)
    current_location: LocationSchema | None = None


class ResponseLog(BaseModel):
    conversation_id: Annotated[str, Field(description="The ID of the conversation")]
    response: Annotated[str, Field(description="The content of the response", min_length = 1)]
    recommendations: list[dict] = Field(default_factory=list)


class RecommendationAccept(BaseModel):
    # Optional user overrides: segment qid -> route_index.
    choices: dict[int, int] = Field(default_factory=dict)
    current_location: LocationSchema


class ConversationCreate(BaseModel):
    title: Annotated[str, Field(description="The title of the conversation")]
    
