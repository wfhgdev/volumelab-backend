from uuid import uuid4

from app.core.security import hash_password
from app.models.app_user_model import AppUserModel


def test_client_cannot_create_app_user(user_client):
    response = user_client.post(
        "/app-users/",
        json={
            "name": "Intruso",
            "email": f"intruso_{uuid4().hex}@volumelab.com",
            "password": "Password123!",
        },
    )
    assert response.status_code == 403


def test_client_cannot_list_app_users(user_client):
    response = user_client.get("/app-users/")
    assert response.status_code == 403


def test_client_can_get_own_profile(user_client, client_user):
    response = user_client.get(f"/app-users/{client_user.id}")
    assert response.status_code == 200
    assert response.json()["id"] == client_user.id


def test_client_cannot_get_other_profile_returns_404(user_client, other_client_user):
    response = user_client.get(f"/app-users/{other_client_user.id}")
    assert response.status_code == 404


def test_client_can_update_own_name(user_client, client_user):
    response = user_client.put(
        f"/app-users/{client_user.id}",
        json={"name": "NuevoNombre"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "NuevoNombre"


def test_client_cannot_update_role_or_status(user_client, client_user):
    response = user_client.put(
        f"/app-users/{client_user.id}",
        json={"role": "ADMIN"},
    )
    assert response.status_code == 403
    assert "administrador" in response.json()["detail"].lower()

    response = user_client.put(
        f"/app-users/{client_user.id}",
        json={"status": "BLOQUEADO"},
    )
    assert response.status_code == 403


def test_client_cannot_update_other_user_returns_404(user_client, other_client_user):
    response = user_client.put(
        f"/app-users/{other_client_user.id}",
        json={"name": "Hacked"},
    )
    assert response.status_code == 404


def test_client_can_delete_own_account(client, db_session):
    # Crear un usuario cliente específico para eliminar
    email = f"autodelete_{uuid4().hex}@volumelab.com"
    user = AppUserModel(
        email=email,
        password_hash=hash_password("Password123!"),
        name="AutoDelete",
        role="CLIENTE",
        status="ACTIVO",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    from tests.conftest import create_auth_headers
    client.headers.update(create_auth_headers(user))

    response = client.delete(f"/app-users/{user.id}")
    assert response.status_code == 204

    # Verificar que el usuario ya no existe
    assert db_session.get(AppUserModel, user.id) is None


def test_client_cannot_delete_other_user_returns_404(user_client, other_client_user):
    response = user_client.delete(f"/app-users/{other_client_user.id}")
    assert response.status_code == 404


def test_admin_full_crud_on_app_users(admin_client, db_session):
    email = f"managed_{uuid4().hex}@volumelab.com"
    # Crear como ADMIN
    create_res = admin_client.post(
        "/app-users/",
        json={
            "name": "Managed",
            "email": email,
            "password": "Password123!",
            "role": "CLIENTE",
            "status": "ACTIVO",
        },
    )
    assert create_res.status_code == 201
    user_id = create_res.json()["id"]

    # Listar como ADMIN
    list_res = admin_client.get("/app-users/")
    assert list_res.status_code == 200

    # Consultar como ADMIN
    get_res = admin_client.get(f"/app-users/{user_id}")
    assert get_res.status_code == 200

    # Modificar rol y status como ADMIN
    update_res = admin_client.put(
        f"/app-users/{user_id}",
        json={"role": "ADMIN", "status": "BLOQUEADO"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["role"] == "ADMIN"
    assert update_res.json()["status"] == "BLOQUEADO"

    # Eliminar como ADMIN
    delete_res = admin_client.delete(f"/app-users/{user_id}")
    assert delete_res.status_code == 204
