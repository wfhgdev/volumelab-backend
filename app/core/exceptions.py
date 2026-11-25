from fastapi import HTTPException, status


class MesocycleNotFoundException(HTTPException):
    def __init__(self, mesocycle_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mesocycle with id {mesocycle_id} not found"
        )


class UserNotFoundException(HTTPException):
    def __init__(self, user_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )


class MesocycleDateValidationException(HTTPException):
    def __init__(self, detail: str = "end_date must be greater than or equal to start_date"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class TrainingWeekNotFoundException(HTTPException):
    def __init__(self, training_week_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training week with id {training_week_id} not found"
        )


class TrainingWeekOrderConflictException(HTTPException):
    def __init__(self, mesocycle_id: int, week_order: int):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A training week with order {week_order} already exists for mesocycle {mesocycle_id}"
        )


class TrainingWeekDateValidationException(HTTPException):
    def __init__(self, detail: str = "end_date must be greater than or equal to start_date"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class AuditNotFoundException(HTTPException):
    def __init__(self, audit_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registro de auditoría con id {audit_id} no encontrado",
        )


class AuditDateRangeValidationException(HTTPException):
    def __init__(self, detail: str = "date_from no puede ser posterior a date_to"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


# Excepciones de Autenticación y Autorización
class MissingTokenException(HTTPException):
    def __init__(self, detail: str = "Token de autenticación no proporcionado"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidCredentialsException(HTTPException):
    def __init__(self, detail: str = "Credenciales inválidas"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class BlockedUserException(HTTPException):
    def __init__(self, detail: str = "Usuario bloqueado"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class InvalidTokenException(HTTPException):
    def __init__(self, detail: str = "Token inválido o mal formado"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ExpiredTokenException(HTTPException):
    def __init__(self, detail: str = "Token expirado"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class PermissionDeniedException(HTTPException):
    def __init__(self, detail: str = "No tienes permisos para realizar esta acción"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class ForbiddenResourceException(HTTPException):
    def __init__(self, detail: str = "No tienes permiso para modificar este recurso"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class ResourceNotFoundException(HTTPException):
    def __init__(self, detail: str = "Recurso no encontrado"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )
