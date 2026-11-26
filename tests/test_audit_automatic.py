from uuid import uuid4

from app.core.security import hash_password
from app.models.app_user_model import AppUserModel
from app.models.audit_model import AuditAction, AuditModel
from tests.conftest import create_auth_headers


def _get_audits(db_session, *, entity: str, record_id: str) -> list[AuditModel]:
    return (
        db_session.query(AuditModel)
        .filter(AuditModel.entity == entity, AuditModel.record_id == record_id)
        .order_by(AuditModel.id.asc())
        .all()
    )


def test_audit_auth_register_records_insert_with_new_user_id(client, db_session):
    email = f"audit_reg_{uuid4().hex}@volumelab.com"
    response = client.post(
        "/auth/register",
        json={"name": "Registro", "email": email, "password": "Password123!"},
    )
    assert response.status_code == 201
    new_user_id = response.json()["id"]

    audits = _get_audits(db_session, entity="app_user", record_id=str(new_user_id))
    assert len(audits) == 1
    assert audits[0].action == AuditAction.INSERT
    assert audits[0].user_id == new_user_id
    assert audits[0].endpoint == "POST /auth/register"


def test_audit_app_user_admin_crud_and_delete_records_admin_id(admin_client, admin_user, db_session):
    email = f"audit_usr_{uuid4().hex}@volumelab.com"
    create_res = admin_client.post(
        "/app-users/",
        json={"name": "Managed", "email": email, "password": "Password123!"},
    )
    assert create_res.status_code == 201
    target_id = create_res.json()["id"]

    update_res = admin_client.put(f"/app-users/{target_id}", json={"name": "Updated"})
    assert update_res.status_code == 200

    delete_res = admin_client.delete(f"/app-users/{target_id}")
    assert delete_res.status_code == 204

    audits = _get_audits(db_session, entity="app_user", record_id=str(target_id))
    assert [a.action for a in audits] == [
        AuditAction.INSERT,
        AuditAction.UPDATE,
        AuditAction.DELETE,
    ]
    assert all(a.user_id == admin_user.id for a in audits)
    assert audits[0].endpoint == "POST /app-users/"
    assert audits[1].endpoint == f"PUT /app-users/{target_id}"
    assert audits[2].endpoint == f"DELETE /app-users/{target_id}"


