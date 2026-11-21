from fastapi import FastAPI
from app.core.config import settings
from app.core.database_connection import engine
from app.core.exception_handlers import register_exception_handlers
from sqlalchemy import text
from app.api import test_routes
from app.api import app_user_routes


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION
)

app.include_router(test_routes.router)
app.include_router(app_user_routes.router)
register_exception_handlers(app)


"""
@app.get("/health/db", tags=["Health"])
def check_database():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"message": "Conexión a la base de datos exitosa"}
"""

