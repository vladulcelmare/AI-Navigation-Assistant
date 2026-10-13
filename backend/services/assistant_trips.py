"""Backend context, route proposals and explicit acceptance of a proposal."""
from dataclasses import asdict
from datetime import UTC, datetime
import math
from uuid import uuid4

from fastapi import HTTPException

from backend import config
from backend.integrations.routing_client import Coordinates, GeoapifyClient
from backend.models.trips import Location, Route, Trip, TripStatus
from backend.models.vehicles import EngineType
from backend.repositories.conversations import SqlConversationRepository
from backend.repositories.opportunities import SqlOpportunityRepository
from backend.repositories.trips import SqlTripRepository
from backend.repositories.users import SqlUserRepository
from backend.repositories.vehicles import SqlVehicleRepository
from backend.services.partner_route_recommendation import choose_partner_route
from backend.services.route_recommendation import recommend_route
from backend.services.route_segmentation import haversine_distance_km, normalize_geometry_points
from backend.services.stop_recommendation import recommend_stops
from backend.services.station_recommendation import add_stations_to_stop_plan


def load_route_context(user_id, vehicle_id, current_location, db):
    vehicles = SqlVehicleRepository(db)

    if vehicle_id:
        vehicle = vehicles.get_vehicle_by_id(vehicle_id)

        if vehicle is None or vehicle.owner_id != user_id:
            raise HTTPException(404, "Vehicle not found")
    else:
        owned = vehicles.get_vehicle_by_owner_id(user_id)

        if len(owned) != 1:
            return {"error": "Select a vehicle before requesting a route"}

        vehicle = owned[0]

    user = SqlUserRepository(db).get_user_by_id(user_id)
    opportunities = SqlOpportunityRepository(db).get_opportunities_for_user(user_id)

    if user is None or user.preferences is None:
        return {"error": "Configure user preferences before requesting a route"}

    if vehicle.telemetry is None or vehicle.telemetry.avg_consumption <= 0:
        return {"error": "Update the vehicle consumption before requesting a route"}

    electric = vehicle.engine_type == EngineType.ELECTRIC
    price = config.ELECTRICITY_PRICE if electric else config.FUEL_PRICE

    if not math.isfinite(price) or price <= 0:
        return {"error": "Configure ELECTRICITY_PRICE or FUEL_PRICE in the backend"}

    active = [
        trip
        for trip in SqlTripRepository(db).get_trips_by_user_id(user_id)
        if trip.vehicle_id == vehicle.vehicle_id
        and trip.status in (TripStatus.PLANNED, TripStatus.IN_PROGRESS)
    ]

    location = current_location
    preference = user.preferences
    roads = preference.road_conditions

    return {
        "vehicle_id": vehicle.vehicle_id,
        "trip_id": active[0].trip_id if active else None,
        "parameters": {
            "engine_type": "Electric" if electric else "Internal_Combustion",
            "avg_consumption": vehicle.telemetry.avg_consumption,
            "total_capacity": vehicle.total_capacity,
            "current_level_percent": vehicle.telemetry.current_fuel,
            "fuel_price": config.FUEL_PRICE if not electric else 0,
            "electricity_price": config.ELECTRICITY_PRICE if electric else 0,
            "partner_opportunities": [
                {
                    "partner_name": item.partner_name,
                    "partner_type": item.partner_type,
                    "partner_offers": item.partner_offers,
                    "partner_criteria": item.partner_criteria,
                }
                for item in opportunities
            ],
            "preferences": {
                "age_group": preference.age_group,
                "driver_type": preference.driver_type.value,
                "road_conditions": (roads[0].value if len(roads) == 1 else "mixed"),
                "tolls": preference.tolls,
            },
            "origin_coordinates": ({"latitude": location.latitude, "longitude": location.longitude} if location else None),
        },
    }


