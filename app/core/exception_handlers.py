from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError


async def integrity_error_handler(request: Request, exc: Exception) -> JSONResponse:
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None)
    diagnostic = getattr(orig, "diag", None)
    constraint = getattr(diagnostic, "constraint_name", None)
    db_message = str(orig) if orig is not None else str(exc)
    lowered = db_message.lower()

    if sqlstate == "23505" or "unique" in lowered or "duplicate" in lowered:
        if constraint == "uq_muscle_group_name" or "muscle_group" in lowered:
            return JSONResponse(
                status_code=409,
                content={"detail": "Ya existe un grupo muscular con este nombre"},
            )
        if constraint == "uq_workout_name" or ("workout" in lowered and "name" in lowered):
            return JSONResponse(
                status_code=409,
                content={"detail": "Ya existe un ejercicio con este nombre"},
            )
        return JSONResponse(
            status_code=409,
            content={"detail": "Conflicto de integridad: el registro ya existe"},
        )
    if sqlstate == "23514" or "check" in lowered:
        return JSONResponse(status_code=422, content={"detail": "Datos fuera de las reglas de negocio"})
    if sqlstate == "23502" or "not-null" in lowered or "not null" in lowered:
        return JSONResponse(status_code=422, content={"detail": "Faltan campos obligatorios"})
    if sqlstate in {"23503", "23001"} or "foreign key" in lowered:
        if "muscle_workout" in lowered or "muscle_group" in lowered:
            return JSONResponse(
                status_code=409,
                content={"detail": "No se puede eliminar un grupo muscular asociado a ejercicios"},
            )
        if "workout" in lowered and ("created_by" in lowered or "creator" in lowered or "app_user" in lowered):
            return JSONResponse(
                status_code=409,
                content={"detail": "El creador del ejercicio ya no existe"},
            )
        return JSONResponse(
            status_code=409,
            content={"detail": "El registro está referenciado por otros datos"},
        )
    if sqlstate in {"22P02"}:
        return JSONResponse(status_code=422, content={"detail": "Datos fuera de las reglas de negocio"})
    return JSONResponse(status_code=409, content={"detail": "Conflicto de integridad"})


async def db_error_handler(request: Request, exc: Exception) -> JSONResponse:
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None)
    diagnostic = getattr(orig, "diag", None)
    constraint = getattr(diagnostic, "constraint_name", None)
    context = getattr(diagnostic, "context", "") or ""
    db_message = str(orig) if orig is not None else str(exc)
    lowered = db_message.lower()

    if sqlstate in {"23505", "23503", "23001", "23502", "23514"}:
        return await integrity_error_handler(request, exc)

    if sqlstate == "22P02" or "invalid input value for enum" in lowered or "invalid input" in lowered:
        return JSONResponse(status_code=422, content={"detail": "Valor inválido para el tipo de dato"})
    if sqlstate == "P0001":
        if "rn-07" in lowered:
            return JSONResponse(status_code=409, content={"detail": db_message})
        if (
            constraint == "workout_public_limit"
            or "fn_workout_client_limit" in context.lower()
            or "fn_workout_client_limit" in lowered
            or "20 public workouts" in lowered
            or "workout_public_limit" in lowered
        ):
            return JSONResponse(
                status_code=409,
                content={"detail": "Un cliente puede tener como máximo 20 ejercicios públicos"},
            )
        if (
            "solo un admin" in lowered
            or constraint == "muscle_group_admin_only"
            or "fn_muscle_group_admin_only" in context.lower()
            or "fn_muscle_group_admin_only" in lowered
            or "require an administrator creator" in lowered
        ):
            return JSONResponse(
                status_code=403,
                content={"detail": "Solo un administrador puede crear o modificar un grupo muscular"},
            )
        return JSONResponse(status_code=422, content={"detail": db_message})
    return JSONResponse(status_code=500, content={"detail": "Error interno de base de datos"})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(DBAPIError, db_error_handler)