def test_audit_app_user_client_self_delete_records_null_user_id(client, db_session):
    user = AppUserModel(
        email=f"audit_selfdel_{uuid4().hex}@volumelab.com",
        password_hash=hash_password("Password123!"),
        name="SelfDelete",
        role="CLIENTE",
        status="ACTIVO",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    user_id = user.id

    client.headers.update(create_auth_headers(user))
    delete_res = client.delete(f"/app-users/{user_id}")
    assert delete_res.status_code == 204

    audits = _get_audits(db_session, entity="app_user", record_id=str(user_id))
    assert len(audits) == 1
    assert audits[0].action == AuditAction.DELETE
    assert audits[0].user_id is None
    assert audits[0].endpoint == f"DELETE /app-users/{user_id}"


def test_audit_workout_muscle_group_and_muscle_workout_crud(admin_client, admin_user, db_session):
    suffix = uuid4().hex[:8]

    mg_create = admin_client.post(
        "/muscle-groups/",
        json={"name": f"MG {suffix}", "created_by": admin_user.id},
    )
    assert mg_create.status_code == 201
    mg_id = mg_create.json()["id"]

    mg_update = admin_client.put(
        f"/muscle-groups/{mg_id}",
        json={"description": "Actualizado"},
    )
    assert mg_update.status_code == 200

    w_create = admin_client.post(
        "/workouts/",
        json={
            "name": f"Workout {suffix}",
            "type": "DINAMICO",
            "created_by": admin_user.id,
            "public": True,
        },
    )
    assert w_create.status_code == 201
    w_id = w_create.json()["id"]

    w_update = admin_client.put(f"/workouts/{w_id}", json={"description": "Desc"})
    assert w_update.status_code == 200

    mw_create = admin_client.post(
        "/muscle-workouts/",
        json={
            "workout_id": w_id,
            "muscle_group_id": mg_id,
            "muscle_role": "PRIMARIO",
        },
    )
    assert mw_create.status_code == 201

    mw_update = admin_client.put(
        f"/muscle-workouts/{w_id}/{mg_id}",
        json={"muscle_role": "SECUNDARIO"},
    )
    assert mw_update.status_code == 200

    mw_delete = admin_client.delete(f"/muscle-workouts/{w_id}/{mg_id}")
    assert mw_delete.status_code == 204

    w_delete = admin_client.delete(f"/workouts/{w_id}")
    assert w_delete.status_code == 204

    mg_delete = admin_client.delete(f"/muscle-groups/{mg_id}")
    assert mg_delete.status_code == 204

    for entity, record_id in (
        ("muscle_group", str(mg_id)),
        ("workout", str(w_id)),
        ("muscle_workout", f"{w_id}:{mg_id}"),
    ):
        audits = _get_audits(db_session, entity=entity, record_id=record_id)
        assert [a.action for a in audits] == [
            AuditAction.INSERT,
            AuditAction.UPDATE,
            AuditAction.DELETE,
        ]
        assert all(a.user_id == admin_user.id for a in audits)


def test_audit_weight_history_mesocycle_week_session_set_crud(
    user_client, client_user, db_session
):
    suffix = uuid4().hex[:8]

    # weight_history
    wh_create = user_client.post(
        "/weight-history/",
        json={"user_id": client_user.id, "weight_kg": "75.50"},
    )
    assert wh_create.status_code == 201
    wh_id = wh_create.json()["id"]
    assert user_client.put(f"/weight-history/{wh_id}", json={"weight_kg": "76.00"}).status_code == 200
    assert user_client.delete(f"/weight-history/{wh_id}").status_code == 204

    # mesocycle
    m_create = user_client.post(
        "/mesocycles/",
        json={
            "user_id": client_user.id,
            "name": f"Meso {suffix}",
            "start_date": "2026-01-01",
            "end_date": "2026-03-31",
            "status": "PLANIFICADO",
        },
    )
    assert m_create.status_code == 201
    m_id = m_create.json()["id"]
    assert user_client.put(f"/mesocycles/{m_id}", json={"name": f"Meso Upd {suffix}"}).status_code == 200

    # training_week
    tw_create = user_client.post(
        "/training-weeks/",
        json={
            "mesocycle_id": m_id,
            "week_order": 1,
            "start_date": "2026-01-01",
            "end_date": "2026-01-07",
        },
    )
    assert tw_create.status_code == 201
    tw_id = tw_create.json()["id"]
    assert user_client.put(f"/training-weeks/{tw_id}", json={"week_order": 2}).status_code == 200

    # workout (for workout_set)
    w_create = user_client.post(
        "/workouts/",
        json={
            "name": f"Press {suffix}",
            "type": "DINAMICO",
            "created_by": client_user.id,
            "is_bodyweight": False,
            "allow_positive_ballast": True,
            "allow_negative_ballast": False,
            "public": False,
        },
    )
    assert w_create.status_code == 201
    w_id = w_create.json()["id"]

    # workout_session
    ws_create = user_client.post(
        "/workout-sessions/",
        json={
            "user_id": client_user.id,
            "week_id": tw_id,
            "title": f"Session {suffix}",
            "session_date": "2026-01-02",
            "current_bodyweight_kg": "75.00",
            "public": False,
            "status": "ABIERTO",
        },
    )
    assert ws_create.status_code == 201
    ws_id = ws_create.json()["id"]
    assert user_client.put(f"/workout-sessions/{ws_id}", json={"title": f"Session Upd {suffix}"}).status_code == 200

    # workout_set
    set_create = user_client.post(
        "/workout-sets/",
        json={
            "session_id": ws_id,
            "exercise_id": w_id,
            "exercise_order": 1,
            "set_number": 1,
            "added_weight_kg": "80.00",
            "reps": 8,
            "rir": 2,
            "completed": True,
        },
    )
    assert set_create.status_code == 201
    set_id = set_create.json()["id"]
    assert user_client.put(f"/workout-sets/{set_id}", json={"reps": 10}).status_code == 200
    assert user_client.delete(f"/workout-sets/{set_id}").status_code == 204

    assert user_client.delete(f"/workout-sessions/{ws_id}").status_code == 204
    assert user_client.delete(f"/training-weeks/{tw_id}").status_code == 204
    assert user_client.delete(f"/mesocycles/{m_id}").status_code == 204

    for entity, record_id in (
        ("weight_history", str(wh_id)),
        ("mesocycle", str(m_id)),
        ("training_week", str(tw_id)),
        ("workout_session", str(ws_id)),
        ("workout_set", str(set_id)),
    ):
        audits = _get_audits(db_session, entity=entity, record_id=record_id)
        assert [a.action for a in audits] == [
            AuditAction.INSERT,
            AuditAction.UPDATE,
            AuditAction.DELETE,
        ]
        assert all(a.user_id == client_user.id for a in audits)


def test_audit_workout_rate_and_session_rate_crud_and_upsert(
    user_client, client_user, db_session
):
    suffix = uuid4().hex[:8]

    w_res = user_client.post(
        "/workouts/",
        json={
            "name": f"PublicW {suffix}",
            "type": "DINAMICO",
            "created_by": client_user.id,
            "public": True,
        },
    )
    assert w_res.status_code == 201
    w_id = w_res.json()["id"]

    ws_res = user_client.post(
        "/workout-sessions/",
        json={
            "user_id": client_user.id,
            "title": f"PublicS {suffix}",
            "session_date": "2026-01-03",
            "current_bodyweight_kg": "75.00",
            "public": True,
            "status": "ABIERTO",
        },
    )
    assert ws_res.status_code == 201
    ws_id = ws_res.json()["id"]

    # workout_rate upsert (INSERT -> UPDATE) + PUT + DELETE
    wr_upsert_1 = user_client.post(
        "/workout-rates/upsert",
        json={"id_workout": w_id, "user_id": client_user.id, "rate": 4},
    )
    assert wr_upsert_1.status_code == 200
    wr_id = wr_upsert_1.json()["id"]

    wr_upsert_2 = user_client.post(
        "/workout-rates/upsert",
        json={"id_workout": w_id, "user_id": client_user.id, "rate": 5},
    )
    assert wr_upsert_2.status_code == 200
    assert wr_upsert_2.json()["id"] == wr_id

    assert user_client.put(f"/workout-rates/{wr_id}", json={"rate": 3}).status_code == 200
    assert user_client.delete(f"/workout-rates/{wr_id}").status_code == 204

    wr_audits = _get_audits(db_session, entity="workout_rate", record_id=str(wr_id))
    assert [a.action for a in wr_audits] == [
        AuditAction.INSERT,
        AuditAction.UPDATE,
        AuditAction.UPDATE,
        AuditAction.DELETE,
    ]
    assert wr_audits[0].endpoint == "POST /workout-rates/upsert"
    assert wr_audits[1].endpoint == "POST /workout-rates/upsert"
    assert wr_audits[2].endpoint == f"PUT /workout-rates/{wr_id}"
    assert wr_audits[3].endpoint == f"DELETE /workout-rates/{wr_id}"
    assert all(a.user_id == client_user.id for a in wr_audits)

    # session_rate upsert (INSERT -> UPDATE) + PUT + DELETE
    sr_upsert_1 = user_client.post(
        "/session-rates/upsert",
        json={"id_workout_session": ws_id, "user_id": client_user.id, "rate": 4},
    )
    assert sr_upsert_1.status_code == 200
    sr_id = sr_upsert_1.json()["id"]

    sr_upsert_2 = user_client.post(
        "/session-rates/upsert",
        json={"id_workout_session": ws_id, "user_id": client_user.id, "rate": 5},
    )
    assert sr_upsert_2.status_code == 200
    assert sr_upsert_2.json()["id"] == sr_id

    assert user_client.put(f"/session-rates/{sr_id}", json={"rate": 2}).status_code == 200
    assert user_client.delete(f"/session-rates/{sr_id}").status_code == 204

    sr_audits = _get_audits(db_session, entity="session_rate", record_id=str(sr_id))
    assert [a.action for a in sr_audits] == [
        AuditAction.INSERT,
        AuditAction.UPDATE,
        AuditAction.UPDATE,
        AuditAction.DELETE,
    ]
    assert sr_audits[0].endpoint == "POST /session-rates/upsert"
    assert sr_audits[1].endpoint == "POST /session-rates/upsert"
    assert sr_audits[2].endpoint == f"PUT /session-rates/{sr_id}"
    assert sr_audits[3].endpoint == f"DELETE /session-rates/{sr_id}"
    assert all(a.user_id == client_user.id for a in sr_audits)


    # Direct POST /workout-rates/ and POST /session-rates/ also record INSERT
    wr_direct = user_client.post(
        "/workout-rates/",
        json={"id_workout": w_id, "user_id": client_user.id, "rate": 5},
    )
    assert wr_direct.status_code == 201
    wr_direct_id = wr_direct.json()["id"]
    wr_direct_audits = _get_audits(db_session, entity="workout_rate", record_id=str(wr_direct_id))
    assert len(wr_direct_audits) == 1
    assert wr_direct_audits[0].action == AuditAction.INSERT
    assert wr_direct_audits[0].endpoint == "POST /workout-rates/"

    sr_direct = user_client.post(
        "/session-rates/",
        json={"id_workout_session": ws_id, "user_id": client_user.id, "rate": 5},
    )
    assert sr_direct.status_code == 201
    sr_direct_id = sr_direct.json()["id"]
    sr_direct_audits = _get_audits(db_session, entity="session_rate", record_id=str(sr_direct_id))
    assert len(sr_direct_audits) == 1
    assert sr_direct_audits[0].action == AuditAction.INSERT
    assert sr_direct_audits[0].endpoint == "POST /session-rates/"


def test_failed_mutation_does_not_create_audit_entry(user_client, client_user, db_session):
    before_count = db_session.query(AuditModel).filter(AuditModel.user_id == client_user.id).count()

    # Forbidden: client trying to create a muscle_group
    res = user_client.post(
        "/muscle-groups/",
        json={"name": f"Forbidden {uuid4().hex[:6]}", "created_by": client_user.id},
    )
    assert res.status_code == 403

    # Not found: updating nonexistent mesocycle
    res2 = user_client.put("/mesocycles/999999999", json={"name": "Nope"})
    assert res2.status_code == 404

    after_count = db_session.query(AuditModel).filter(AuditModel.user_id == client_user.id).count()
    assert after_count == before_count
