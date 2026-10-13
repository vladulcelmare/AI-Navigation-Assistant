from types import SimpleNamespace
from unittest.mock import Mock
import asyncio
import json
import pytest
from fastapi import HTTPException
from backend.models.trips import Location, TripStatus
from backend.models.users import DriverType, RoadConditions
from backend.models.vehicles import EngineType
from backend.services import assistant_trips as service
from backend.services import vehicles as vehicle_service
from backend.schemas.vehicles import LocationSchema
from backend.repositories.trips import SqlTripRepository
from backend.tool_calling import call_tool


@pytest.fixture
def state(monkeypatch):
    vehicle = SimpleNamespace(vehicle_id="vehicle-1", owner_id="user-1", engine_type=EngineType.ELECTRIC,
                              total_capacity=75, telemetry=SimpleNamespace(avg_consumption=20, current_fuel=80))
    location = LocationSchema(latitude=44, longitude=26)
    vehicles = Mock()
    vehicles.get_vehicle_by_id.return_value = vehicle
    vehicles.get_vehicle_by_owner_id.return_value = [vehicle]
    users = Mock()
    users.get_user_by_id.return_value = SimpleNamespace(preferences=SimpleNamespace(
        road_conditions=[RoadConditions.HIGHWAY_ROADS], age_group="adult",
        driver_type=DriverType.CALM, tolls=False))
    trips = Mock()
    trips.get_trips_by_user_id.return_value = []
    trips.has_active_trip_for_vehicle.return_value = False
    saved = {}
    trips.create_trip.side_effect = lambda trip, **kwargs: saved.setdefault(trip.trip_id, trip)
    trips.update_trip.side_effect = lambda trip, **kwargs: trip
    trips.get_trip_by_id.side_effect = saved.get
    conversations = Mock()
    conversation = SimpleNamespace(recommendations=[])
    conversations.load_user_conversation.return_value = conversation
    for name, repository in [("SqlVehicleRepository", vehicles), ("SqlUserRepository", users),
                             ("SqlTripRepository", trips), ("SqlConversationRepository", conversations)]:
        monkeypatch.setattr(service, name, lambda db, repository=repository: repository)
    monkeypatch.setattr(vehicle_service, "SqlVehicleRepository", lambda db: vehicles)
    monkeypatch.setattr(service.config, "ELECTRICITY_PRICE", 1.0)
    monkeypatch.setattr(service.config, "FUEL_PRICE", 7.0)
    db = Mock()
    context = service.load_route_context("user-1", "vehicle-1", location, db)
    alternatives = [{"qid": 0, "route_index": index, "rank_score": 1 / index,
                     "distance_km": index * 2, "distance_min": index * 3, "cost_per_km": 0.2,
                     "geometry": {"type": "LineString", "coordinates": [[26, 44], [26.01, 44.01]]}}
                    for index in (1, 2)]
    result = {"origin": "Current location", "destination": "B",
              "origin_coordinates": {"latitude": 44, "longitude": 26},
              "destination_coordinates": {"latitude": 44.01, "longitude": 26.01},
              "routes": [alternatives]}
    proposal = service.make_recommendation(result, [alternatives[0]], context)
    conversation.recommendations = [proposal]
    return SimpleNamespace(vehicle=vehicle, vehicles=vehicles, users=users, trips=trips,
                           conversations=conversations, proposal=proposal, context=context,
                           location=location, saved=saved, db=db)


def accept(state, choices=None, current_location=None):
    return service.accept_recommendation("user-1", "conversation-1",
                                         state.proposal["recommendation_id"], choices or {},
                                         current_location or state.location, state.db)


def test_context_uses_database_preferences_and_telemetry(state):
    parameters = state.context["parameters"]
    assert parameters["engine_type"] == "Electric"
    assert parameters["avg_consumption"] == 20
    assert parameters["preferences"]["road_conditions"] == "highway_roads"
    assert parameters["preferences"]["tolls"] is False
    assert parameters["origin_coordinates"] == {"latitude": 44, "longitude": 26}


def test_vehicle_selection_and_ownership(state):
    state.vehicles.get_vehicle_by_owner_id.return_value = [state.vehicle, state.vehicle]
    assert "error" in service.load_route_context(
        "user-1", None, LocationSchema(latitude=44, longitude=26), state.db)
    state.vehicle.owner_id = "other-user"
    with pytest.raises(HTTPException) as error:
        service.load_route_context(
            "user-1", "vehicle-1", LocationSchema(latitude=44, longitude=26), state.db)
    assert error.value.status_code == 404


