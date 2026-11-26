from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token, verify_password
from app.models.app_user_model import AppUserModel
from app.models.audit_model import AuditAction, AuditModel


scenarios("../features/auth.feature")


@pytest.fixture
def auth_context(client, db_session, user_factory):
    return {
        "client": client,
        "db": db_session,
        "user_factory": user_factory,
        "payload": {
            "name": "New member", "email": f"member_{uuid4().hex}@example.com", "password": "Client1234!",
        },
    }


@given("the authentication API is available")
def authentication_api_available(auth_context):
    assert "Authorization" not in auth_context["client"].headers


@given(parsers.parse('an account with role "{role}" and status "{status}"'))
def existing_account(auth_context, role, status):
    auth_context["user"] = auth_context["user_factory"](role=role, status=status)


@when("I register a new account")
def register_account(auth_context):
    auth_context["response"] = auth_context["client"].post("/auth/register", json=auth_context["payload"])


@when(parsers.parse('I register with the forbidden field "{field}" set to "{value}"'))
def register_with_forbidden_field(auth_context, field, value):
    payload = {**auth_context["payload"], field: value}
    auth_context["response"] = auth_context["client"].post("/auth/register", json=payload)


@when("I register with the existing email in uppercase")
def register_duplicate_email(auth_context):
    payload = {**auth_context["payload"], "email": auth_context["user"].email.upper()}
    auth_context["response"] = auth_context["client"].post("/auth/register", json=payload)


@when("I sign in with the account credentials")
def sign_in(auth_context):
    auth_context["response"] = auth_context["client"].post("/auth/login", json={
        "email": auth_context["user"].email.upper(), "password": "Client1234!",
    })


@when("I sign in with an incorrect password")
def sign_in_with_incorrect_password(auth_context):
    auth_context["response"] = auth_context["client"].post("/auth/login", json={
        "email": auth_context["user"].email, "password": "Incorrect1234!",
    })


@when("I sign in with an unknown email")
def sign_in_with_unknown_email(auth_context):
    auth_context["response"] = auth_context["client"].post("/auth/login", json={
        "email": auth_context["payload"]["email"], "password": "Client1234!",
    })


@when("I request my profile without a token")
def request_profile_without_token(auth_context):
    auth_context["response"] = auth_context["client"].get("/auth/me")


@when(parsers.parse('I request my profile with a "{kind}" token'))
def request_profile_with_invalid_token(auth_context, kind):
    payload = decode_access_token(create_access_token(auth_context["user"].id, "CLIENTE"))
    key = settings.SECRET_KEY
    if kind == "expired":
        past = datetime.now(timezone.utc) - timedelta(minutes=10)
        payload.update(iat=int((past - timedelta(minutes=5)).timestamp()), exp=int(past.timestamp()))
    elif kind == "wrong_signature":
        key = "b" * 64
    elif kind == "non_numeric_subject":
        payload["sub"] = "invalid-user-id"
    else:
        assert kind == "malformed"
    token = "invalid-jwt" if kind == "malformed" else jwt.encode(payload, key, algorithm=settings.ALGORITHM)
    auth_context["response"] = auth_context["client"].get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"},
    )


@when("the account is blocked before its token is used")
def block_account_before_token_use(auth_context):
    user = auth_context["user"]
    token = create_access_token(user.id, user.role)
    user.status = "BLOQUEADO"
    auth_context["db"].commit()
    auth_context["response"] = auth_context["client"].get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"},
    )


@then(parsers.parse("the response status is {status_code:d}"))
def response_status(auth_context, status_code):
    assert auth_context["response"].status_code == status_code


@then("the response contains an active client without credentials")
def response_contains_active_client(auth_context):
    data = auth_context["response"].json()
    assert data["email"] == auth_context["payload"]["email"]
    assert data["role"] == "CLIENTE"
    assert data["status"] == "ACTIVO"
    assert "password" not in data
    assert "password_hash" not in data


@then("the stored password is hashed")
def password_is_hashed(auth_context):
    user = auth_context["db"].get(AppUserModel, auth_context["response"].json()["id"])
    assert user.password_hash != auth_context["payload"]["password"]
    assert verify_password(auth_context["payload"]["password"], user.password_hash)


@then("registration creates one audit event for the new account")
def registration_is_audited(auth_context):
    user_id = auth_context["response"].json()["id"]
    event = auth_context["db"].query(AuditModel).one()
    assert event.entity == "app_user"
    assert event.record_id == str(user_id)
    assert event.user_id == user_id
    assert event.action == AuditAction.INSERT
    assert event.endpoint == "POST /auth/register"


@then("no account or audit event is created")
def no_account_or_audit_created(auth_context):
    assert auth_context["db"].query(AppUserModel).count() == 0
    assert auth_context["db"].query(AuditModel).count() == 0


@then("the existing account is preserved without an audit event")
def existing_account_is_preserved(auth_context):
    users = auth_context["db"].query(AppUserModel).all()
    assert [user.id for user in users] == [auth_context["user"].id]
    assert auth_context["db"].query(AuditModel).count() == 0


@then("the response contains a bearer token with the configured lifetime")
def response_contains_bearer_token(auth_context):
    data = auth_context["response"].json()
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    payload = decode_access_token(data["access_token"])
    assert payload["sub"] == str(auth_context["user"].id)
    assert payload["role"] == auth_context["user"].role
    assert payload["exp"] - payload["iat"] == data["expires_in"]


@then("I can retrieve my profile using the issued token")
def profile_matches_authenticated_account(auth_context):
    token = auth_context["response"].json()["access_token"]
    response = auth_context["client"].get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["id"] == auth_context["user"].id
    assert response.json()["role"] == auth_context["user"].role
    assert "password" not in response.json()
    assert "password_hash" not in response.json()


@then("the response requests bearer authentication")
def response_requests_authentication(auth_context):
    assert auth_context["response"].headers["www-authenticate"] == "Bearer"


@then("the response does not contain a token")
def response_contains_no_token(auth_context):
    assert "access_token" not in auth_context["response"].json()
