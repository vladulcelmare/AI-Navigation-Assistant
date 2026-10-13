from typing import Annotated
from unittest import result
from fastapi import APIRouter, Depends, HTTPException, Path, status
from pytest import Session

from backend.database import get_db
from backend.dependencies import (
    get_current_user_id,
    get_trip_repository,
)
from backend.models.trips import  Route, Trip, TripStatus
from backend.repositories.trips import SqlTripRepository
from backend.schemas.trips import (
    LocationSchema,
    RouteOutput,
    TripOutput,
    TripRecalculateInput,
    TripRecalculateOutput,
    TripStatusChange,
)
from backend.services.assistant_trips import recalculate_trip

router = APIRouter(prefix="/trips", tags=["Trips"])


def _route_to_response(route: Route) -> RouteOutput:
    # Convert domain locations into the public Pydantic representation
    geometry = []
    for point in route.geometry:
        geometry.append(
            LocationSchema(
                latitude=point.latitude,
                longitude=point.longitude,
            )
        )

    return RouteOutput(distance_km=route.distance_km,
                       duration_minutes=route.duration_minutes,
                       geometry=geometry,
                       )


def _to_response(trip: Trip) -> TripOutput:
    route_options = []
    for route in trip.route_options or []:
        route_options.append(_route_to_response(route))

    return TripOutput(
        trip_id=trip.trip_id,
        user_id=trip.user_id,
        vehicle_id=trip.vehicle_id,
        created_at=trip.created_at,
        origin=LocationSchema(
            latitude=trip.origin.latitude,
            longitude=trip.origin.longitude,
        ),
        destination=LocationSchema(
            latitude=trip.destination.latitude,
            longitude=trip.destination.longitude,
        ),
        route=_route_to_response(trip.route),
        route_options=route_options,
        cost_per_km=trip.cost_per_km,
        status=trip.status,
        route_origin=LocationSchema(**vars(trip.route_origin or trip.origin)),
    )


@router.post("/{trip_id}/recalculate", response_model=TripRecalculateOutput)
async def recalculate_my_trip(trip_id: Annotated[str, Path(min_length=1, max_length=64)], payload: TripRecalculateInput,
    current_user_id: Annotated[str, Depends(get_current_user_id)], repository: Annotated[SqlTripRepository, Depends(get_trip_repository)],
    db: Annotated[Session, Depends(get_db)]) -> TripRecalculateOutput:
    result = await recalculate_trip(
        user_id=current_user_id,
        trip_id=trip_id,
        current_location=payload.current_location,
        db=db,
    )
    return TripRecalculateOutput(
        trip=_to_response(result["trip"]),
        stop_recommendations=result.get("stop_recommendations", {}),
        partner_route=result.get("partner_route"),
    )


@router.get("", response_model=list[TripOutput])
def get_my_trips(current_user_id: Annotated[str, Depends(get_current_user_id)],
                 repository: Annotated[SqlTripRepository, Depends(get_trip_repository)]) -> list[TripOutput]:
    
    return [
        _to_response(trip)
        for trip in repository.get_trips_by_user_id(current_user_id)
    ]


@router.get("/{trip_id}", response_model=TripOutput)
def get_trip(trip_id: Annotated[str, Path(min_length=1, max_length=64)],
             current_user_id: Annotated[str, Depends(get_current_user_id)],
             repository: Annotated[SqlTripRepository, Depends(get_trip_repository)]) -> TripOutput:

    trip = repository.get_trip_by_id(trip_id)

    # A valid trip ID is still restricted to the authenticated user's trips
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Trip not found"
        )

    if trip.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trip"
        )

    return _to_response(trip)

@router.patch("/{trip_id}/status", response_model=TripOutput)
def change_trip_status(trip_id: Annotated[str, Path(min_length=1, max_length=64)],
                       payload: TripStatusChange,
                       current_user_id: Annotated[str, Depends(get_current_user_id)],
                       repository: Annotated[SqlTripRepository, Depends(get_trip_repository)]) -> TripOutput:

    trip = repository.get_trip_by_id(trip_id)

    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Trip not found"
        )
    if trip.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trip"
        )

    transitions = {
        TripStatus.PLANNED: {TripStatus.IN_PROGRESS, TripStatus.CANCELLED},
        TripStatus.IN_PROGRESS: {TripStatus.COMPLETED, TripStatus.CANCELLED},
        TripStatus.COMPLETED: set(),
        TripStatus.CANCELLED: set(),
    }
    if payload.status != trip.status and payload.status not in transitions[trip.status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid trip status transition"
        )

    trip.status = payload.status
    repository.update_trip(trip)
    return _to_response(trip)
