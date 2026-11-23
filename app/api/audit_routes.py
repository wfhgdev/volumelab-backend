from datetime import datetime

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.controllers.audit_controller import (
    create_audit,
    delete_audit,
    get_audit,
    list_audits,
    update_audit,
)
from app.core.database_connection import get_db
from app.models.audit_model import AuditAction
from app.schemas.audit_schema import AuditCreate, AuditResponse, AuditUpdate


router = APIRouter(prefix="/audits", tags=["Audits"])


@router.post(
    "/",
    response_model=AuditResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear registro de auditoría",
    description="Registra una operación crítica o exportación (INSERT, UPDATE, DELETE, EXPORT) en la tabla audit.",
)
def create(payload: AuditCreate, db: Session = Depends(get_db)):
    return create_audit(db, payload)


@router.get(
    "/",
    response_model=list[AuditResponse],
    summary="Listar registros de auditoría",
    description="Consulta paginada de auditoría filtrable por usuario, entidad, registro, acción y rango temporal.",
)
def list_all(
    user_id: int | None = Query(default=None, gt=0, description="Filtrar por ID de usuario"),
    entity: str | None = Query(default=None, min_length=1, max_length=60, description="Filtrar por entidad"),
    record_id: str | None = Query(default=None, min_length=1, max_length=60, description="Filtrar por ID del registro"),
    action: AuditAction | None = Query(default=None, description="Filtrar por acción (INSERT, UPDATE, DELETE, EXPORT)"),
    date_from: datetime | None = Query(default=None, description="Fecha/hora inicial inclusive (ISO 8601)"),
    date_to: datetime | None = Query(default=None, description="Fecha/hora final inclusive (ISO 8601)"),
    skip: int = Query(default=0, ge=0, description="Registros a omitir"),
    limit: int = Query(default=100, ge=1, le=500, description="Máximo de registros a devolver"),
    db: Session = Depends(get_db),
):
    return list_audits(
        db=db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        entity=entity,
        record_id=record_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
    )


@router.get(
    "/{audit_id}",
    response_model=AuditResponse,
    summary="Consultar registro de auditoría por ID",
)
def get_one(
    audit_id: int = Path(..., gt=0, description="Identificador del registro de auditoría"),
    db: Session = Depends(get_db),
):
    return get_audit(db, audit_id)


@router.put(
    "/{audit_id}",
    response_model=AuditResponse,
    summary="Actualizar registro de auditoría",
)
def update(
    payload: AuditUpdate,
    audit_id: int = Path(..., gt=0, description="Identificador del registro de auditoría"),
    db: Session = Depends(get_db),
):
    return update_audit(db, audit_id, payload)


@router.delete(
    "/{audit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar registro de auditoría",
)
def delete(
    audit_id: int = Path(..., gt=0, description="Identificador del registro de auditoría"),
    db: Session = Depends(get_db),
):
    delete_audit(db, audit_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