def selected_route(segments):
    points = []
    for segment in segments:
        geometry = normalize_geometry_points(segment["geometry"])
        if len(geometry) < 2:
            raise HTTPException(502, "Route segment has no usable geometry")
        if points and haversine_distance_km(points[-1], geometry[0]) > 0.25:
            raise HTTPException(502, "Route segments are not connected")

        points.extend(geometry[1:] if points and points[-1] == geometry[0] else geometry)

    return Route(sum(segment["distance_km"] for segment in segments),
                sum(segment["distance_min"] for segment in segments),
                [Location(latitude=lat, longitude=lon) for lon, lat in points])


async def make_recommendation(result, selected, context):
    route = selected_route(selected)
    parameters = context["parameters"]

    stop_plan = recommend_stops(
        [segment["geometry"] for segment in selected],
        engine_type=parameters["engine_type"],
        total_capacity=parameters["total_capacity"],
        current_level_percent=parameters["current_level_percent"],
        avg_consumption=parameters["avg_consumption"],
    )

    stop_plan = await add_stations_to_stop_plan(stop_plan, parameters["engine_type"], parameters.get("partner_opportunities", []))
    partner_route = None
    if stop_plan.get("stop_count", 0) > 0:
        origin = Coordinates(latitude=result["origin_coordinates"]["latitude"], longitude=result["origin_coordinates"]["longitude"],)
        destination = Coordinates(latitude=result["destination_coordinates"]["latitude"], longitude=result["destination_coordinates"]["longitude"],)
        partner_route = await choose_partner_route(
            GeoapifyClient(),
            origin=origin,
            destination=destination,
            base_route=route,
            stop_plan=stop_plan,
            engine_type=parameters["engine_type"],
            avoid_tolls=not parameters["preferences"]["tolls"],
        )
        if partner_route:
            route = partner_route["route"]

    return {
        "recommendation_id": str(uuid4()),
        "vehicle_id": context["vehicle_id"],
        "trip_id": context["trip_id"],
        "created_at": datetime.now(UTC).isoformat(),
        "uses_current_location": (parameters["origin_coordinates"] is not None),
        "origin": result["origin_coordinates"],
        "destination": result["destination_coordinates"],
        "origin_name": result["origin"],
        "destination_name": result["destination"],
        "segments": result["routes"],
        "choices": {str(segment["qid"]): segment["route_index"] for segment in selected},
        "route": asdict(route),
        "stop_recommendations": stop_plan,
        "partner_route": (
            {
                "route": asdict(partner_route["route"]),
                "station": partner_route["station"],
                "detour_distance_km": partner_route["detour_distance_km"],
                "detour_minutes": partner_route["detour_minutes"],
            }
            if partner_route
            else None
        ),
        "cost_per_km": selected[0]["cost_per_km"],
    }


def describe_recommendation(proposal):
    route = proposal["route"]
    stop_plan = proposal.get("stop_recommendations",{})
    stops = stop_plan.get("stops", [])
    if not stops:
        stop_message = ("Nu sunt necesare opriri pentru alimentare.")
    else:
        stop_lines = []
        for stop in stops:
            distance = stop.get("distance_from_origin_km", 0)
            stations = stop.get("stations", [])
            partner_stations = [station for station in stations if station.get("partner_opportunity")]

            if not partner_stations:
                stop_lines.append(f"Oprire la km {distance:.0f}; " "nu a fost găsit un partener eligibil.")
                continue

            station = partner_stations[0]
            opportunity = station["partner_opportunity"]
            offer = opportunity.get("partner_offers", {})
            discount_type = offer.get("discount_type")
            if discount_type == "percent":
                offer_text = (f"{offer.get('discount_percent', 0)}% " "reducere la carburant sau energie")
            elif discount_type == "per_liter":
                offer_text = (f"{offer.get('discount_value', 0):.2f} RON " "reducere per litru")
            elif discount_type == "per_kwh":
                offer_text = (f"{offer.get('discount_value', 0):.2f} RON " "reducere per kWh")
            else:
                offer_text = offer.get("title","ofertă disponibilă",)

            stop_lines.append(
                f"Oprire la km {distance:.0f}, "
                f"la {station.get('name', 'stația parteneră')}, "
                f"cu oferta: {offer_text}."
            )

        stop_message = " ".join(stop_lines)

    partner_route = proposal.get("partner_route")

    if partner_route:
        partner_message = (
            "Ruta trece printr-un partener și adaugă "
            f"aproximativ "
            f"{partner_route.get('detour_minutes', 0):.0f} minute."
        )
    else:
        partner_message = ""

    return (
        f"Îți recomand traseul către "
        f"{proposal['destination_name']}: "
        f"{route['distance_km']:.1f} km și "
        f"{route['duration_minutes']:.0f} minute. "
        f"{stop_message} "
        f"{partner_message}"
    )


