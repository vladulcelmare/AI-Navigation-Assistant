# AI Powered In-car Assistant

An AI assistant capable of receiving your vehicle telemetry to propose personally-tailored routes. <br>
Project written in Python 3.13 (backend), .... (frontend)

## Requirements

The user must have installed the following: <br>
*backend*

* **uv**
* **Python 3.13**
* **dotenv**
* **sqlalchemy**
* **OpenAI** (functional key required)
* **Pydantic** and EmailStr
* **xgboost**
* **jwt**
* **sklearn**

*frontend*
* Node.js

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

...


## Installation guide

Before executing the commands written below, the user must have a functional OpenAI key stored in a .env file. The .env file must be in the same directory as the project (SmartLibrarian).<br>
Recommended : ensure it is in .gitignore, to avoid exposing the key.

```powershell
cd .\<repo-name>\
# if uv is not installed, run this
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
# restart terminal then cd to project again to install python
uv python install 3.13
uv venv --python 3.13.14
uv pip install --python .venv\Scripts\python.exe requirements
```

Check if environment is in .venv\Scripts\python.exe <br>
If found, select interpretor (CTRL + SHIFT + P) : 'project_root'\.venv\Scripts\python.exe <br>
Finally, run this:

```powershell
# in case u havent already
cd .\<repo-name>\
# run this only if powershell does not allow
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

To run any program, ensure you type in powershell first in project main directory:
```powershell
$env:PYTHONPATH = (Get-Location).Path
```

Finished!
