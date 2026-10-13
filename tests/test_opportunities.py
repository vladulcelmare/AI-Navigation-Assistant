import pytest
from fastapi.testclient import TestClient

from backend.dependencies import get_current_user_id
from backend.main import app
from backend.models.opportunities import Opportunities
from backend.routers.opportunities import get_opportunity_repository

OPPORTUNITY = Opportunities(
    user_id="user-1",
    partner_name="Enel X Charging Station",
    partner_type="charging_station",
    partner_offers={"discount_percent": 10},
    partner_criteria={"engine_type": "Electric"},
)


class OpportunityRepositoryStub:
    def get_opportunities_for_user(self, user_id: str) -> list[Opportunities]:
        return [OPPORTUNITY] if user_id == OPPORTUNITY.user_id else []

    def get_opportunity_for_user(
        self,
        user_id: str,
        partner_name: str,
    ) -> Opportunities | None:
        if user_id == OPPORTUNITY.user_id and partner_name == OPPORTUNITY.partner_name:
            return OPPORTUNITY
        return None


@pytest.fixture(autouse=True)
def dependencies():
    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    app.dependency_overrides[get_opportunity_repository] = (
        lambda: OpportunityRepositoryStub()
    )
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


def test_authenticated_user_lists_own_opportunities() -> None:
    response = client.get("/opportunities")

    assert response.status_code == 200
    assert response.json()[0]["partner_name"] == OPPORTUNITY.partner_name


def test_unknown_opportunity_is_not_found() -> None:
    response = client.get("/opportunities/Unknown Partner")

    assert response.status_code == 404
