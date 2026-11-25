from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.controllers.audit_controller import get_audit, list_audits
from app.core.database_connection import get_db
from app.core.dependencies import require_admin
from app.models.app_user_model import AppUserModel
from app.models.audit_model import AuditAction
from app.schemas.audit_schema import AuditResponse

router = APIRouter(prefix="/audits", tags=["Audits"])


@router.get(
    "/",
    response_model=list[AuditResponse],
    summary="Listar registros de auditoría",
    description="Consulta paginada de auditoría exclusiva para administradores.",
)
def list_all(
    current_user: Annotated[AppUserModel, Depends(require_admin)],
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
    description="Consulta individual de un registro de auditoría exclusiva para administradores.",
)
def get_one(
    audit_id: Annotated[int, Path(gt=0, description="Identificador del registro de auditoría")],
    current_user: Annotated[AppUserModel, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    return get_audit(db, audit_id)
