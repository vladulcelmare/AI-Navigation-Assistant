from pydantic import BaseModel, Field


class OpportunityOutput(BaseModel):
    user_id: str
    partner_name: str = Field(min_length=1)
    partner_type: str = Field(min_length=1)
    partner_offers: dict
    partner_criteria: dict


class OpportunityCreateInput(BaseModel):
    partner_name: str = Field(min_length=1, max_length=128)
    partner_type: str = Field(min_length=1, max_length=128)
    partner_offers: dict
    partner_criteria: dict


class OpportunityUpdateInput(BaseModel):
    partner_name: str | None = Field(default=None, min_length=1, max_length=128)
    partner_type: str | None = Field(default=None, min_length=1, max_length=128)
    partner_offers: dict | None = None
    partner_criteria: dict | None = None
