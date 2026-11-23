from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from app.controllers.workout_session_controller import (
    create_workout_session,
    delete_workout_session,
    get_workout_session_by_id,
    get_workout_sessions,
    update_workout_session,
)
from app.models.app_user_model import AppUserModel, RoleUser
from app.models.mesocycle_model import MesocycleModel
from app.models.training_week_model import TrainingWeekModel
from app.models.workout_session_model import SessionStatus, WorkoutSessionModel
from app.schemas.workout_session_schema import WorkoutSessionCreate, WorkoutSessionUpdate


def make_session(
    session_id: int = 1,
    status: SessionStatus = SessionStatus.ABIERTO,
    closed_at: datetime | None = None,
    title: str = "Sesion",
) -> WorkoutSessionModel:
    return WorkoutSessionModel(
        id=session_id,
        user_id=1,
        week_id=None,
        title=title,
        session_date=date(2026, 11, 21),
        current_bodyweight_kg=Decimal("60.50"),
        observation="Prueba",
        public=False,
        status=status,
        closed_at=closed_at,
    )


def make_db(
    user_exists: bool = True,
    week_exists: bool = True,
    session=None,
    role: RoleUser = RoleUser.CLIENTE,
    public_count: int = 0,
    week_owner_id: int = 1,
) -> MagicMock:
    db = MagicMock()

    user = MagicMock()
    user.id = 1
    user.role = role

    week = MagicMock()
    week.mesocycle_id = 10
    mesocycle = MagicMock()
    mesocycle.user_id = week_owner_id

    def fake_get(model, ident):
        if model is AppUserModel:
            return user if user_exists else None
        if model is TrainingWeekModel:
            return week if week_exists else None
        if model is MesocycleModel:
            return mesocycle if week_exists else None
        if model is WorkoutSessionModel:
            return session
        return None

    db.get.side_effect = fake_get
    db.scalar.return_value = public_count
    return db


def test_create_commits_when_user_exists():
    db = make_db()
    payload = WorkoutSessionCreate(user_id=1, session_date=date(2026, 11, 21))

    result = create_workout_session(db, payload)

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(result)
    assert result.user_id == 1


def test_create_commits_with_training_week():
    db = make_db()
    payload = WorkoutSessionCreate(
        user_id=1,
        week_id=1,
        session_date=date(2026, 11, 21),
    )

    result = create_workout_session(db, payload)

    assert result.week_id == 1
    db.commit.assert_called_once()


def test_create_raises_404_when_user_missing():
    db = make_db(user_exists=False)
    payload = WorkoutSessionCreate(user_id=999, session_date=date(2026, 11, 21))

    with pytest.raises(HTTPException) as exc:
        create_workout_session(db, payload)

    assert exc.value.status_code == 404
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_create_raises_404_when_week_missing():
    db = make_db(week_exists=False)
    payload = WorkoutSessionCreate(
        user_id=1,
        week_id=999,
        session_date=date(2026, 11, 21),
    )

    with pytest.raises(HTTPException) as exc:
        create_workout_session(db, payload)

    assert exc.value.status_code == 404
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_get_by_id_returns_session():
    db = make_db(session=make_session(session_id=7))

    result = get_workout_session_by_id(db, 7)

    assert result.id == 7


def test_get_by_id_raises_404_when_missing():
    db = make_db()

    with pytest.raises(HTTPException) as exc:
        get_workout_session_by_id(db, 99)

    assert exc.value.status_code == 404


def test_list_returns_sessions():
    db = make_db()
    db.scalars.return_value.all.return_value = [make_session()]

    result = get_workout_sessions(db, user_id=1, skip=5, limit=10)

    assert len(result) == 1
    assert result[0].id == 1
    db.scalars.assert_called_once()


def test_update_changes_title():
    session = make_session()
    db = make_db(session=session)

    result = update_workout_session(db, 1, WorkoutSessionUpdate(title="Nuevo titulo"))

    assert result.title == "Nuevo titulo"
    db.commit.assert_called_once()


def test_update_raises_404_when_session_missing():
    db = make_db()

    with pytest.raises(HTTPException) as exc:
        update_workout_session(db, 99, WorkoutSessionUpdate(title="Nuevo titulo"))

    assert exc.value.status_code == 404


def test_update_raises_404_when_new_user_missing():
    db = make_db(user_exists=False, session=make_session())

    with pytest.raises(HTTPException) as exc:
        update_workout_session(db, 1, WorkoutSessionUpdate(user_id=999))

    assert exc.value.status_code == 404
    db.commit.assert_not_called()


def test_update_raises_404_when_new_week_missing():
    db = make_db(week_exists=False, session=make_session())

    with pytest.raises(HTTPException) as exc:
        update_workout_session(db, 1, WorkoutSessionUpdate(week_id=999))

    assert exc.value.status_code == 404
    db.commit.assert_not_called()


def test_update_raises_422_when_closing_without_closed_at():
    db = make_db(session=make_session())

    with pytest.raises(HTTPException) as exc:
        update_workout_session(
            db,
            1,
            WorkoutSessionUpdate(status="CERRADO"),
        )

    assert exc.value.status_code == 422
    db.commit.assert_not_called()


def test_update_closes_session_with_closed_at():
    db = make_db(session=make_session())

    result = update_workout_session(
        db,
        1,
        WorkoutSessionUpdate(
            status="CERRADO",
            closed_at=datetime(2026, 11, 21, 22, 0, 0),
        ),
    )

    assert result.status == "CERRADO"
    db.commit.assert_called_once()


def test_update_raises_422_when_opening_with_closed_at():
    db = make_db(
        session=make_session(
            status=SessionStatus.CERRADO,
            closed_at=datetime(2026, 11, 21, 22, 0, 0),
        )
    )

    with pytest.raises(HTTPException) as exc:
        update_workout_session(db, 1, WorkoutSessionUpdate(status="ABIERTO"))

    assert exc.value.status_code == 422
    db.commit.assert_not_called()


def test_delete_removes_and_commits():
    session = make_session()
    db = make_db(session=session)

    delete_workout_session(db, 1)

    db.delete.assert_called_once_with(session)
    db.commit.assert_called_once()


def test_delete_raises_404_when_missing():
    db = make_db()

    with pytest.raises(HTTPException) as exc:
        delete_workout_session(db, 99)

    assert exc.value.status_code == 404


def test_list_orders_by_session_date_then_id():
    db = make_db()
    db.scalars.return_value.all.return_value = []

    get_workout_sessions(db)

    query = str(db.scalars.call_args.args[0])
    assert "ORDER BY workout_session.session_date DESC, workout_session.id DESC" in query


def test_create_rejects_training_week_from_another_user():
    db = make_db(week_owner_id=2)
    payload = WorkoutSessionCreate(user_id=1, week_id=1, session_date=date(2026, 11, 21))

    with pytest.raises(HTTPException) as exc:
        create_workout_session(db, payload)

    assert exc.value.status_code == 422
    db.commit.assert_not_called()


def test_update_rejects_training_week_from_another_user():
    db = make_db(session=make_session(), week_owner_id=2)

    with pytest.raises(HTTPException) as exc:
        update_workout_session(db, 1, WorkoutSessionUpdate(week_id=1))

    assert exc.value.status_code == 422
    db.commit.assert_not_called()


def test_create_rejects_21st_public_session_for_cliente():
    db = make_db(public_count=20)
    payload = WorkoutSessionCreate(user_id=1, session_date=date(2026, 11, 21), public=True)

    with pytest.raises(HTTPException) as exc:
        create_workout_session(db, payload)

    assert exc.value.status_code == 422
    db.commit.assert_not_called()


def test_create_allows_public_session_for_admin():
    db = make_db(role=RoleUser.ADMIN, public_count=20)
    payload = WorkoutSessionCreate(user_id=1, session_date=date(2026, 11, 21), public=True)

    result = create_workout_session(db, payload)

    assert result.public is True
    db.commit.assert_called_once()


def test_update_rejects_publishing_over_cliente_quota():
    db = make_db(session=make_session(), public_count=20)

    with pytest.raises(HTTPException) as exc:
        update_workout_session(db, 1, WorkoutSessionUpdate(public=True))

    assert exc.value.status_code == 422
    db.commit.assert_not_called()
