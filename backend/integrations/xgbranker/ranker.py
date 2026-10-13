from pathlib import Path
from typing import Any
import numpy as np
import xgboost as xgb

RANKER_FEATURES = [
    "qid",
    "cost_per_km",
    "distance_km",
    "distance_min",
    "total_cost",
    "route_road_condition",
    "route_has_tolls",
    "POI count",
    "preference_road_conditions",
    "preference_age_group",
    "preference_driver_type",
]


ROAD_MAPPING = {
    "highway_roads": 0,
    "city_roads": 1,
    "dirt_roads": 2,
    "mixed": 3,
}

AGE_MAPPING = {
    "young": 0,
    "adult": 1,
    "senior": 2,
}

DRIVER_MAPPING = {
    "efficient": 0,
    "fast": 1,
    "calm": 2,
}


class RouteRanker:
    def __init__(self, model_path: str | Path):
        self.model = xgb.XGBRanker()
        self.model.load_model(str(model_path))

        expected_features = (
            self.model.get_booster().num_features()
        )

        if expected_features != len(RANKER_FEATURES):
            raise ValueError(
                f"Model expects {expected_features} features, "
                f"but pipeline provides "
                f"{len(RANKER_FEATURES)}."
            )

    def rank(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not records:
            return []

        matrix = []

        for record in records:
            row = [
                record["qid"],
                record["cost_per_km"],
                record["distance_km"],
                record["distance_min"],
                record["total_cost"],
                ROAD_MAPPING[
                    record["route_road_condition"]
                ],
                int(record["route_has_tolls"]),
                record["POI count"],
                ROAD_MAPPING[
                    record["preference_road_conditions"]
                ],
                AGE_MAPPING[
                    record["preference_age_group"]
                ],
                DRIVER_MAPPING[
                    record["preference_driver_type"]
                ],
            ]

            matrix.append(row)

            predictions = self.model.predict(np.asarray(matrix,
                                                        dtype=np.float32))

        ranked_records = []

        for record, score in zip(
            records,
            predictions):
            ranked_records.append({**record, "rank_score": float(score)})

        return sorted(
            ranked_records,
            key=lambda record: (record["qid"], -record["rank_score"])
            )
