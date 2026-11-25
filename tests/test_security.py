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


def test_create_and_decode_access_token():
    token = create_access_token(user_id=42, role="ADMIN")
    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert payload["role"] == "ADMIN"
    assert "iat" in payload
    assert "exp" in payload
    assert payload["exp"] > payload["iat"]


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
    token = create_access_token(user_id=1, role="CLIENTE")
    wrong_key = "a" * 32

    with pytest.raises(jwt.PyJWTError):
        jwt.decode(token, wrong_key, algorithms=[settings.ALGORITHM])
