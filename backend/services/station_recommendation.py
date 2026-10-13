from __future__ import annotations
from typing import Any
from backend.integrations.routing_client import GeoapifyClient


def station_matches_opportunity(station: dict[str, Any], opportunity: dict[str, Any],engine_type: str) -> bool:
    station_name = station.get("name", "").casefold()
    partner_name = opportunity.get("partner_name", "").casefold()
    criteria = opportunity.get("partner_criteria", {})

    if partner_name not in station_name:
        return False
    required_type = criteria.get("station_type")
    if required_type and station.get("type") != required_type:
        return False
    allowed_engines = criteria.get("engine_types", [])
    if allowed_engines and engine_type not in allowed_engines:
        return False
    return True


def attach_partner_opportunity(station: dict[str, Any], opportunities: list[dict[str, Any]], engine_type: str) -> dict[str, Any]:
    station["partner_opportunity"] = None
    for opportunity in opportunities:
        if station_matches_opportunity(station, opportunity, engine_type):
            station["partner_opportunity"] = opportunity
            break
    return station


async def add_stations_to_stop_plan(stop_plan: dict[str, Any], engine_type: str, opportunities: list[dict[str, Any]], *, radius_m: int = 5000, limit: int = 5) -> dict[str, Any]:
    stops = stop_plan.get("stops", [])
    if not stops:
        return stop_plan

    client = GeoapifyClient()
    electric = engine_type.casefold() == "electric"

    for stop in stops:
        location = stop.get("location")
        if not location:
            stop["stations"] = []
            continue
        stations = await client.find_stations_near_point(
            latitude=float(location["latitude"]),
            longitude=float(location["longitude"]),
            electric=electric,
            radius_m=radius_m,
            limit=limit,
        )
        stop["stations"] = [attach_partner_opportunity(station, opportunities, engine_type.casefold()) for station in stations]
    return stop_plan