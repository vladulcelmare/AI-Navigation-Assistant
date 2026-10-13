from dataclasses import dataclass


@dataclass
class Opportunities:
    """
    Represents opportunity entity from db
    """
    user_id: str
    partner_name: str
    partner_type: str
    partner_offers: dict
    partner_criteria: dict