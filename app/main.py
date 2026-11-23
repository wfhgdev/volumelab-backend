from fastapi import FastAPI
from app.core.config import settings
from app.core.database_connection import engine
from app.core.exception_handlers import register_exception_handlers
from sqlalchemy import text
from app.api import test_routes
from app.api import app_user_routes
from app.api import weight_history_routes
from app.api import workout_rate_routes
from app.api import session_rate_routes
from app.api import mesocycle_routes
from app.api import training_week_routes
from app.api import workout_routes
from app.api import muscle_group_routes
from app.api import muscle_workout_routes


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION
)

app.include_router(test_routes.router)
app.include_router(app_user_routes.router)
app.include_router(weight_history_routes.router)
app.include_router(mesocycle_routes.router)
app.include_router(training_week_routes.router)
app.include_router(workout_rate_routes.router)
app.include_router(session_rate_routes.router)
app.include_router(workout_routes.router)
app.include_router(muscle_group_routes.router)
app.include_router(muscle_workout_routes.router)
register_exception_handlers(app)

