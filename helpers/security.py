from datetime import datetime, timedelta, timezone
import hmac

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from fastapi_config import get_session
from helpers.config import Config
from models.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
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
        payload = jwt.decode(credentials.credentials, Config.jwt_secret, algorithms=[Config.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Session expired, please sign in again")
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid authentication token")

    user = session.get(User, payload.get("sub"))
    if not user:
        raise _unauthorized("Account no longer exists")
    return user


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    if not Config.admin_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin endpoints are disabled")
    if not x_admin_key or not hmac.compare_digest(x_admin_key, Config.admin_api_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin key")
