from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.auth import router as auth_router
from backend.routers.conversations import router as conversations_router
from backend.routers.health import router as health_router
from backend.routers.opportunities import router as opportunities_router
from backend.routers.trips import router as trips_router
from backend.routers.users import router as users_router
from backend.routers.vehicles import router as vehicles_router

app = FastAPI(
    title = "AI-Powered In-Car Assistant"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Access-Token", "X-Token-Type"],
)


app.include_router(vehicles_router)
app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(users_router)
app.include_router(trips_router)
app.include_router(opportunities_router)
app.include_router(health_router)


@app.get("/", status_code=status.HTTP_200_OK)
def root():
    return {"message": "Welcome to the AI-Powered In-Car Assistant API"}
