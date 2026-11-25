from uuid import uuid4

from app.core.security import hash_password
from app.models.app_user_model import AppUserModel


def test_register_creates_active_cliente(client):
    email = f"nuevo_{uuid4().hex}@volumelab.com"
    payload = {
        "name": "Nuevo",
        "lastname": "Usuario",
        "email": email,
        "password": "Password123!",
        "gender": "PREFIERO NO DECIR",
        "height_cm": 175,
    }

    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["email"] == email.lower()
    assert data["role"] == "CLIENTE"
    assert data["status"] == "ACTIVO"
    assert "password" not in data
    assert "password_hash" not in data


def test_register_rejects_forbidden_fields(client):
    email = f"hacker_{uuid4().hex}@volumelab.com"

    # Intento de enviar role ADMIN
    response = client.post(
        "/auth/register",
        json={"name": "Hacker", "email": email, "password": "Password123!", "role": "ADMIN"},
    )
    assert response.status_code == 422

    # Intento de enviar password_hash
    response = client.post(
        "/auth/register",
        json={"name": "Hacker", "email": email, "password": "Password123!", "password_hash": "hash"},
    )
    assert response.status_code == 422

    # Intento de enviar status
    response = client.post(
        "/auth/register",
        json={"name": "Hacker", "email": email, "password": "Password123!", "status": "ACTIVO"},
    )
    assert response.status_code == 422


def test_register_duplicate_email_returns_409(client):
    email = f"dup_{uuid4().hex}@volumelab.com"
    payload = {"name": "Usuario", "email": email, "password": "Password123!"}

    assert client.post("/auth/register", json=payload).status_code == 201

    response = client.post("/auth/register", json={**payload, "email": email.upper()})
    assert response.status_code == 409


def test_register_short_password_returns_422(client):
    response = client.post(
        "/auth/register",
        json={"name": "Usuario", "email": f"u_{uuid4().hex}@volumelab.com", "password": "short"},
    )
    assert response.status_code == 422


def test_login_success_returns_token(client, db_session):
    email = f"login_user_{uuid4().hex}@volumelab.com"
    user = AppUserModel(
        email=email,
        password_hash=hash_password("Password123!"),
        name="Login",
        role="CLIENTE",
        status="ACTIVO",
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600


def test_login_invalid_password_returns_401(client, db_session):
    email = f"user_{uuid4().hex}@volumelab.com"
    user = AppUserModel(
        email=email,
        password_hash=hash_password("Password123!"),
        name="User",
        role="CLIENTE",
        status="ACTIVO",
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/auth/login",
        json={"email": email, "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales inválidas"
    assert "Bearer" in response.headers.get("www-authenticate", "")


def test_login_nonexistent_email_returns_same_401(client):
    response = client.post(
        "/auth/login",
        json={"email": "nonexistent@volumelab.com", "password": "Password123!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales inválidas"


def test_login_blocked_user_returns_403(client, db_session):
    email = f"blocked_{uuid4().hex}@volumelab.com"
    user = AppUserModel(
        email=email,
        password_hash=hash_password("Password123!"),
        name="Blocked",
        role="CLIENTE",
        status="BLOQUEADO",
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Usuario bloqueado"


def test_auth_me_with_valid_token(user_client, client_user):
    response = user_client.get("/auth/me")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == client_user.id
    assert data["email"] == client_user.email
    assert "password" not in data
    assert "password_hash" not in data


def test_auth_me_without_token_returns_401(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert "www-authenticate" in response.headers


def test_auth_me_with_malformed_token_returns_401(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-valid-jwt-token"})
    assert response.status_code == 401
