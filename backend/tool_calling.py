from backend.services.route_recommendation import recommend_route
from pydantic import BaseModel, ConfigDict, Field


class RouteArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    origin_name: str | None = Field(min_length=1)
    destination_name: str = Field(min_length=1)

async def call_tool(tool_name: str, args: dict, route_context: dict | None = None):
    if tool_name == "recommend_route":
        validated = RouteArguments.model_validate(args)
        if not route_context or route_context.get("error"):
            raise ValueError((route_context or {}).get("error", "Select a vehicle before requesting a route"))
        parameters = dict(route_context["parameters"])
        origin = "Current location" if parameters.get("origin_coordinates") else validated.origin_name
        if not origin:
            raise ValueError("Provide an origin or update the vehicle location")
        return await recommend_route(origin_name=origin, destination_name=validated.destination_name, **parameters)
    else:
        raise ValueError(f"Unknown tool: {tool_name}")
