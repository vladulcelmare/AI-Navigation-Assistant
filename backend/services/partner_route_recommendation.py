from __future__ import annotations
from typing import Any
from backend.integrations.routing_client import (Coordinates, GeoapifyClient)
from backend.models.trips import Route

MAX_PARTNER_DETOUR_KM = 5.0
MAX_PARTNER_DETOUR_MINUTES = 10.0

def _offer_score(station: dict[str, Any]) -> float:
    offer = (station.get("partner_opportunity") or {}).get("partner_offers", {})
    discount = float(offer.get("discount_percent", 0))
    points = float(offer.get("reward_points", 0))
    return discount * 2 + points * 0.1


async def choose_partner_route(client: GeoapifyClient, *, origin: Coordinates, destination: Coordinates,
    base_route: Route, stop_plan: dict[str, Any], engine_type: str, avoid_tolls: bool) -> dict[str, Any] | None:
    
    stops = stop_plan.get("stops", [])
    if not stops:
        return None
    best_option = None
    for stop in stops:
        stations = [station for station in stop.get("stations", []) if station.get("partner_opportunity")]
        for station in stations:
            location = station["location"]
            via = Coordinates(latitude=float(location["latitude"]), longitude=float(location["longitude"]))
            candidates = await client.get_route_candidates(
                origin,
                destination,
                via=via,
                alternatives=1,
                avoid_tolls=avoid_tolls,
            )

            if not candidates:
                continue
            candidate = candidates[0]
            detour_km = (candidate.distance_km - base_route.distance_km)
            detour_minutes = (candidate.duration_min - base_route.duration_minutes)
            if detour_km < 0:
                detour_km = 0
            if detour_minutes < 0:
                detour_minutes = 0
            if detour_km > MAX_PARTNER_DETOUR_KM:
                continue
            if detour_minutes > MAX_PARTNER_DETOUR_MINUTES:
                continue
            score = (_offer_score(station) - detour_km * 2 - detour_minutes * 1.5)

            if best_option is None or score > best_option["score"]:
                partner_route = client._to_route(candidate)
                best_option = {
                    "score": score,
                    "route": partner_route,
                    "station": station,
                    "detour_distance_km": round(detour_km, 2),
                    "detour_minutes": round(detour_minutes, 2),
                }

    return best_option