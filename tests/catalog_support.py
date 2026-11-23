from uuid import uuid4

from app.models.muscle_workout_model import MuscleRole, MuscleWorkoutModel
from app.models.workout_model import ExerciseType, WorkoutModel


def associate_group(db, muscle_group_id, creator_id, count=1):
    associations = []
    for _ in range(count):
        workout = WorkoutModel(
            name=f"Exercise {uuid4().hex}", type=ExerciseType.DYNAMIC, created_by=creator_id,
        )
        db.add(workout)
        db.flush()
        association = MuscleWorkoutModel(
            workout_id=workout.id, muscle_group_id=muscle_group_id,
            muscle_role=MuscleRole.PRIMARY, weighing=100,
        )
        db.add(association)
        associations.append(association)
    db.commit()
    return associations
