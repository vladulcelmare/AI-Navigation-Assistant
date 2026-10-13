import asyncio
from collections import Counter
from pathlib import Path

from backend.integrations.routing_client import (
    Coordinates,
    GeoapifyClient,
)
from backend.integrations.xgbranker.ranker import (
    RouteRanker,
)
from backend.services.route_features import (
    build_route_record,
    calculate_cost_per_km,
    generate_preferences,
)
from backend.services.route_segmentation import (
    deduplicate_routes,
    split_route_geometry,
)


async def main() -> None:
    client = GeoapifyClient()

    origin = await client.geocode("Paris, France")
    destination = await client.geocode(
        "Timișoara, Romania"
    )

    print(
        f"Origin: {origin.latitude:.6f}, "
        f"{origin.longitude:.6f}"
    )
    print(
        f"Destination: {destination.latitude:.6f}, "
        f"{destination.longitude:.6f}"
    )

    routes = await client.get_routes(
        origin,
        destination,
        alternatives=3,
    )

    print(f"Routes returned: {len(routes)}")

    for index, route in enumerate(routes, start=1):
        print(
            f"Route {index}: "
            f"{route.distance_km:.2f} km, "
            f"{route.duration_min:.2f} min, "
            f"tolls={route.has_tolls}"
        )

    base_route = routes[0]
    geometry = base_route.geometry

    segments = split_route_geometry(
        geometry,
        max_segment_km=150.0,
    )

    print(f"\nSegments: {len(segments)}")

    for segment in segments:
        print(
            f"Segment {segment.segment_index}: "
            f"{segment.distance_km:.2f} km | "
            f"start={segment.start_point} | "
            f"end={segment.end_point}"
        )
    cost_per_km = calculate_cost_per_km(
        engine_type="Electric",
        avg_consumption=18.5,
        fuel_price=1.75,
        electricity_price=0.25,
    )
    # Seed for generating consistent preferences
    preferences = generate_preferences(
        seed=42
    )
    print("\nGenerated preferences:", preferences)

    print(
        f"\nCost per km: {cost_per_km:.5f}"
    )


    all_records = []

    for segment in segments:
        start_lon, start_lat = segment.start_point
        end_lon, end_lat = segment.end_point

        segment_origin = Coordinates(
            latitude=start_lat,
            longitude=start_lon,
        )
        segment_destination = Coordinates(
            latitude=end_lat,
            longitude=end_lon,
        )

        segment_routes = await client.get_routes(
            origin=segment_origin,
            destination=segment_destination,
            alternatives=3,
        )

        unique_routes = deduplicate_routes(
            segment_routes
        )

        segment_records = []

        for route_index, route in enumerate(
            unique_routes,
            start=1,
        ):
            """raza de 5 km
                5 puncte de sampling
                restaurants + accommodation + fuel + charging stations
                """
            poi_count = await client.count_pois_near_route(
                route.geometry
            )
            record = build_route_record(
                qid=segment.segment_index,
                route_index=route_index,
                route=route,
                cost_per_km=cost_per_km,
                poi_count=poi_count,
                preferences=preferences,
            )

            segment_records.append(record)
        all_records.extend(segment_records)

        print(
            f"\nSegment {segment.segment_index}: "
            f"{len(segment_routes)} requested, "
            f"{len(segment_records)} unique"
        )

        for record in segment_records:
            print(
                f"  Alternative {record['route_index']}: "
                f"{record['distance_km']:.2f} km, "
                f"{record['distance_min']:.2f} min, "
                f"tolls={bool(record['route_has_tolls'])}, "
                f"condition={record['route_road_condition']}"
            )

        if segment.segment_index == 0:
            print("\nExample record:")
            print(segment_records[0])
            print("Columns:", list(segment_records[0].keys()))

    print(
        f"\nTotal route records: "
        f"{len(all_records)}"
    )

    print(
        "First record:",
        all_records[0],
    )

    qid_sizes = Counter(
        record["qid"]
        for record in all_records
    )

    print("Routes per qid:", dict(qid_sizes))
    ranker = RouteRanker(
        Path(
            "backend/integrations/"
            "xgbranker/xgbranker_ndcg.json"
        )
    )

    ranked_records = ranker.rank(
        all_records
    )
    best_by_qid = {}
    for record in ranked_records:
        qid = record["qid"]

        if (
            qid not in best_by_qid
            or record["rank_score"]
            > best_by_qid[qid]["rank_score"]
        ):
            best_by_qid[qid] = record

    best_segment_routes = list(
        best_by_qid.values()
    )

    print("\nBest route per segment:")

    for record in best_segment_routes:
        print(
            f"qid={record['qid']}, "
            f"route={record['route_index']}, "
            f"score={record['rank_score']:.4f}, "
            f"distance={record['distance_km']:.2f} km"
        )

    total_distance = sum(
        record["distance_km"]
        for record in best_segment_routes
    )

    total_duration = sum(
        record["distance_min"]
        for record in best_segment_routes
    )

    total_cost = sum(
        record["total_cost"]
        for record in best_segment_routes
    )

    has_tolls = any(
        record["route_has_tolls"]
        for record in best_segment_routes
    )

    total_pois = sum(
        record["POI count"]
        for record in best_segment_routes
    )

    print("\nFinal recommended route:")
    print(
        f"Distance: {total_distance:.2f} km"
    )
    print(
        f"Duration: {total_duration:.2f} minutes"
    )
    print(
        f"Cost: {total_cost:.2f}"
    )
    print(f"Tolls: {bool(has_tolls)}")
    print(f"POIs: {total_pois}")

    print("\nRanked records:")

    for record in ranked_records[:10]:
        print(
            f"qid={record['qid']}, "
            f"route={record['route_index']}, "
            f"score={record['rank_score']:.4f}"
        )


if __name__ == "__main__":
    asyncio.run(main())