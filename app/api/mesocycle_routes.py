from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database_connection import get_db
from app.core.dependencies import AuditContext, get_audit_context, get_current_user
from app.models.app_user_model import AppUserModel
from app.schemas.mesocycle_schema import (
    MesocycleCreate,
    MesocycleUpdate,
    MesocycleResponse,
    MesocycleStatusEnum
)
from app.controllers import mesocycle_controller


router = APIRouter(prefix="/mesocycles", tags=["Mesocycles"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[AppUserModel, Depends(get_current_user)]
RequestAuditContext = Annotated[AuditContext, Depends(get_audit_context)]


@router.post("/", response_model=MesocycleResponse, status_code=status.HTTP_201_CREATED)
def create_new_mesocycle(
    mesocycle: MesocycleCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
    audit_context: RequestAuditContext,
):
    """Crea un nuevo mesociclo asociado a un usuario."""
    return mesocycle_controller.create_mesocycle(
        db=db, mesocycle=mesocycle, current_user=current_user, audit_context=audit_context
    )


@router.get("/", response_model=List[MesocycleResponse], status_code=status.HTTP_200_OK)
def list_mesocycles(
    db: DatabaseSession,
    current_user: CurrentUser,
    user_id: Optional[int] = Query(None, description="Filtrar por ID de usuario"),
    status: Optional[MesocycleStatusEnum] = Query(None, description="Filtrar por estado del mesociclo"),
    skip: int = Query(0, ge=0, description="Registros a omitir"),
    limit: int = Query(100, ge=1, le=500, description="Máximo de registros a retornar"),
):
    """Obtiene el listado de mesociclos con filtros opcionales."""
    status_str = status.value if status else None
    return mesocycle_controller.get_mesocycles(
        db=db,
        current_user=current_user,
        user_id=user_id,
        status=status_str,
        skip=skip,
        limit=limit
    )


@router.get("/{mesocycle_id}", response_model=MesocycleResponse, status_code=status.HTTP_200_OK)
def get_mesocycle(
    mesocycle_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
):
    """Obtiene un mesociclo por su ID."""
    return mesocycle_controller.get_mesocycle_by_id(db=db, mesocycle_id=mesocycle_id, current_user=current_user)


@router.put("/{mesocycle_id}", response_model=MesocycleResponse, status_code=status.HTTP_200_OK)
def update_mesocycle(
    mesocycle_id: int,
    mesocycle_update: MesocycleUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
    audit_context: RequestAuditContext,
):
    """Actualiza los datos de un mesociclo existente."""
    return mesocycle_controller.update_mesocycle(
        db=db,
        mesocycle_id=mesocycle_id,
        mesocycle_update=mesocycle_update,
        current_user=current_user,
        audit_context=audit_context,
    )


@router.delete("/{mesocycle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mesocycle(
    mesocycle_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
    audit_context: RequestAuditContext,
):
    """Elimina un mesociclo por su ID."""
    mesocycle_controller.delete_mesocycle(
        db=db, mesocycle_id=mesocycle_id, current_user=current_user, audit_context=audit_context
    )
    return None
