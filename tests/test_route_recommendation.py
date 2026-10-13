import asyncio

from backend.services.route_recommendation import (
    recommend_route,
)


async def main() -> None:
    result = await recommend_route(
        origin_name="Paris, France",
        destination_name="Timișoara, Romania",
        engine_type="Electric",
        avg_consumption=18.5,
        fuel_price=1.75,
        electricity_price=0.25,
    )

    print("Origin:", result["origin"])
    print("Destination:", result["destination"])
    print("Distance:", round(result["distance_km"], 2), "km")
    print("Duration:", round(result["duration_min"], 2), "minutes")
    print("Cost:", round(result["total_cost"], 2))
    print("Tolls:", result["has_tolls"])
    print("POIs:", result["poi_count"])

    print("\nSelected routes:")

    for route in result["routes"]:
        print(
            f"Segment {route['qid']}: "
            f"route {route['route_index']}, "
            f"score={route['rank_score']:.4f}"
        )


if __name__ == "__main__":
    asyncio.run(main())