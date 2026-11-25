from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    app_user_routes,
    audit_routes,
    auth_routes,
    mesocycle_routes,
    muscle_group_routes,
    muscle_workout_routes,
    session_rate_routes,
    training_week_routes,
    weight_history_routes,
    workout_rate_routes,
    workout_routes,
    workout_session_routes,
    workout_set_routes,
)
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(app_user_routes.router)
app.include_router(weight_history_routes.router)
app.include_router(mesocycle_routes.router)
app.include_router(training_week_routes.router)
app.include_router(workout_rate_routes.router)
app.include_router(session_rate_routes.router)
app.include_router(audit_routes.router)
app.include_router(workout_session_routes.router)
app.include_router(workout_set_routes.router)
app.include_router(workout_routes.router)
app.include_router(muscle_group_routes.router)
app.include_router(muscle_workout_routes.router)

register_exception_handlers(app)
