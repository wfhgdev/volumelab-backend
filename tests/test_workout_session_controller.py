from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.controllers.workout_session_controller import (
    create_workout_session,
    delete_workout_session,
    get_workout_session_by_id,
    get_workout_sessions,
    update_workout_session,
)
from app.models.app_user_model import AppUserModel, RoleUser, UserStatus
from app.models.mesocycle_model import MesocycleModel, MesocycleStatus
from app.models.training_week_model import TrainingWeekModel
from app.models.workout_session_model import SessionStatus, WorkoutSessionModel
from app.schemas.workout_session_schema import WorkoutSessionCreate, WorkoutSessionUpdate


def create_user(db_session, role: RoleUser = RoleUser.CLIENTE) -> AppUserModel:
    user = AppUserModel(
        email=f"session_user_{uuid4().hex}@example.com",
        password_hash="hash",
        name="Session",
        role=role,
        status=UserStatus.ACTIVO,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_week(db_session, user_id: int) -> TrainingWeekModel:
    mesocycle = MesocycleModel(
        user_id=user_id,
        name=f"Meso {uuid4().hex}",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        status=MesocycleStatus.PLANIFICADO,
    )
    db_session.add(mesocycle)
    db_session.commit()
    db_session.refresh(mesocycle)

    week = TrainingWeekModel(
        mesocycle_id=mesocycle.id,
        week_order=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 7),
    )
    db_session.add(week)
    db_session.commit()
    db_session.refresh(week)
    return week


def create_session(
    db_session,
    user_id: int,
    session_date: date = date(2026, 11, 21),
    week_id: int | None = None,
    public: bool = False,
    status: str = "ABIERTO",
    closed_at: datetime | None = None,
    title: str = "Sesion",
) -> WorkoutSessionModel:
    return create_workout_session(
        db_session,
        WorkoutSessionCreate(
            user_id=user_id,
            week_id=week_id,
            title=title,
            session_date=session_date,
            current_bodyweight_kg=Decimal("60.50"),
            observation="Prueba",
            public=public,
            status=status,
            closed_at=closed_at,
        ),
    )


def seed_public_sessions(db_session, user_id: int, count: int) -> None:
    for index in range(count):
        db_session.add(
            WorkoutSessionModel(
                user_id=user_id,
                title=f"Seed {index}",
                session_date=date(2026, 1, 1),
                current_bodyweight_kg=Decimal("60.50"),
                public=True,
                status=SessionStatus.ABIERTO,
            )
        )
    db_session.commit()


def test_create_commits_when_user_exists(db_session, test_user):
    result = create_session(db_session, test_user.id)

    assert result.id >= 1
    assert result.user_id == test_user.id


def test_create_commits_with_training_week(db_session, test_user):
    week = create_week(db_session, test_user.id)

    result = create_session(db_session, test_user.id, week_id=week.id)

    assert result.week_id == week.id


def test_create_raises_404_when_user_missing(db_session):
    with pytest.raises(HTTPException) as exc:
        create_session(db_session, 2_000_000_000)

    assert exc.value.status_code == 404


def test_create_raises_404_when_week_missing(db_session, test_user):
    with pytest.raises(HTTPException) as exc:
        create_session(db_session, test_user.id, week_id=2_000_000_000)

    assert exc.value.status_code == 404


def test_get_by_id_returns_session(db_session, test_user):
    expected = create_session(db_session, test_user.id)

    result = get_workout_session_by_id(db_session, expected.id)

    assert result.id == expected.id


def test_get_by_id_raises_404_when_missing(db_session):
    with pytest.raises(HTTPException) as exc:
        get_workout_session_by_id(db_session, 2_000_000_000)

    assert exc.value.status_code == 404


def test_list_returns_sessions(db_session, test_user):
    expected = create_session(db_session, test_user.id)

    result = get_workout_sessions(db_session, user_id=test_user.id, skip=0, limit=500)

    assert any(session.id == expected.id for session in result)


def test_update_changes_title(db_session, test_user):
    session = create_session(db_session, test_user.id)

    result = update_workout_session(
        db_session, session.id, WorkoutSessionUpdate(title="Nuevo titulo")
    )

    assert result.title == "Nuevo titulo"


def test_update_raises_404_when_session_missing(db_session):
    with pytest.raises(HTTPException) as exc:
        update_workout_session(
            db_session, 2_000_000_000, WorkoutSessionUpdate(title="Nuevo titulo")
        )

    assert exc.value.status_code == 404


def test_update_raises_404_when_new_user_missing(db_session, test_user):
    session = create_session(db_session, test_user.id)

    with pytest.raises(HTTPException) as exc:
        update_workout_session(
            db_session, session.id, WorkoutSessionUpdate(user_id=2_000_000_000)
        )

    assert exc.value.status_code == 404


def test_update_raises_404_when_new_week_missing(db_session, test_user):
    session = create_session(db_session, test_user.id)

    with pytest.raises(HTTPException) as exc:
        update_workout_session(
            db_session, session.id, WorkoutSessionUpdate(week_id=2_000_000_000)
        )

    assert exc.value.status_code == 404


def test_update_raises_422_when_closing_without_closed_at(db_session, test_user):
    session = create_session(db_session, test_user.id)

    with pytest.raises(HTTPException) as exc:
        update_workout_session(
            db_session, session.id, WorkoutSessionUpdate(status="CERRADO")
        )

    assert exc.value.status_code == 422


def test_update_closes_session_with_closed_at(db_session, test_user):
    session = create_session(db_session, test_user.id)

    result = update_workout_session(
        db_session,
        session.id,
        WorkoutSessionUpdate(
            status="CERRADO",
            closed_at=datetime(2026, 11, 21, 22, 0, 0),
        ),
    )

    assert result.status == "CERRADO"
    assert result.closed_at is not None


def test_update_raises_422_when_opening_with_closed_at(db_session, test_user):
    session = create_session(
        db_session,
        test_user.id,
        status="CERRADO",
        closed_at=datetime(2026, 11, 21, 22, 0, 0),
    )

    with pytest.raises(HTTPException) as exc:
        update_workout_session(
            db_session, session.id, WorkoutSessionUpdate(status="ABIERTO")
        )

    assert exc.value.status_code == 422


def test_delete_removes_and_commits(db_session, test_user):
    session = create_session(db_session, test_user.id)

    delete_workout_session(db_session, session.id)

    with pytest.raises(HTTPException) as exc:
        get_workout_session_by_id(db_session, session.id)
    assert exc.value.status_code == 404


def test_delete_raises_404_when_missing(db_session):
    with pytest.raises(HTTPException) as exc:
        delete_workout_session(db_session, 2_000_000_000)

    assert exc.value.status_code == 404


def test_list_orders_by_session_date_then_id(db_session, test_user):
    older = create_session(db_session, test_user.id, session_date=date(2026, 1, 1))
    newer = create_session(db_session, test_user.id, session_date=date(2026, 2, 1))

    result = get_workout_sessions(db_session, user_id=test_user.id, skip=0, limit=500)

    ids = [session.id for session in result]
    assert ids.index(newer.id) < ids.index(older.id)


def test_create_rejects_training_week_from_another_user(db_session, test_user):
    other = create_user(db_session)
    other_week = create_week(db_session, other.id)

    with pytest.raises(HTTPException) as exc:
        create_session(db_session, test_user.id, week_id=other_week.id)

    assert exc.value.status_code == 422


def test_update_rejects_training_week_from_another_user(db_session, test_user):
    other = create_user(db_session)
    other_week = create_week(db_session, other.id)
    session = create_session(db_session, test_user.id)

    with pytest.raises(HTTPException) as exc:
        update_workout_session(
            db_session, session.id, WorkoutSessionUpdate(week_id=other_week.id)
        )

    assert exc.value.status_code == 422


def test_create_rejects_21st_public_session_for_cliente(db_session, test_user):
    seed_public_sessions(db_session, test_user.id, 20)

    with pytest.raises(HTTPException) as exc:
        create_session(db_session, test_user.id, public=True)

    assert exc.value.status_code == 422


def test_create_allows_public_session_for_admin(db_session):
    admin = create_user(db_session, role=RoleUser.ADMIN)
    seed_public_sessions(db_session, admin.id, 20)

    result = create_session(db_session, admin.id, public=True)

    assert result.public is True


def test_update_rejects_publishing_over_cliente_quota(db_session, test_user):
    seed_public_sessions(db_session, test_user.id, 20)
    session = create_session(db_session, test_user.id, public=False)

    with pytest.raises(HTTPException) as exc:
        update_workout_session(
            db_session, session.id, WorkoutSessionUpdate(public=True)
        )

    assert exc.value.status_code == 422
