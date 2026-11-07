"""Password hashing (bcrypt) and JWT access tokens (PyJWT)."""

import uuid
from datetime import datetime, timedelta, timezone
from functools import cache

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

DEV_SECRET = "dev-insecure-secret-change-me"


# ---- passwords ----------------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:  # malformed hash or password > 72 bytes
        return False


@cache
def _dummy_hash() -> str:
    return hash_password("dummy-password-for-timing")


def burn_password_check(password: str) -> None:
    """Run a bcrypt check even when the email doesn't exist, so response time
    doesn't reveal which emails are registered."""
    verify_password(password, _dummy_hash())


# ---- JWT ----------------------------------------------------------------------

def create_access_token(user_id: uuid.UUID, role: str) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    now = datetime.now(timezone.utc)
    expires_in = settings.access_token_expire_minutes * 60
    payload = {
        "sub": str(user_id),
        "role": role,  # informational only; authorization always re-reads the role from the DB
        "type": "access",
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm), expires_in


def decode_access_token(token: str) -> uuid.UUID:
    """Validate the token and return the user id it belongs to."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "iat"]},
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired") from None
    except jwt.InvalidTokenError:
        raise UnauthorizedError("Invalid token") from None

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")
    try:
        return uuid.UUID(payload["sub"])
    except ValueError:
        raise UnauthorizedError("Invalid token subject") from None
