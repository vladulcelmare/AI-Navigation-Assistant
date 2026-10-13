from pathlib import Path
from typing import Any

from backend.integrations.routing_client import GeoapifyClient, Coordinates
from backend.integrations.xgbranker.ranker import (
    RouteRanker,
)
from backend.services.route_features import (
    build_route_record,
    calculate_cost_per_km,
)
from backend.services.route_segmentation import (
    deduplicate_routes,
    split_route_geometry,
)


async def recommend_route(origin_name: str, destination_name: str,
                          engine_type: str, avg_consumption: float,
                          total_capacity: float, current_level_percent: float,
                          fuel_price: float, electricity_price: float,
                          preferences: dict[str, Any] | None = None,
                          partner_opportunities: list[dict] | None = None,
                          destination_coordinates: dict | None = None,
                          origin_coordinates: dict | None = None) -> dict[str, Any]:
    
    client = GeoapifyClient()

    origin = Coordinates(**origin_coordinates) if origin_coordinates else await client.geocode(origin_name)
    destination = (Coordinates(**destination_coordinates) if destination_coordinates else await client.geocode(destination_name))

    preferences = preferences or {"road_conditions": "mixed", "age_group": "adult",
                                  "driver_type": "efficient", "tolls": True}

    routes = await client.get_route_candidates(
        origin,
        destination,
        alternatives=3,
        avoid_tolls=not preferences["tolls"],
    )

    segments = split_route_geometry(
        routes[0].geometry,
        max_segment_km=150.0,
    )

    cost_per_km = calculate_cost_per_km(
        engine_type=engine_type,
        avg_consumption=avg_consumption,
        fuel_price=fuel_price,
        electricity_price=electricity_price,
    )


    all_records = []

    for segment in segments:
        start_lon, start_lat = segment.start_point
        end_lon, end_lat = segment.end_point

        segment_routes = await client.get_route_candidates(
            Coordinates(latitude=start_lat, longitude=start_lon),
            Coordinates(latitude=end_lat, longitude=end_lon),
            alternatives=3,
            avoid_tolls=not preferences["tolls"],
        )

        unique_routes = deduplicate_routes(segment_routes)

        for route_index, route in enumerate(unique_routes, start=1):
            poi_count = await client.count_pois_near_route(
                route.geometry
            )

            all_records.append(
                build_route_record(
                    qid=segment.segment_index,
                    route_index=route_index,
                    route=route,
                    cost_per_km=cost_per_km,
                    poi_count=poi_count,
                    preferences=preferences,
                )
            )

    model_path = (
        Path(__file__).resolve().parents[2]
        / "backend"
        / "integrations"
        / "xgbranker"
        / "xgbranker_ndcg.json"
    )

    ranker = RouteRanker(model_path)
    ranked_records = ranker.rank(all_records)

    top_3_qid = {}

    for record in ranked_records:
        curr_qid = record["qid"]

        if curr_qid not in top_3_qid:
            top_3_qid[curr_qid] = []

        if len(top_3_qid[curr_qid]) < 3:
            top_3_qid[curr_qid].append(record)

    best_routes = [alternatives[0] for alternatives in top_3_qid.values()]

    return {
        "origin": origin_name,
        "destination": destination_name,
        "origin_coordinates": {"latitude": origin.latitude, "longitude": origin.longitude},
        "destination_coordinates": {"latitude": destination.latitude, "longitude": destination.longitude},
        "preferences": preferences,
        "partner_opportunities": partner_opportunities,
        "routes": list(top_3_qid.values()),
        "distance_km": sum(
            route["distance_km"]
            for route in best_routes
        ),
        "duration_min": sum(
            route["distance_min"]
            for route in best_routes
        ),
        "total_cost": sum(
            route["total_cost"]
            for route in best_routes
        ),
        "has_tolls": any(
            route["route_has_tolls"]
            for route in best_routes
        ),
        "poi_count": sum(
            route["POI count"]
            for route in best_routes
        ),
    }
