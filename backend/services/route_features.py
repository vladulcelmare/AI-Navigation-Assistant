import numpy as np

HIGHWAY_CLASSES = {
    "motorway",
    "trunk",
    "primary",
}

CITY_CLASSES = {
    "secondary",
    "tertiary",
    "residential",
    "service_other",
    "unclassified",
}

DIRT_SURFACES = {
    "dirt",
    "gravel",
    "path",
    "compacted",
    "impassable",
}


def extract_road_condition(properties: dict,) -> str:
    road_classes = set()
    surfaces = set()

    for leg in properties.get("legs", []):
        for step in leg.get("steps", []):
            road_class = step.get("road_class")
            surface = step.get("surface")

            if road_class:
                road_classes.add(road_class)

            if surface:
                surfaces.add(surface)

    if surfaces.intersection(DIRT_SURFACES):
        return "dirt_roads"

    has_highway = bool(
        road_classes.intersection(HIGHWAY_CLASSES)
    )

    has_city = bool(
        road_classes.intersection(CITY_CLASSES)
    )

    if has_highway and has_city:
        return "mixed"

    if has_highway:
        return "highway_roads"

    if has_city:
        return "city_roads"

    return "mixed"


def build_route_record(
    qid: int,
    route_index: int,
    route,
    cost_per_km: float,
    poi_count: int,
    preferences: dict,
) -> dict:
    road_condition = extract_road_condition(
        route.properties
    )

    total_cost = (
        route.distance_km * cost_per_km
    )

    return {
        "qid": qid,
        "route_index": route_index,
        "geometry": route.geometry,
        "cost_per_km": round(cost_per_km, 4),
        "distance_km": round(route.distance_km, 2),
        "distance_min": round(route.duration_min, 2),
        "total_cost": round(total_cost, 2),
        "route_road_condition": road_condition,
        "route_has_tolls": int(route.has_tolls),
        "POI count": poi_count,
        "preference_road_conditions": (
            preferences["road_conditions"]
        ),
        "preference_age_group": (
            preferences["age_group"]
        ),
        "preference_driver_type": (
            preferences["driver_type"]
        ),
        "preference_tolls": int(
            preferences["tolls"]
        ),
    }


def calculate_cost_per_km(
    engine_type: str,
    avg_consumption: float,
    fuel_price: float,
    electricity_price: float,
) -> float:
    if engine_type == "Electric":
        return (
            avg_consumption * electricity_price
        ) / 100

    return (
        avg_consumption * fuel_price
    ) / 100



def generate_preferences(seed: int | None = None,) -> dict:
    rng = np.random.default_rng(seed)

    return {
        "road_conditions": rng.choice(
            [
                "highway_roads",
                "city_roads",
                "dirt_roads",
                "mixed",
            ]
        ).item(),
        "age_group": rng.choice(
            [
                "young",
                "adult",
                "senior",
            ]
        ).item(),
        "driver_type": rng.choice(
            [
                "efficient",
                "fast",
                "calm",
            ]
        ).item(),
        "tolls": bool(
            rng.integers(0, 2)
        ),
    }
