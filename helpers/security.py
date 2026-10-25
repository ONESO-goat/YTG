import hmac
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from db import get_session
from helpers.config import Config
from models.models import User

bearer_scheme = HTTPBearer(auto_error=False)

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_BYTES = 72  # bcrypt ignores anything past 72 bytes


# ------------------------------------------------------------------------------
# Passwords
# ------------------------------------------------------------------------------
def password_problem(password: str) -> str | None:
    """Why a password is too weak, or None if it is acceptable."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
    if len(password.encode()) > MAX_PASSWORD_BYTES:
        return f"Password must be at most {MAX_PASSWORD_BYTES} bytes long."
    if not any(c.isupper() for c in password) or not any(c.isdigit() for c in password):
        return "Password must contain at least one uppercase letter and one number."
    return None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


# A real hash to compare against when the account doesn't exist, so a failed login takes the
# same time either way and response timing doesn't reveal which usernames exist
_DUMMY_HASH = hash_password("timing-equalizer-0A")


def verify_password(password: str, hashed: str | None) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), (hashed or _DUMMY_HASH).encode()) and hashed is not None
    except ValueError:
        return False


# ------------------------------------------------------------------------------
# Tokens
# ------------------------------------------------------------------------------
def create_access_token(user: User) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user.id,
        # Tokens from before the last password change stop working
        "ver": user.token_version,
        "iat": now,
        "exp": now + timedelta(minutes=Config.jwt_expire_minutes),
    }
    return jwt.encode(payload, Config.jwt_secret, algorithm=Config.jwt_algorithm)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None:
        raise _unauthorized("Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials,
            Config.jwt_secret,
            algorithms=[Config.jwt_algorithm],
            options={"require": ["sub", "exp"]},
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Session expired, please sign in again") from None
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid authentication token") from None

    user = session.get(User, payload["sub"])
    if not user:
        raise _unauthorized("Account no longer exists")
    if payload.get("ver", 0) != user.token_version:
        raise _unauthorized("Your password was changed, please sign in again")
    return user


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    if not Config.admin_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin endpoints are disabled")
    if not x_admin_key or not hmac.compare_digest(x_admin_key, Config.admin_api_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin key")
