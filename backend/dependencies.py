from typing import Annotated
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.integrations.routing_client import GeoapifyClient
from backend.repositories.opportunities import SqlOpportunityRepository
from backend.repositories.trips import SqlTripRepository
from backend.repositories.vehicles import SqlVehicleRepository
from backend.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


# Decode the JWT and return the authenticated user's ID.
def get_current_user_id(
	credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
	credentials_exception = HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail="Could not validate credentials",
		headers={"WWW-Authenticate": "Bearer"},
	)
	if credentials is None:
		raise credentials_exception
	try:
		return decode_access_token(credentials.credentials)
	except jwt.InvalidTokenError as error:
		raise credentials_exception from error


def get_trip_repository(db: Annotated[Session, Depends(get_db)]) -> SqlTripRepository:
	return SqlTripRepository(db)


def get_opportunity_repository(db: Annotated[Session, Depends(get_db)]) -> SqlOpportunityRepository:
	return SqlOpportunityRepository(db)

def get_vehicle_repository(db: Annotated[Session, Depends(get_db)]) -> SqlVehicleRepository:
	return SqlVehicleRepository(db)