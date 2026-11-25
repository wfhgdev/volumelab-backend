from fastapi import HTTPException, status

from app.models.app_user_model import AppUserModel


def is_admin(user: AppUserModel) -> bool:
    """Verifica si el usuario tiene rol de administrador."""
    return user.role == "ADMIN"


def resolve_owner_id(current_user: AppUserModel, requested_id: int | None) -> int:
    """
    Resuelve el ID de propietario para creaciones y filtros:
    - Si es ADMIN: usa requested_id si se especificó, o current_user.id por defecto.
    - Si es CLIENTE: si requested_id no coincide con su id, lanza 403. Si coincide o no se envía, usa su propio id.
    """
    if is_admin(current_user):
        return requested_id if requested_id is not None else current_user.id

    if requested_id is not None and requested_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para operar a nombre de otro usuario",
        )
    return current_user.id


def ensure_owner_or_admin(
    current_user: AppUserModel,
    owner_id: int | None,
    is_private: bool = True,
) -> None:
    """
    Garantiza que el recurso pertenezca al usuario o que el usuario sea administrador:
    - Si es privado y pertenece a otro: lanza 404 (oculta la existencia del recurso).
    - Si es público y pertenece a otro: lanza 403 (permiso denegado para modificar).
    """
    if is_admin(current_user):
        return

    if owner_id is not None and owner_id == current_user.id:
        return

    if is_private:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurso no encontrado",
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permiso para modificar este recurso",
    )
