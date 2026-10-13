import json
from datetime import date, datetime
from typing import Protocol, override
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.users import (
    DriverType,
    RoadConditions,
    User,
    UserCredentials,
    UserPreference,
)


class UserRepository(Protocol):
    def get_user_by_id(self, user_id: str) -> User | None:
        """
        Fetch an user by ID
        """

    def get_user_by_username(self, username: str) -> User | None:
        """
        Fetch an user by username
        """

    def get_user_by_email(self, email: str) -> User | None:
        """
        Fetch an user by email
        """

    def get_password_hash_by_email(self, email: str,) -> str | None:
        """
        Return the stored password hash for internal authentication only
        """

    def create_user(self, user: User, credentials: UserCredentials) -> User:
        """
        Create a new user
        """

    def update_user(self, user: User, credentials: UserCredentials) -> User:
        """
        Update an existing user
        """

    def update_partial_user(self, user: User, fields: dict) -> User:
        """
        Updates specific fields of an existing user
        """

    def delete_user(self, user_id: str) -> None:
        """
        Deletes an existing user
        """

    def delete_user_password(self, user_id: str, new_psd: str) -> str:
        """
        Deletes the password for an existing user and returns the new password to be sent by email
        """


class SqlUserRepository(UserRepository):
    def __init__(self, db: Session):
        """
        Store the SQLAlchemy session used by the repository
        """
        self.db = db

    @staticmethod
    def _serialize_preferences(preferences: UserPreference) -> str:
        """
        Convert domain preferences into a JSON suitable for database
        """

        return json.dumps(
            {
                "age_group": preferences.age_group,
                "driver_type": preferences.driver_type.value,
                "road_conditions": [
                    condition.value
                    for condition in preferences.road_conditions
                ],
                "tolls": preferences.tolls,
            }
        )

    @staticmethod
    def _deserialize_preferences(value: str | None, user_id: str) -> UserPreference:
        """
        Rebuild domain preferences from database JSON
        """

        if not value:
            return UserPreference(
                user_id=user_id,
                age_group="adult",
                driver_type=DriverType.EFFICIENT,
                road_conditions=[
                    RoadConditions.MIXED
                ],
                tolls=True,
            )

        data = json.loads(value)

        return UserPreference(
            user_id=user_id,
            age_group=data["age_group"],
            driver_type=DriverType(
                data["driver_type"]
            ),
            road_conditions=[
                RoadConditions(item)
                for item in data["road_conditions"]
            ],
            tolls=bool(data["tolls"]),
        )

    @staticmethod
    def _to_datetime(value: date | datetime) -> datetime:
        """
        Normalize a date or datetime value to datetime
        """

        if isinstance(value, datetime):
            return value

        return datetime.combine(
            value,
            datetime.min.time(),
        )

    @classmethod
    def _row_to_user(cls, row) -> User:
        """
        Convert a SQL row into a domain User entity
        """

        user_id = row["user_unique_id"]

        return User(
            user_id=user_id,
            username=row["username"],
            email=row["user_email"],
            created_at=cls._to_datetime(
                row["creation_date"]
            ),
            preferences=cls._deserialize_preferences(
                row["user_preferences_json"],
                user_id,
            ),
            trip_history=[],
            conversations=[],
        )

    @override
    def get_user_by_id(self, user_id: str) -> User | None:
        """
        Find a user by their unique ID
        """

        query = text("""
            SELECT
                user_unique_id,
                username,
                password_hash,
                user_email,
                creation_date,
                user_preferences_json
            FROM Users_Management.user_info
            WHERE user_unique_id = :user_id
        """)

        row = self.db.execute(
            query,
            {"user_id": user_id},
        ).mappings().first()

        if row is None:
            return None

        return self._row_to_user(row)

    @override
    def get_user_by_username(self, username: str) -> User | None:
        """
        Find a user by their username
        """

        query = text("""
            SELECT
                user_unique_id,
                username,
                password_hash,
                user_email,
                creation_date,
                user_preferences_json
            FROM Users_Management.user_info
            WHERE username = :username
        """)

        row = self.db.execute(
            query,
            {"username": username},
        ).mappings().first()

        if row is None:
            return None

        return self._row_to_user(row)

    @override
    def get_user_by_email(self, email: str) -> User | None:
        """
        Find a user by their email address
        """

        query = text("""
            SELECT
                user_unique_id,
                username,
                password_hash,
                user_email,
                creation_date,
                user_preferences_json
            FROM Users_Management.user_info
            WHERE user_email = :email
        """)

        row = self.db.execute(
            query,
            {"email": email},
        ).mappings().first()

        if row is None:
            return None

        return self._row_to_user(row)

    @override
    def get_password_hash_by_email(self, email: str) -> str | None:
        """
        Return the stored password hash for authentication
        """

        query = text("""
            SELECT password_hash
            FROM Users_Management.user_info
            WHERE user_email = :email
        """)

        row = self.db.execute(
            query,
            {"email": email},
        ).mappings().first()

        if row is None:
            return None

        return row["password_hash"]

    @override
    def create_user(self, user: User, credentials: UserCredentials) -> User:
        """
        Create a user
        """

        if credentials.user_id != user.user_id:
            raise ValueError(
                "User ID and credentials user ID must match"
            )

        query = text("""
            INSERT INTO Users_Management.user_info
            (
                user_unique_id,
                username,
                password_hash,
                user_email,
                creation_date,
                user_preferences_json
            )
            VALUES
            (
                :user_id,
                :username,
                :password_hash,
                :email,
                :creation_date,
                :preferences
            )
        """)

        try:
            self.db.execute(
                query,
                {
                    "user_id": user.user_id,
                    "username": user.username,
                    "password_hash": (
                        credentials.password_hash
                    ),
                    "email": user.email,
                    "creation_date": (
                        user.created_at.date()
                    ),
                    "preferences": (
                        self._serialize_preferences(
                            user.preferences
                        )
                    ),
                },
            )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return self.get_user_by_id(user.user_id)

    @override
    def update_user(self, user: User, credentials: UserCredentials) -> User:
        """
        Update all user fields
        """

        if credentials.user_id != user.user_id:
            raise ValueError(
                "User ID and credentials user ID must match"
            )

        query = text("""
            UPDATE Users_Management.user_info
            SET
                username = :username,
                password_hash = :password_hash,
                user_email = :email,
                creation_date = :creation_date,
                user_preferences_json = :preferences
            WHERE user_unique_id = :user_id
        """)

        try:
            result = self.db.execute(
                query,
                {
                    "user_id": user.user_id,
                    "username": user.username,
                    "password_hash": (
                        credentials.password_hash
                    ),
                    "email": user.email,
                    "creation_date": (
                        user.created_at.date()
                    ),
                    "preferences": (
                        self._serialize_preferences(
                            user.preferences
                        )
                    ),
                },
            )

            if result.rowcount == 0:
                self.db.rollback()
                raise ValueError(
                    "User was not found"
                )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return self.get_user_by_id(user.user_id)

    @override
    def update_partial_user(self, user: User, fields: dict) -> User:
        """
        Partially update user fields
        """

        field_to_db_column = {
            "username": "username",
            "email": "user_email",
            "password_hash": "password_hash",
            "creation_date": "creation_date",
            "user_preferences_json": (
                "user_preferences_json"
            ),
        }

        invalid_fields = set(fields) - set(field_to_db_column)

        if invalid_fields:
            raise ValueError(
                f"Unsupported fields: {invalid_fields}"
            )

        if not fields:
            return self.get_user_by_id(user.user_id)

        set_clauses = ", ".join(f"{field_to_db_column[field]} = :{field}" for field in fields)

        values = dict(fields)
        values["user_id"] = user.user_id

        query = text(f"""
            UPDATE Users_Management.user_info
            SET {set_clauses}
            WHERE user_unique_id = :user_id
        """)

        try:
            result = self.db.execute(
                query,
                values,
            )

            if result.rowcount == 0:
                self.db.rollback()
                raise ValueError(
                    "User was not found"
                )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return self.get_user_by_id(user.user_id)

    @override
    def delete_user_password(self, user_id: str, new_psd: str = "1234") -> str:
        """
        Delete user password
        """

        query = text("""
            UPDATE Users_Management.user_info
            SET password_hash = :revoked_password
            WHERE user_unique_id = :user_id
        """)

        try:
            result = self.db.execute(
                query,
                {
                    "user_id": user_id,
                    "revoked_password": new_psd,
                },
            )

            if result.rowcount == 0:
                self.db.rollback()
                raise ValueError("User was not found")

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return new_psd


    @override
    def delete_user(self, user_id: str,) -> None:
        """
        Delete an user
        """
        query = text("""
            DELETE FROM Users_Management.user_info
            WHERE user_unique_id = :user_id
        """)
    
        try:
            result = self.db.execute(
                query,
                {"user_id": user_id},
            )
    
            if result.rowcount == 0:
                self.db.rollback()
                raise ValueError(
                    "User was not found"
                )
    
            self.db.commit()
    
        except Exception:
            self.db.rollback()
            raise
