# Conversation and trip flow

## Setup

Run `database/001_add_trip_route_and_status.sql`, then `database/002_assistant_state.sql`
on the project's SQL Server database. The second migration adds nullable columns for
current vehicle location and the latest conversation recommendations.

Set `FUEL_PRICE` (per litre) and `ELECTRICITY_PRICE` (per kWh) in `.env`, in the same
currency. Zero means unconfigured; the assistant will ask for backend configuration.
These are configured estimates, not live prices.

All endpoints below require the user's bearer token. The backend checks ownership.

## Location

The GPS/telemetry producer periodically sends `PUT /vehicles/{vehicle_id}/location`:

```json
{"latitude": 47.159, "longitude": 27.587, "updated_at": "<current UTC ISO timestamp>"}
```

Use a real timestamp, for example the producer's current UTC time. Updates older
than the stored position are rejected. Routing treats positions over 120 seconds
old as unavailable. `GET /vehicles/{vehicle_id}/location` returns the stored sample.
No GPS device or background simulator is started by the backend; a producer must
feed this endpoint. Position is stored in SQL, not in frontend state or process memory.

## Recommend, accept, start

1. Create a conversation using `POST /users/me/conversations` with a title.
2. Send `POST /users/me/conversations/{id}/messages` with `content` and `vehicle_id`.
   The vehicle ID may be omitted when there is exactly one vehicle, or the
   conversation already has a recommendation for the selected vehicle.
3. The reply contains `response` and `recommendations`. Each recommendation includes
   its ID, selected route geometry, segment alternatives and selected `choices`.
   Epsilon still applies per segment. No trip is created at this point.
4. Accept using `POST /users/me/conversations/{id}/recommendations/{recommendation_id}/accept`
   with `{}`. To override an alternative, send `{"choices": {"0": 2}}`, using the
   segment's actual `qid` and the alternative's `route_index`.
5. The returned trip is `PLANNED`. Start it with `PATCH /trips/{trip_id}/status`
   and `{"status": "IN_PROGRESS"}`. Finish with `{"status": "COMPLETED"}`;
   cancellation uses `CANCELLED`. Finished trips cannot be reopened.

For an existing planned/active trip, request another recommendation for that vehicle.
It uses fresh backend location. Accepting updates that same trip, preserving `origin`
and exposing the new departure point as `route_origin`. A position that has expired
or moved more than 250 metres since recommendation requires a new recommendation.

Only the latest recommendation batch is kept per conversation. Repeated acceptance
of an accepted recommendation returns its trip instead of creating another one.
The frontend implementation is outside this change.