async def accept_recommendation(user_id, conversation_id, recommendation_id, choices, current_location, db):
    conversations = SqlConversationRepository(db)
    conversation = conversations.load_user_conversation(user_id, conversation_id)

    if conversation is None:
        raise HTTPException(404, "Conversation not found")

    proposal = next(( item for item in conversation.recommendations
                        if item["recommendation_id"] == recommendation_id), None)

    if proposal is None:
        raise HTTPException(404, "Recommendation not found; use the latest recommendation")

    try:
        vehicles = SqlVehicleRepository(db)
        vehicle = vehicles.get_vehicle_by_id(proposal["vehicle_id"], lock=True)

        if vehicle is None or vehicle.owner_id != user_id:
            raise HTTPException(404, "Vehicle not found")
        conversation = conversations.load_user_conversation(user_id,conversation_id)
        proposal = next((item for item in conversation.recommendations
                            if item["recommendation_id"] == recommendation_id), None)

        if proposal is None:
            raise HTTPException(409, "Recommendation was replaced; request a new one")
        trips = SqlTripRepository(db)
        if proposal.get("accepted_trip_id"):
            return trips.get_trip_by_id(proposal["accepted_trip_id"])

        origin = Location(**proposal["origin"])
        if proposal["uses_current_location"] or proposal["trip_id"]:
            current = (current_location.model_dump() if current_location else None)

            if current is None or haversine_distance_km([origin.longitude, origin.latitude],[current["longitude"], current["latitude"]]) > 0.25:
                raise HTTPException(409,"Location changed or expired; request a new recommendation")

        options = {segment[0]["qid"]: segment for segment in proposal["segments"]}
        if set(choices) - options.keys():
            raise HTTPException(422, "Unknown segment")

        selected = []
        for qid, alternatives in options.items():
            index = choices.get(qid, proposal["choices"][str(qid)])
            chosen = next((route for route in alternatives if route["route_index"] == index), None)
            if chosen is None:
                raise HTTPException(422, "Unknown route alternative")
            selected.append(chosen)
        partner_route = None
        if proposal.get("partner_route") and not choices:
            saved_route = proposal["partner_route"]["route"]
            route = Route(
                distance_km=saved_route["distance_km"],
                duration_minutes=saved_route["duration_minutes"],
                geometry=[Location(**point) for point in saved_route["geometry"]],
            )

            stop_plan = proposal.get("stop_recommendations", {})
        else:
            route = selected_route(selected)
            opportunities = SqlOpportunityRepository(db).get_opportunities_for_user(user_id)

            partner_opportunities = [
                {
                    "partner_name": item.partner_name,
                    "partner_type": item.partner_type,
                    "partner_offers": item.partner_offers,
                    "partner_criteria": item.partner_criteria,
                }
                for item in opportunities
            ]

            stop_plan = recommend_stops(
                [segment["geometry"] for segment in selected],
                engine_type=vehicle.engine_type.value,
                total_capacity=vehicle.total_capacity,
                current_level_percent=vehicle.telemetry.current_fuel,
                avg_consumption=vehicle.telemetry.avg_consumption,
            )

            stop_plan = await add_stations_to_stop_plan(stop_plan, vehicle.engine_type.value, partner_opportunities)
            if stop_plan.get("stop_count", 0) > 0:
                partner_route = await choose_partner_route(
                    GeoapifyClient(),
                    origin=Coordinates(
                        latitude=proposal["origin"]["latitude"],
                        longitude=proposal["origin"]["longitude"],
                    ),
                    destination=Coordinates(
                        latitude=proposal["destination"]["latitude"],
                        longitude=proposal["destination"]["longitude"],
                    ),
                    base_route=route,
                    stop_plan=stop_plan,
                    engine_type=vehicle.engine_type.value,
                    avoid_tolls=False,
                )

                if partner_route:
                    route = partner_route["route"]

        if proposal["trip_id"]:
            trip = trips.get_trip_by_id(proposal["trip_id"])
            if (trip is None or trip.user_id != user_id or trip.vehicle_id != vehicle.vehicle_id):
                raise HTTPException(404, "Trip not found")
            if trip.status not in (TripStatus.PLANNED, TripStatus.IN_PROGRESS):
                raise HTTPException(409, "Trip is already finished")

            trip.route = route
            trip.route_options = [route]
            trip.route_origin = origin
            trip.destination = Location(**proposal["destination"])
            trip.cost_per_km = proposal["cost_per_km"]
            trip = trips.update_trip(trip, commit=False)
        else:
            if trips.has_active_trip_for_vehicle(vehicle.vehicle_id):
                raise HTTPException(409, "Vehicle already has a trip; request a new recommendation")

            trip = Trip(
                user_id,
                vehicle.vehicle_id,
                recommendation_id,
                datetime.now(UTC),
                origin,
                Location(**proposal["destination"]),
                route,
                proposal["cost_per_km"],
                route_options=[route],
                route_origin=origin,
            )

            trip = trips.create_trip(trip, commit=False)
        proposal["accepted_trip_id"] = trip.trip_id
        proposal["choices"] = {str(segment["qid"]): segment["route_index"] for segment in selected}
        proposal["route"] = asdict(route)
        proposal["stop_recommendations"] = stop_plan
        proposal["partner_route"] = (
            {
                "route": asdict(partner_route["route"]),
                "station": partner_route["station"],
                "detour_distance_km": partner_route[
                    "detour_distance_km"
                ],
                "detour_minutes": partner_route[
                    "detour_minutes"
                ],
            }
            if partner_route
            else proposal.get("partner_route")
        )
        conversations.save_recommendations(user_id, conversation_id, conversation.recommendations)
        return trip
    except Exception:
        db.rollback()
        raise


