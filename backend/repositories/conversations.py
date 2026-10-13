from datetime import datetime
import json
from typing import Protocol, override
from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.conversations import Conversation, Message


class ConversationRepository(Protocol):
    def delete_user_conversation(self, user_id: str, conversation_id: str) -> None:
        """
        Deletes a specific conversation for an existing user
        """

    def create_user_conversation(self, user_id: str, title: str) -> Conversation:
        """
        Creates a new conversation for an existing user
        """

    def load_user_conversation(self, user_id: str, conversation_id: str) -> Conversation | None:
        """
        Loads a specific conversation for an existing user
        """

    def load_user_conversations(self, user_id: str) -> list[Conversation]:
        """
        Loads all conversations for an existing user
        """

    def log_user_message(self, user_id: str, conversation_id: str, message: str, role: str) -> None:
        """
        Logs a message for a specific conversation of an existing user
        """


class SqlConversationRepository(ConversationRepository):
    def __init__(self, db: Session):
        self.db = db

    def save_recommendations(self, user_id: str, conversation_id: str, recommendations: list[dict]):
        try:
            self.db.execute(text("""
                UPDATE Users_Chats.Conversations SET recommendations_json = :recommendations
                WHERE user_unique_id = :user_id AND conversation_id = :conversation_id
            """), {"user_id": user_id, "conversation_id": conversation_id,
                   "recommendations": json.dumps(recommendations)})
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    @override
    def delete_user_conversation(self, user_id: str, conversation_id: str) -> None:
        """
        Delete a conversation of an user
        """

        conversation = self.load_user_conversation(user_id, conversation_id)

        if conversation is None:
            raise ValueError(
                "Conversation was not found for this user"
            )

        delete_messages_query = text("""
            DELETE FROM Users_Chats.Messages
            WHERE conversation_id = :conversation_id
        """)

        delete_conversations_query = text("""
            DELETE FROM Users_Chats.Conversations
            WHERE user_unique_id = :user_id
            AND conversation_id = :conversation_id
        """)

        try:
            self.db.execute(
                delete_messages_query,
                {"conversation_id": conversation_id},
            )

            result = self.db.execute(
                delete_conversations_query,
                {"user_id": user_id, "conversation_id": conversation_id},
            )

            if result.rowcount == 0:
                self.db.rollback()
                raise ValueError(
                    "Conversation was not found for this user"
                )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

    @override
    def create_user_conversation(self, user_id: str, title: str) -> Conversation:
        """
        Create a conversation
        """

        conversation_id = str(uuid4())
        creation_date = datetime.now().astimezone()

        query = text("""
            INSERT INTO Users_Chats.Conversations
            (
                user_unique_id,
                conversation_id,
                title,
                creation_date
            )
            VALUES
            (
                :user_id,
                :conversation_id,
                :title,
                :creation_date
            )
        """)

        try:
            self.db.execute(
                query,
                {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "title": title,
                    "creation_date": creation_date.date(),
                },
            )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return Conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            title=title,
            creation_date=creation_date,
            messages=[],
        )

    def _load_conversation_messages(self, conversation_id: str) -> list[Message]:
        query = text("""
            SELECT
                message_id,
                conversation_id,
                content,
                chat_role
            FROM Users_Chats.Messages
            WHERE conversation_id = :conversation_id
            ORDER BY message_id ASC
        """)

        rows = self.db.execute(
            query,
            {"conversation_id": conversation_id},
        ).mappings().all()

        return [
            Message(
                message_id=row["message_id"],
                conversation_id=row["conversation_id"],
                content=row["content"],
                chat_role=row["chat_role"],
            )
            for row in rows
        ]

    @override
    def load_user_conversation(self, user_id: str, conversation_id: str) -> Conversation | None:
        """
        Load a specific conversation for an existing user
        """
        query = text("""
            SELECT 
                user_unique_id,
                conversation_id,
                title,
                creation_date,
                recommendations_json
            FROM 
                Users_Chats.Conversations
            WHERE conversation_id = :conversation_id
            AND user_unique_id = :user_id
        """)

        result = self.db.execute(
            query,
            {"user_id": user_id, 
             "conversation_id": conversation_id},
        ).mappings().first()

        if result is None:
            return None

        messages = self._load_conversation_messages(conversation_id)

        conversation = Conversation(
            conversation_id=result["conversation_id"],
            user_id=result["user_unique_id"],
            title=result["title"],
            creation_date=result["creation_date"],
            messages=messages,
            recommendations=json.loads(result["recommendations_json"] or "[]"),
        )

        return conversation

    @override
    def load_user_conversations(self, user_id: str) -> list[Conversation]:
        """
        Load all conversations for an existing user
        """
        query = text("""
            SELECT 
                user_unique_id,
                conversation_id
            FROM 
                Users_Chats.Conversations
            WHERE user_unique_id = :user_id
        """)

        rows = self.db.execute(
            query,
            {"user_id": user_id},
        ).mappings().all()

        conversations = []
        for row in rows:
            conversation_obj = self.load_user_conversation(user_id, row["conversation_id"])
            conversation = Conversation(
                conversation_id=conversation_obj.conversation_id,
                user_id=conversation_obj.user_id,
                title=conversation_obj.title,
                creation_date=conversation_obj.creation_date,
                messages=conversation_obj.messages,
            )
            conversations.append(conversation)

        return conversations

    @override
    def log_user_message(self, user_id: str, conversation_id: str, message: str, role: str) -> None:
        """
        Logs a message for a specific conversation of an existing user
        """
        if message is None:
            return

        conversation = self.load_user_conversation(user_id, conversation_id)
        if conversation is None:
            raise ValueError(
                "Conversation was not found for this user"
            )
        
        query = text("""
            INSERT INTO Users_Chats.Messages
            (
                conversation_id,
                content,
                chat_role
            )
            VALUES
            (
                :conversation_id,
                :message,
                :chat_role
            )
        """)

        try:
            self.db.execute(
                query,
                {
                    "conversation_id": conversation_id,
                    "message": message,
                    "chat_role": role,
                },
            )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise
