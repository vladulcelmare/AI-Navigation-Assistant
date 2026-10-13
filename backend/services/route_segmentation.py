import json
from dataclasses import dataclass
from itertools import pairwise
from math import atan2, cos, radians, sin, sqrt
from typing import Any


@dataclass
class RouteSegment:
    segment_index: int
    points: list[list[float]]
    distance_km: float

    @property
    def start_point(self) -> list[float]:
        return self.points[0]

    @property
    def end_point(self) -> list[float]:
        return self.points[-1]


def haversine_distance_km(
    first_point: list[float],
    second_point: list[float],
) -> float:
    """
    Calculates distance between two GeoJSON points.

    GeoJSON point format:
    [longitude, latitude]
    """

    first_longitude, first_latitude = first_point
    second_longitude, second_latitude = second_point

    earth_radius_km = 6371.0

    latitude_difference = radians(
        second_latitude - first_latitude
    )

    longitude_difference = radians(
        second_longitude - first_longitude
    )

    first_latitude = radians(first_latitude)
    second_latitude = radians(second_latitude)

    value = (
        sin(latitude_difference / 2) ** 2
        + cos(first_latitude)
        * cos(second_latitude)
        * sin(longitude_difference / 2) ** 2
    )

    angular_distance = 2 * atan2(
        sqrt(value),
        sqrt(1 - value),
    )

    return earth_radius_km * angular_distance


def normalize_geometry_points(
    geometry: dict[str, Any],
) -> list[list[float]]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])

    if geometry_type == "LineString":
        return coordinates

    if geometry_type == "MultiLineString":
        points = []

        for line in coordinates:
            for point in line:
                if not points or point != points[-1]:
                    points.append(point)

        return points

    raise ValueError(
        f"Unsupported geometry type: {geometry_type}"
    )


def split_route_geometry(
    geometry: dict[str, Any],
    max_segment_km: float = 150.0,
) -> list[RouteSegment]:
    points = normalize_geometry_points(geometry)

    if len(points) < 2:
        raise ValueError(
            "The route geometry must contain at least two points"
        )

    segments = []

    current_points = [points[0]]
    current_distance_km = 0.0

    for start_point, end_point in pairwise(points):
        distance_km = haversine_distance_km(
            start_point,
            end_point,
        )

        if distance_km > max_segment_km:
            raise ValueError(
                "Two consecutive geometry points are farther "
                "apart than the maximum segment length"
            )

        if (
            current_distance_km + distance_km
            <= max_segment_km
        ):
            current_points.append(end_point)
            current_distance_km += distance_km
            continue

        segments.append(
            RouteSegment(
                segment_index=len(segments),
                points=current_points,
                distance_km=current_distance_km,
            )
        )

        current_points = [
            start_point,
            end_point,
        ]

        current_distance_km = distance_km

    if len(current_points) >= 2:
        segments.append(
            RouteSegment(
                segment_index=len(segments),
                points=current_points,
                distance_km=current_distance_km,
            )
        )

    return segments


def deduplicate_routes(routes):
    unique_routes = []
    seen_geometries = set()

    for route in routes:
        geometry_key = json.dumps(
            route.geometry,
            sort_keys=True,
        )

        if geometry_key in seen_geometries:
            continue

        seen_geometries.add(geometry_key)
        unique_routes.append(route)

    return unique_routes