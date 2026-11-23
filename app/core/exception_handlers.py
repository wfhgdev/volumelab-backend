from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError


async def integrity_error_handler(request: Request, exc: Exception) -> JSONResponse:
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None)
    db_message = str(orig) if orig is not None else str(exc)
    lowered = db_message.lower()

    if sqlstate == "23505" or "unique" in lowered or "duplicate" in lowered:
        return JSONResponse(status_code=409, content={"detail": "Conflicto de integridad: el registro ya existe"})
    if sqlstate == "23514" or "check" in lowered:
        return JSONResponse(status_code=422, content={"detail": "Datos fuera de las reglas de negocio"})
    if sqlstate == "23502" or "not-null" in lowered or "not null" in lowered:
        return JSONResponse(status_code=422, content={"detail": "Faltan campos obligatorios"})
    if sqlstate == "23503" or "foreign key" in lowered:
        return JSONResponse(status_code=409, content={"detail": "El registro está referenciado por otros datos"})
    return JSONResponse(status_code=409, content={"detail": "Conflicto de integridad"})


async def db_error_handler(request: Request, exc: Exception) -> JSONResponse:
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None)
    db_message = str(orig) if orig is not None else str(exc)
    lowered = db_message.lower()

    if sqlstate == "22P02" or "invalid input value for enum" in lowered:
        return JSONResponse(status_code=422, content={"detail": "Valor inválido para el tipo de dato"})
    if sqlstate == "P0001":
        if "rn-07" in lowered:
            return JSONResponse(status_code=409, content={"detail": db_message})
        if "solo un admin" in lowered:
            return JSONResponse(status_code=403, content={"detail": db_message})
        return JSONResponse(status_code=422, content={"detail": db_message})
    return JSONResponse(status_code=500, content={"detail": "Error interno de base de datos"})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(DBAPIError, db_error_handler)
