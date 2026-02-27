from datetime import datetime, timedelta

import jwt

from app.schemas.login import JWTPayload
from app.settings.config import settings
from app.utils.jwt_utils import create_access_token


def test_create_access_token_returns_string():
    expire = datetime.utcnow() + timedelta(minutes=30)
    payload = JWTPayload(user_id=1, username="admin", is_superuser=True, exp=expire)
    token = create_access_token(data=payload)
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_access_token_decodable():
    expire = datetime.utcnow() + timedelta(minutes=30)
    payload = JWTPayload(user_id=42, username="testuser", is_superuser=False, exp=expire)
    token = create_access_token(data=payload)

    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert decoded["user_id"] == 42
    assert decoded["username"] == "testuser"
    assert decoded["is_superuser"] is False
