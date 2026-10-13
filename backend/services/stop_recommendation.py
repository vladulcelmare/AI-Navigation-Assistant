from __future__ import annotations
from math import isfinite
from typing import Any
from backend.services.route_segmentation import (haversine_distance_km,normalize_geometry_points)

DEFAULT_RESERVE_PERCENT = 20.0


def _validate_inputs(*, total_capacity: float, current_level_percent: float, avg_consumption: float,
    reserve_percent: float) -> None:
    values = (total_capacity, current_level_percent, avg_consumption, reserve_percent)
    if not all(isfinite(value) for value in values):
        raise ValueError("Vehicle range values must be finite")
    if total_capacity <= 0:
        raise ValueError("Vehicle capacity must be greater than zero")
    if avg_consumption <= 0:
        raise ValueError("Vehicle consumption must be greater than zero")
    if not 0 <= current_level_percent <= 100:
        raise ValueError("Current fuel or battery level must be between 0 and 100 percent")
    if not 0 <= reserve_percent < 100:
        raise ValueError("Reserve percentage must be between 0 and 100 percent")


def _merge_route_points(route_geometry: list[dict[str, Any]]) -> list[list[float]]:
    points: list[list[float]] = []
    for geometry in route_geometry:
        segment_points = normalize_geometry_points(geometry)
        if len(segment_points) < 2:
            continue
        if points and points[-1] == segment_points[0]:
            points.extend(segment_points[1:])
        else:
            points.extend(segment_points)

    if len(points) < 2:
        raise ValueError("Route geometry must contain at least two usable points")
    return points


def _calculate_route_distance_km(points: list[list[float]]) -> float:
    return sum(haversine_distance_km(start, end) for start, end in zip(points, points[1:]))

def _point_at_distance(points: list[list[float]], target_distance_km: float) -> list[float]:
    travelled_km = 0.0

    for start, end in zip(points, points[1:]):
        segment_distance_km = haversine_distance_km(start, end)
        if segment_distance_km <= 0:
            continue
        if travelled_km + segment_distance_km >= target_distance_km:
            remaining_km = target_distance_km - travelled_km
            ratio = remaining_km / segment_distance_km
            longitude = start[0] + (end[0] - start[0]) * ratio
            latitude = start[1] + (end[1] - start[1]) * ratio
            return [longitude, latitude]
        travelled_km += segment_distance_km
    return list(points[-1])


def recommend_stops(route_geometry: list[dict[str, Any]], *, engine_type: str, total_capacity: float,
    current_level_percent: float, avg_consumption: float, reserve_percent: float = DEFAULT_RESERVE_PERCENT,
) -> dict[str, Any]:
    _validate_inputs(
        total_capacity=total_capacity,
        current_level_percent=current_level_percent,
        avg_consumption=avg_consumption,
        reserve_percent=reserve_percent,
    )
    points = _merge_route_points(route_geometry)
    route_distance_km = _calculate_route_distance_km(points)
    available_energy = (total_capacity * current_level_percent / 100)
    initial_range_km = (available_energy / avg_consumption) * 100
    reserve_factor = (100 - reserve_percent) / 100
    safe_initial_range_km = (initial_range_km * reserve_factor)
    full_capacity_safe_range_km = (total_capacity / avg_consumption) * 100 * reserve_factor
    is_electric = engine_type.casefold() == "electric"
    stop_type = "charging" if is_electric else "refueling"
    stops: list[dict[str, Any]] = []
    next_stop_distance_km = safe_initial_range_km
    stop_number = 1
    while next_stop_distance_km < route_distance_km:
        longitude, latitude = _point_at_distance(points, next_stop_distance_km)
        stops.append({
            "stop_number": stop_number,
            "type": stop_type,
            "distance_from_origin_km": round(next_stop_distance_km, 1),
            "location": {"latitude": round(latitude, 6), "longitude": round(longitude, 6)},
            "reason": (
                "The route exceeds the vehicle safe range "
                "with the current fuel or battery level."
            ),
        })

        stop_number += 1
        next_stop_distance_km += full_capacity_safe_range_km

    return {
        "route_distance_km": round(route_distance_km, 1),
        "initial_range_km": round(initial_range_km, 1),
        "safe_range_km": round(safe_initial_range_km, 1),
        "full_capacity_safe_range_km": round(full_capacity_safe_range_km, 1),
        "reserve_percent": reserve_percent,
        "stop_count": len(stops),
        "destination_reachable": len(stops) == 0,
        "energy_type": "battery" if is_electric else "fuel",
        "stops": stops,
    }