def test_tool_uses_frontend_location_not_llm_origin(state, monkeypatch):
    from unittest.mock import AsyncMock
    from backend import tool_calling
    routing = AsyncMock()
    monkeypatch.setattr(tool_calling, "recommend_route", routing)
    asyncio.run(call_tool("recommend_route",
                          {"origin_name": "Old departure", "destination_name": "B"}, state.context))
    assert routing.call_args.kwargs["origin_name"] == "Current location"
    assert routing.call_args.kwargs["origin_coordinates"] == {"latitude": 44, "longitude": 26}


def test_accept_saves_selected_geometry_and_is_idempotent(state):
    trip = accept(state, {0: 2})
    assert trip.route.distance_km == 4
    assert trip.route.geometry[-1] == Location(44.01, 26.01)
    assert trip.status == TripStatus.PLANNED
    assert accept(state).trip_id == trip.trip_id
    state.trips.create_trip.assert_called_once()
    assert state.trips.create_trip.call_args.kwargs == {"commit": False}
    state.conversations.save_recommendations.assert_called_once()


def test_switch_route_preserves_original_trip_origin(state):
    trip = accept(state)
    trip.origin = Location(43, 25)
    trip.status = TripStatus.IN_PROGRESS
    del state.proposal["accepted_trip_id"]
    state.proposal["trip_id"] = trip.trip_id
    state.proposal["destination"] = {"latitude": 44.02, "longitude": 26.02}
    for alternative in state.proposal["segments"][0]:
        alternative["geometry"]["coordinates"][-1] = [26.02, 44.02]
    updated = accept(state, {0: 2})
    assert updated.origin == Location(43, 25)
    assert updated.route_origin == Location(44, 26)
    assert updated.destination == Location(44.02, 26.02)
    assert updated.status == TripStatus.IN_PROGRESS
    state.trips.update_trip.assert_called_once()


def test_accept_rejects_moved_location(state):
    moved_location = LocationSchema(latitude=45, longitude=26)
    with pytest.raises(HTTPException) as error:
        accept(state, current_location=moved_location)
    assert error.value.status_code == 409
    state.trips.create_trip.assert_not_called()


@pytest.mark.parametrize("case", ["insufficient_range", "unknown_choice"])
def test_accept_rejects_invalid_state(state, case):
    if case == "insufficient_range":
        state.vehicle.telemetry.current_fuel = 0
    with pytest.raises(HTTPException):
        accept(state, {0: 999} if case == "unknown_choice" else {})
    state.trips.create_trip.assert_not_called()


def test_disconnected_segments_are_rejected(state):
    first = state.proposal["segments"][0][0]
    second = {**first, "geometry": {"type": "LineString", "coordinates": [[27, 45], [28, 46]]}}
    with pytest.raises(HTTPException, match="not connected"):
        service.selected_route([first, second])


def test_trip_update_serializes_route_and_destination(state, monkeypatch):
    trip = accept(state)
    repository = SqlTripRepository(state.db)
    monkeypatch.setattr(repository, "get_trip_by_id", lambda trip_id: trip)
    assert repository.update_trip(trip) is trip
    query, parameters = state.db.execute.call_args.args
    data = json.loads(parameters["route_json"])
    assert data["geometry"][0] == {"latitude": 44, "longitude": 26}
    assert len(data["routes"]) == 1
    assert data["route_origin"] == {"latitude": 44, "longitude": 26}
    assert "initial_location =" not in str(query)
    assert parameters["destination"] == "44.010000,26.010000"


def test_message_returns_and_persists_structured_recommendation(state, monkeypatch):
    from unittest.mock import AsyncMock
    from backend.services import conversations
    from backend.schemas.conversations import MessageLog
    conversation = state.conversations.load_user_conversation.return_value
    conversation.messages = []
    agent = SimpleNamespace(generate_response=AsyncMock(return_value=[(
        {"origin": "Current location", "destination": "B", "origin_coordinates": state.proposal["origin"],
         "destination_coordinates": state.proposal["destination"], "routes": state.proposal["segments"]},
        [state.proposal["segments"][0][0]])]))
    monkeypatch.setattr(conversations, "SqlConversationRepository", lambda db: state.conversations)
    monkeypatch.setattr(conversations, "LLM_Agent", lambda: agent)
    monkeypatch.setattr(conversations, "_load_trip_history", lambda user_id, db: [])
    reply = asyncio.run(conversations.log_my_message("conversation-1",
        MessageLog(content="Take me to B", vehicle_id="vehicle-1",
                   current_location=LocationSchema(latitude=44, longitude=26)), "user-1", state.db))
    assert "2.0 km" in reply.response
    assert reply.recommendations[0]["route"]["geometry"][-1] == {"latitude": 44.01, "longitude": 26.01}
    assert reply.recommendations[0]["recommendation_id"]
    state.conversations.save_recommendations.assert_called_once()
    state.trips.create_trip.assert_not_called()