async def recalculate_trip(user_id, trip_id, current_location, db):
    trips = SqlTripRepository(db)
    trip = trips.get_trip_by_id(trip_id)
    if trip is None:
        raise HTTPException(404, "Trip not found")

    if trip.user_id != user_id:
        raise HTTPException(403, "You do not have access to this trip")

    if trip.status not in (TripStatus.PLANNED, TripStatus.IN_PROGRESS):
        raise HTTPException(409, "Only active trips can be recalculated")
    current_point = [current_location.longitude,current_location.latitude]

    route_points = [[point.longitude, point.latitude] for point in trip.route.geometry]
    distance_from_route = min(
        haversine_distance_km(current_point,route_point)
        for route_point in route_points
    )

    if distance_from_route < 0.1:
        raise HTTPException(409, "Vehicle is still on the current route")
    context = load_route_context(user_id, trip.vehicle_id, current_location, db)
    if context.get("error"):
        raise HTTPException(422, context["error"])

    result = await recommend_route(
        origin_name="Current location",
        destination_name="Current destination",
        destination_coordinates={
            "latitude": trip.destination.latitude,
            "longitude": trip.destination.longitude,
        },
        **context["parameters"],
    )

    selected = [alternatives[0] for alternatives in result["routes"] if alternatives]
    if not selected:
        raise HTTPException(502, "No route alternatives were returned")

    context["trip_id"] = trip.trip_id
    recommendation = await make_recommendation(result, selected, context)
    route_data = recommendation["route"]
    route = Route(
        distance_km=route_data["distance_km"],
        duration_minutes=route_data["duration_minutes"],
        geometry=[Location(**point) for point in route_data["geometry"]],
    )

    trip.route = route
    trip.route_options = [route]
    trip.route_origin = Location(
        latitude=current_location.latitude,
        longitude=current_location.longitude,
    )

    trips.update_trip(trip)
    return {
        "trip": trip,
        "stop_recommendations": recommendation["stop_recommendations"],
        "partner_route": recommendation["partner_route"],
    }