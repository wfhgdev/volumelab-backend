from datetime import datetime, timedelta, timezone
import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.app_user_model import RoleUser


def test_password_hash_differs_from_plaintext():
    plain = "SuperSecret123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert hashed.startswith("$argon2")


def test_verify_password_correct_and_incorrect():
    plain = "SuperSecret123!"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False


@pytest.mark.parametrize("user_id", [42, "42"])
@pytest.mark.parametrize("role", ["ADMIN", "CLIENTE", RoleUser.ADMIN, RoleUser.CLIENTE])
def test_create_and_decode_access_token(user_id, role):
    token = create_access_token(user_id=user_id, role=role)
    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert payload["role"] == getattr(role, "value", role)
    assert "iat" in payload
    assert "exp" in payload
    assert payload["exp"] - payload["iat"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_decode_expired_token_raises_error():
    past = datetime.now(timezone.utc) - timedelta(minutes=10)
    payload = {
        "sub": "1",
        "role": "CLIENTE",
        "iat": int((past - timedelta(minutes=5)).timestamp()),
        "exp": int(past.timestamp()),
    }
    expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token)


def test_decode_token_with_wrong_key_raises_error():
    payload = decode_access_token(create_access_token(user_id=1, role="CLIENTE"))
    token = jwt.encode(payload, "a" * 64, algorithm=settings.ALGORITHM)

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token)


def test_password_hashes_use_independent_salts():
    password = "SamePassword123!"
    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash
    assert verify_password(password, first_hash)
    assert verify_password(password, second_hash)


@pytest.mark.parametrize("claim", ["sub", "iat", "exp"])
def test_decode_requires_mandatory_claims(claim):
    payload = decode_access_token(create_access_token(user_id=1, role="CLIENTE"))
    del payload[claim]
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(token)


@pytest.mark.parametrize("token", ["", "not-a-token", "invalid.jwt.signature"])
def test_decode_rejects_malformed_tokens(token):
    with pytest.raises(jwt.DecodeError):
        decode_access_token(token)


@pytest.mark.parametrize("algorithm", ["HS384", "none"])
def test_decode_rejects_unapproved_algorithms(algorithm):
    payload = decode_access_token(create_access_token(user_id=1, role="CLIENTE"))
    key = "a" * 64 if algorithm != "none" else None
    token = jwt.encode(payload, key, algorithm=algorithm)

    with pytest.raises(jwt.InvalidAlgorithmError):
        decode_access_token(token)


def test_decode_rejects_tokens_issued_in_the_future():
    future = datetime.now(timezone.utc) + timedelta(minutes=10)
    token = jwt.encode(
        {"sub": "1", "iat": int(future.timestamp()), "exp": int((future + timedelta(minutes=10)).timestamp())},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    with pytest.raises(jwt.ImmatureSignatureError):
        decode_access_token(token)


def test_access_token_uses_configured_lifetime(monkeypatch):
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 15)
    payload = decode_access_token(create_access_token(user_id=1, role="CLIENTE"))

    assert payload["exp"] - payload["iat"] == 900
