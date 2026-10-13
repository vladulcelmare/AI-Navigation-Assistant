import json
from typing import Protocol, override
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.opportunities import Opportunities


class OpportunityRepository(Protocol):
    def get_opportunities_for_user(self, user_id: str) -> list[Opportunities]:
        """
        Gets all opportunities for an user
        """

    def get_opportunity_for_user(self, user_id: str, partner_name: str) -> Opportunities | None:
        """
        Gets a specific opportunity for an user
        """

    def get_all_opportunities(self) -> list[Opportunities]:
        """
        Lists all available opportunities
        """

    def create_opportunity(self, opportunity: Opportunities) -> Opportunities:
        """
        Creates a new opportunity
        """

    def update_partial_opportunity(self, opportunity: Opportunities, fields: dict) -> Opportunities:
        """
        Updates specific fields of an existing opportunity
        """
    
    def update_opportunity(self, opportunity: Opportunities) -> Opportunities:
        """
        Updates an existing opportunity
        """

    def delete_opportunity(self, user_id: str, partner_name: str) -> None:
        """
        Deletes an opportunity
        """

    def delete_user_opportunities(self, user_id: str) -> None:
        """
        Deletes all opportunities belonging to a user
        """


class SqlOpportunityRepository(OpportunityRepository):
    def __init__(self, db: Session):
        """
        Store sqlalchemy session
        """
        self.db = db

    @staticmethod
    def _serialize_json(value: dict | None) -> str | None:
        """
        Convert dict into .json
        """
        if value is None:
            return None

        return json.dumps(value)

    @staticmethod
    def _deserialize_json(value: str | None) -> dict:
        """
        Convert JSON string from the database into a dict
        """
        if not value:
            return {}

        if isinstance(value, dict):
            return value

        return json.loads(value)

    @classmethod
    def _row_to_opportunity(cls, row) -> Opportunities:
        """
        Transform a SQL row into a domain Opportunities entity.
        """
        return Opportunities(
            user_id=row["user_unique_id"],
            partner_name=row["partner_name"],
            partner_type=row["partner_type"],
            partner_offers=cls._deserialize_json(
                row["partner_offers_json"]
            ),
            partner_criteria=cls._deserialize_json(
                row["partner_offer_criteria_json"]
            ),
        )

    @override
    def get_opportunities_for_user(self, user_id: str) -> list[Opportunities]:
        """Return all opportunities belonging to a user."""
        rows = self.db.execute(
            text("""
                SELECT
                    user_unique_id,
                    partner_name,
                    partner_type,
                    partner_offers_json,
                    partner_offer_criteria_json
                FROM Users_Opportunities.partners
                WHERE user_unique_id = :user_id
                ORDER BY partner_name
            """),
            {"user_id": user_id},
        ).mappings().all()

        return [self._row_to_opportunity(row) for row in rows]

    @override
    def get_opportunity_for_user(self, user_id: str, partner_name: str) -> Opportunities | None:
        """
        Fetch all opportunities associated with a specific user
        """
        query = text("""
            SELECT
                user_unique_id,
                partner_name,
                partner_type,
                partner_offers_json,
                partner_offer_criteria_json
            FROM Users_Opportunities.partners
            WHERE user_unique_id = :user_id
            AND partner_name = :partner_name
        """)

        row = self.db.execute(
            query,
            {
                "user_id": user_id,
                "partner_name": partner_name,
            },
        ).mappings().first()

        if row is None:
            return None

        return self._row_to_opportunity(row)

    @override
    def get_all_opportunities(self) -> list[Opportunities]:
        """
        Fetch all opportunities from the database
        """
        query = text("""
            SELECT
                user_unique_id,
                partner_name,
                partner_type,
                partner_offers_json,
                partner_offer_criteria_json
            FROM Users_Opportunities.partners
        """)

        rows = self.db.execute(query).mappings().all()

        return [self._row_to_opportunity(row) for row in rows]
    
    @override
    def create_opportunity(self, opportunity: Opportunities) -> Opportunities:
        """
        Create a new opportunity
        """
        query = text("""
            INSERT INTO Users_Opportunities.partners
            (
                user_unique_id,
                partner_name,
                partner_type,
                partner_offers_json,
                partner_offer_criteria_json
            )
            VALUES
            (
                :user_id,
                :partner_name,
                :partner_type,
                :partner_offers,
                :partner_criteria
            )
        """)

        try:
            self.db.execute(
                query,
                {
                    "user_id": opportunity.user_id,
                    "partner_name": opportunity.partner_name,
                    "partner_type": opportunity.partner_type,
                    "partner_offers": self._serialize_json(
                        opportunity.partner_offers
                    ),
                    "partner_criteria": self._serialize_json(
                        opportunity.partner_criteria
                    ),
                },
            )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        result = self.get_opportunity_for_user(
            opportunity.user_id,
            opportunity.partner_name,
        )

        if result is None:
            raise RuntimeError(
                "Opportunity was not found after creation"
            )

        return result

    @override
    def update_opportunity(self, opportunity: Opportunities) -> Opportunities:
        """
        Update an opportunity
        """
        query = text("""
            UPDATE Users_Opportunities.partners
            SET
                partner_name = :partner_name,
                partner_type = :partner_type,
                partner_offers_json = :partner_offers,
                partner_offer_criteria_json = :partner_criteria
            WHERE user_unique_id = :user_id
            AND partner_name = :partner_name
        """)

        try:
            result = self.db.execute(
                query,
                {
                    "user_id": opportunity.user_id,
                    "partner_name": opportunity.partner_name,
                    "partner_type": opportunity.partner_type,
                    "partner_offers": self._serialize_json(
                        opportunity.partner_offers
                    ),
                    "partner_criteria": self._serialize_json(
                        opportunity.partner_criteria
                    ),
                },
            )

            if result.rowcount == 0:
                self.db.rollback()
                raise ValueError(
                    "Opportunity was not found"
                )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        result = self.get_opportunity_for_user(
            opportunity.user_id,
            opportunity.partner_name,
        )

        if result is None:
            raise RuntimeError(
                "Opportunity was not found after update"
            )

        return result

    @override
    def update_partial_opportunity(self, opportunity: Opportunities, fields: dict) -> Opportunities:
        """
        Update only the allowed fields of an opportunity
        """
        field_mapping = {
            "partner_name": "partner_name",
            "partner_type": "partner_type",
            "partner_offers": "partner_offers_json",
            "partner_criteria": (
                "partner_offer_criteria_json"
            ),
        }

        invalid_fields = set(fields) - set(field_mapping)

        if invalid_fields:
            raise ValueError(
                f"Unsupported fields: {invalid_fields}"
            )

        if not fields:
            result = self.get_opportunity_for_user(
                opportunity.user_id,
                opportunity.partner_name,
            )

            if result is None:
                raise ValueError(
                    "Opportunity was not found"
                )

            return result

        values = {"user_id": opportunity.user_id}

        sql_fields = []

        for domain_field, value in fields.items():
            database_field = field_mapping[domain_field]
            parameter_name = f"value_{domain_field}"

            sql_fields.append(
                f"{database_field} = :{parameter_name}"
            )

            if domain_field in {"partner_offers", "partner_criteria"}:
                value = self._serialize_json(value)

            values[parameter_name] = value

        set_clause = ", ".join(sql_fields)

        query = text(f"""
            UPDATE Users_Opportunities.partners
            SET {set_clause}
            WHERE user_unique_id = :user_id
            AND partner_name = :partner_name
        """)

        try:
            values["partner_name"] = opportunity.partner_name
            result = self.db.execute(query, values)

            if result.rowcount == 0:
                self.db.rollback()
                raise ValueError(
                    "Opportunity was not found"
                )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        result = self.get_opportunity_for_user(
            opportunity.user_id,
            fields.get("partner_name", opportunity.partner_name),
        )

        if result is None:
            raise RuntimeError(
                "Opportunity was not found after update"
            )

        return result

    @override
    def delete_opportunity(self, user_id: str, partner_name: str) -> None:
        """
        Delete an opportunity
        """
        query = text("""
            DELETE FROM Users_Opportunities.partners
            WHERE user_unique_id = :user_id
            AND partner_name = :partner_name
        """)

        try:
            result = self.db.execute(
                query,
                {"user_id": user_id, "partner_name": partner_name},
            )

            if result.rowcount == 0:
                self.db.rollback()
                raise ValueError(
                    "Opportunity was not found"
                )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

    @override
    def delete_user_opportunities(self, user_id: str) -> None:
        """
        Delete all opportunities belonging to a user
        """
        query = text("""
            DELETE FROM Users_Opportunities.partners
            WHERE user_unique_id = :user_id
        """)

        try:
            self.db.execute(
                query,
                {"user_id": user_id},
            )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise
