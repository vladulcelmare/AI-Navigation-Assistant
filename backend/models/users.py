from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from backend.models.conversations import Conversation
from backend.models.trips import UserTripHistory


@dataclass
class UserPreference:
    user_id: str
    age_group: str
    driver_type: DriverType
    road_conditions: list[RoadConditions]
    tolls: bool = True

    def __post_init__(self):
        possible_age_groups = {"young": range(18, 30), "adult": range(30, 60), "senior": range(60, 120)}

        if self.age_group not in possible_age_groups:
            raise ValueError(f"Age group must be one of {list(possible_age_groups.keys())}")

        self.age_group = self.age_group.lower()


class DriverType(Enum):
    """
    Different types of drivers
    """
    CALM = "calm"
    FAST = "fast"
    EFFICIENT = "efficient"



class RoadConditions(Enum):
    """
    Different types of roads
    """
    HIGHWAY_ROADS = "highway_roads"
    CITY_ROADS = "city_roads"
    DIRT_ROADS = "dirt_roads"
    MIXED = "mixed"





@dataclass
class User:
    """
    Represents a user entity from the db
    """
    user_id: str
    username: str
    email: str
    created_at: datetime
    preferences: UserPreference
    trip_history: list[UserTripHistory]
    conversations: list[Conversation]

@dataclass
class UserCredentials:
    user_id: str
    password_hash: str
