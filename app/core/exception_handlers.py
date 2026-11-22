from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.audit_logger import AuditLogLevel, log_audit_event


async def integrity_error_handler(request: Request, exc: Exception) -> JSONResponse:
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None)
    db_message = str(orig) if orig is not None else str(exc)
    lowered = db_message.lower()

    if sqlstate == "23505" or "unique" in lowered or "duplicate" in lowered:
        status_code, detail = 409, "Conflicto de integridad: el registro ya existe"
    elif sqlstate == "23514" or "check" in lowered:
        status_code, detail = 422, "Datos fuera de las reglas de negocio"
    elif sqlstate == "23502" or "not-null" in lowered or "not null" in lowered:
        status_code, detail = 422, "Faltan campos obligatorios"
    elif sqlstate == "23503" or "foreign key" in lowered:
        status_code, detail = 409, "El registro está referenciado por otros datos"
    else:
        status_code, detail = 409, "Conflicto de integridad"

    log_audit_event(
        AuditLogLevel.WARNING,
        event="db.integrity_error",
        message=detail,
        endpoint=str(request.url.path),
        http_method=request.method,
        status_code=status_code,
        details={"sqlstate": sqlstate},
    )
    return JSONResponse(status_code=status_code, content={"detail": detail})


async def db_error_handler(request: Request, exc: Exception) -> JSONResponse:
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None)
    db_message = str(orig) if orig is not None else str(exc)
    lowered = db_message.lower()

    if sqlstate == "22P02" or "invalid input value for enum" in lowered:
        status_code, detail = 422, "Valor inválido para el tipo de dato"
        level = AuditLogLevel.WARNING
    elif sqlstate == "P0001":
        level = AuditLogLevel.WARNING
        if "rn-07" in lowered:
            status_code, detail = 409, db_message
        elif "solo un admin" in lowered:
            status_code, detail = 403, db_message
        else:
            status_code, detail = 422, db_message
    else:
        status_code, detail = 500, "Error interno de base de datos"
        level = AuditLogLevel.ERROR

    log_audit_event(
        level,
        event="db.api_error",
        message=detail,
        endpoint=str(request.url.path),
        http_method=request.method,
        status_code=status_code,
        details={"sqlstate": sqlstate},
    )
    return JSONResponse(status_code=status_code, content={"detail": detail})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(DBAPIError, db_error_handler)
