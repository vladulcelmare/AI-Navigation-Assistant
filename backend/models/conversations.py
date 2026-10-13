from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    conversation_id: str
    message_id: int
    content: str
    chat_role: str

@dataclass
class Conversation:
    conversation_id: str
    user_id: str
    title: str
    creation_date: datetime
    messages: list[Message]
    recommendations: list[dict] = field(default_factory=list)
