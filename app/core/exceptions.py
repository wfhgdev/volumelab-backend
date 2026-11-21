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
