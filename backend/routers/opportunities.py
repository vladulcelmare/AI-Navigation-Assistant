from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, status

from backend.dependencies import get_current_user_id, get_opportunity_repository
from backend.models.opportunities import Opportunities
from backend.repositories.opportunities import (
    SqlOpportunityRepository,
)
from backend.schemas.opportunities import (
    OpportunityCreateInput,
    OpportunityOutput,
    OpportunityUpdateInput,
)

router = APIRouter(prefix="/opportunities", tags=["Opportunities"])


def _to_response(opportunity: Opportunities) -> OpportunityOutput:
    return OpportunityOutput(
        user_id = opportunity.user_id,
        partner_name = opportunity.partner_name,
        partner_type = opportunity.partner_type,
        partner_offers = opportunity.partner_offers,
        partner_criteria = opportunity.partner_criteria,
    )


@router.post("", response_model = OpportunityOutput, status_code = status.HTTP_201_CREATED)
def create_opportunity(payload: OpportunityCreateInput, current_user_id: Annotated[str, Depends(get_current_user_id)],
                       repository: Annotated[SqlOpportunityRepository, Depends(get_opportunity_repository)]) -> OpportunityOutput:
    
    opportunity = repository.create_opportunity(
        Opportunities(
            user_id=current_user_id,
            partner_name=payload.partner_name,
            partner_type=payload.partner_type,
            partner_offers=payload.partner_offers,
            partner_criteria=payload.partner_criteria,
        )
    )
    
    return _to_response(opportunity)


@router.get("", response_model = list[OpportunityOutput], status_code = status.HTTP_200_OK)
def list_my_opportunities(current_user_id: Annotated[str, Depends(get_current_user_id)],
                          repository: Annotated[SqlOpportunityRepository,
                          Depends(get_opportunity_repository)]) -> list[OpportunityOutput]:
    
    opportunities = repository.get_opportunities_for_user(current_user_id)

    return [_to_response(opportunity) for opportunity in opportunities]


@router.get("/{partner_name}", response_model = OpportunityOutput, status_code = status.HTTP_200_OK)
def get_my_opportunity(partner_name: Annotated[str, Path(min_length=1, max_length=128)],
                       current_user_id: Annotated[str, Depends(get_current_user_id)],
                       repository: Annotated[SqlOpportunityRepository, Depends(get_opportunity_repository)]) -> OpportunityOutput:
    
    opportunity = repository.get_opportunity_for_user(
        current_user_id,
        partner_name,
    )

    if opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )

    return _to_response(opportunity)


@router.patch("/{partner_name}", response_model = OpportunityOutput, status_code = status.HTTP_200_OK)
def update_opportunity(partner_name: Annotated[str, Path(min_length=1, max_length=128)],
                       payload: OpportunityUpdateInput,
                       current_user_id: Annotated[str, Depends(get_current_user_id)],
                       repository: Annotated[SqlOpportunityRepository, Depends(get_opportunity_repository)]) -> OpportunityOutput:
    
    existing = repository.get_opportunity_for_user(current_user_id, partner_name)

    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )

    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )
    
    updated = repository.update_partial_opportunity(existing, fields)
    return _to_response(updated)


@router.delete("/{partner_name}", status_code = status.HTTP_204_NO_CONTENT)
def delete_opportunity(partner_name: Annotated[str, Path(min_length=1, max_length=128)],
                       current_user_id: Annotated[str, Depends(get_current_user_id)],
                       repository: Annotated[SqlOpportunityRepository, Depends(get_opportunity_repository)]) -> None:
    
    try:
        repository.delete_opportunity(current_user_id, partner_name)

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error