from uuid import uuid4

from sqlalchemy import func

from app.core.security import verify_password
from app.models.app_user_model import AppUserModel, RoleUser, UserStatus
from seeders.admin_seeder import DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD, seed_admin
from seeders import run as seeder_run


def test_seed_admin_creates_default_admin_and_is_idempotent(db_session, monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

    # Asegurar que el email por defecto no exista dentro de esta transacción de prueba
    db_session.query(AppUserModel).filter(
        func.lower(AppUserModel.email) == DEFAULT_ADMIN_EMAIL.lower()
    ).delete(synchronize_session=False)
    db_session.commit()

    created = seed_admin(db_session)

    assert created is not None
    assert created.email == DEFAULT_ADMIN_EMAIL
    assert created.role == RoleUser.ADMIN
    assert created.role == "ADMIN"
    assert created.status == UserStatus.ACTIVO
    assert created.status == "ACTIVO"
    assert created.password_hash.startswith("$argon2")
    assert verify_password(DEFAULT_ADMIN_PASSWORD, created.password_hash)

    # Ejecutar de nuevo no debe duplicar ni crear otro registro
    duplicate = seed_admin(db_session)
    assert duplicate is None

    # Comprobación insensible a mayúsculas/minúsculas
    monkeypatch.setenv("ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL.upper())
    duplicate_case = seed_admin(db_session)
    assert duplicate_case is None


def test_seed_admin_uses_env_variables(db_session, monkeypatch):
    custom_email = f"custom_admin_{uuid4().hex}@volumelab.com"
    custom_password = "SuperSecurePassword2026!"
    monkeypatch.setenv("ADMIN_EMAIL", custom_email)
    monkeypatch.setenv("ADMIN_PASSWORD", custom_password)

    created = seed_admin(db_session)

    assert created is not None
    assert created.email == custom_email
    assert created.role == "ADMIN"
    assert created.status == "ACTIVO"
    assert created.password_hash.startswith("$argon2")
    assert verify_password(custom_password, created.password_hash)


def test_seeder_run_registers_admin_and_removes_test(monkeypatch, capsys):
    calls = []

    class DummySession:
        def close(self):
            calls.append("close")

    dummy_admin = AppUserModel(
        email="admin@volumelab.com",
        password_hash="$argon2id$dummy",
        name="Administrador",
        role=RoleUser.ADMIN,
        status=UserStatus.ACTIVO,
    )

    monkeypatch.setattr(seeder_run, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr(seeder_run, "seed_admin", lambda db: calls.append("admin") or dummy_admin)
    monkeypatch.setattr("sys.argv", ["seeders.run", "--entity", "admin"])

    seeder_run.main()

    captured = capsys.readouterr()
    assert calls == ["admin", "close"]
    assert "Seeded admin user: admin@volumelab.com" in captured.out
