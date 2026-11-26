from uuid import uuid4

import pytest

from app.core.config import settings


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


@pytest.mark.parametrize("field, value", [
    ("role", "ADMIN"), ("password_hash", "stored-hash"), ("status", "ACTIVO"),
])
def test_register_rejects_forbidden_fields(client, field, value):
    email = f"hacker_{uuid4().hex}@volumelab.com"

    response = client.post(
        "/auth/register",
        json={"name": "New member", "email": email, "password": "Password123!", field: value},
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


def test_login_success_returns_token(client, client_user):
    response = client.post(
        "/auth/login",
        json={"email": client_user.email, "password": "Client1234!"},
    )
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_login_invalid_password_returns_401(client, client_user):
    response = client.post(
        "/auth/login",
        json={"email": client_user.email, "password": "WrongPassword!"},
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


def test_login_blocked_user_returns_403(client, user_factory):
    user = user_factory(status="BLOQUEADO")

    response = client.post(
        "/auth/login",
        json={"email": user.email, "password": "Client1234!"},
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
