import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "1433"))
DB_NAME = os.getenv("DB_NAME", "In_Car_Assistant_DB")
DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))

GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")

GEOAPIFY_PLACES_URL = "https://api.geoapify.com/v2/places"
GEOAPIFY_ROUTING_URL = "https://api.geoapify.com/v1/routing"
GEOAPIFY_GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"


# Prices in the same currency per litre / kWh; configure before recommending routes.
FUEL_PRICE = float(os.getenv("FUEL_PRICE", "0"))
ELECTRICITY_PRICE = float(os.getenv("ELECTRICITY_PRICE", "0"))

CHAT_TOOLS = [{
    "type": "function",
    "name": "recommend_route",
    "description": "Recommend a route. Vehicle data and preferences are supplied by the backend.",
    "parameters": {
        "type": "object",
        "properties": {
            "origin_name": {"type": ["string", "null"], "description": "Explicit departure place, or null to use current location."},
            "destination_name": {"type": "string", "description": "Requested destination."}
        },
        "required": ["origin_name", "destination_name"],
        "additionalProperties": False
    },
    "strict": True
}]

SYSTEM_PROMPT = """
You are an in-car assistant. Help with navigation and give concise responses.
Use recommend_route for route requests. Ask for the destination when it is unclear.
The backend supplies vehicle data, preferences, prices and current location; do not invent or ask for these in chat.
Use null for origin_name unless the user explicitly provides a departure place.
A recommendation is only a proposal: never claim that a trip has started or changed before acceptance.
"""
