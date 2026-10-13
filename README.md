# AI Powered In-car Assistant

An AI assistant capable of receiving your vehicle telemetry to propose personally-tailored routes. <br>
Project written in Python 3.13 (backend), React + Vite (frontend)

## Requirements

* **Backend:** Python 3.13, `uv`, SQL Server, and Microsoft ODBC Driver 17 for SQL Server
* **Frontend:** Node.js and npm

## Frontend

The frontend is a React application built with Vite and Tailwind CSS. It is located in
`frontend/` and is organized by feature:

* `src/app/` - application composition and providers
* `src/pages/` - login and dashboard screens
* `src/components/` - reusable layout components
* `src/features/auth/` - authentication and user data
* `src/features/map/` - map, routing, and location functionality
* `src/features/vehicles/` - vehicle selection, telemetry, and indicators
* `src/lib/` - shared HTTP client utilities
* `src/assets/` - imported vehicle images and other assets

### Frontend setup

```powershell
cd .\frontend\
npm install
Copy-Item .env.example .env
```

Set the backend address and public map configuration in `frontend/.env`:

```env
VITE_BACKEND_BASE_URL=127.0.0.1:8000
VITE_GEOAPIFY_MAP_STYLE_URL=
VITE_GEOAPIFY_BASE_URL=https://api.geoapify.com
VITE_GEOAPIFY_KEY=
VITE_ORS_BASE_URL=https://api.heigit.org/openrouteservice/v2
VITE_ORS_KEY=
VITE_USE_MOCK_MAP=false
VITE_USE_MOCK_LOCATION=true
```

Frontend commands:

```powershell
# Start the Vite development server with hot reload
npm run dev

# Create an optimized production build in frontend/dist/
npm run build

# Run Oxlint across the frontend source
npm run lint
```

The local `.env` file, `node_modules/`, and Vite's generated `dist/` directory
are excluded from version control. Use `.env.example` as the safe configuration template.


## Backend

The backend is a FastAPI application in `backend/`. Its routers expose the HTTP API;
services implement assistant, conversation, route, vehicle, and trip behavior; and
repositories persist domain data in SQL Server.

### Backend requirements

* Python 3.13
* [`uv`](https://docs.astral.sh/uv/)
* SQL Server and the Microsoft ODBC Driver 17 for SQL Server
* Geoapify API key for routing, places, and geocoding requests

### Backend setup

Run these commands from the repository root in PowerShell:

```powershell
uv sync
Copy-Item .env.example .env
```

Edit the root `.env` and configure the required SQL Server credentials
(`DB_USER` and `DB_PASSWORD`), a private `JWT_SECRET_KEY`, and `GEOAPIFY_API_KEY`.
Set `DB_SERVER`, `DB_PORT`, `DB_NAME`, and `DB_DRIVER` if your SQL Server differs
from the defaults. Set `FUEL_PRICE` (per litre) and `ELECTRICITY_PRICE` (per kWh)
in the same currency if route cost estimates are needed. Keep `.env` private; use
`.env.example` as the shareable template.

Apply the SQL Server migrations in order before using conversation and trip flows:

1. `database/001_add_trip_route_and_status.sql`
2. `database/002_assistant_state.sql`

### Run and verify the backend

```powershell
# Start FastAPI with reload enabled
uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# Open the interactive API documentation
# http://127.0.0.1:8000/docs

# Run the backend tests
uv run pytest
```

The backend loads configuration from the repository-root `.env`. The frontend's
`VITE_BACKEND_BASE_URL` should point to the running API, for example
`http://127.0.0.1:8000`.
