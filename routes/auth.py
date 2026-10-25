from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import Session

from fastapi_config import get_session
from helpers.security import create_access_token, get_current_user
from models.models import Guardian, User, UserType
from models.schemas import AuthResponse, ConnectionPublic, GuardianPublic, MeResponse, UserPublic
from services.guardian_services import GuardianServices
from services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])
user_service = UserService()
guardian_service = GuardianServices()


class UserSignup(BaseModel):
    username: str = Field(..., min_length=3, max_length=40)
    email: EmailStr
    password: str
    user_type: UserType = UserType.INDIVIDUAL


class UserLogin(BaseModel):
    # Username or email
    identifier: str = Field(..., min_length=1)
    password: str


def build_me(session: Session, user: User) -> MeResponse:
    guardian = guardian_service.get_guardian_by_owner(session, user=user)
    connection = None
    if not guardian:
        connection, _ = guardian_service.get_user_connection_if_any(session=session, user=user)
        if connection:
            guardian = session.get(Guardian, connection.guardian_id)
    return MeResponse(
        user=UserPublic.model_validate(user),
        guardian=GuardianPublic.model_validate(guardian) if guardian else None,
        is_guardian_owner=bool(guardian and guardian.owner_id == user.id),
        connection=ConnectionPublic.model_validate(connection) if connection else None,
    )


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=AuthResponse)
def signup(user_input: UserSignup, session: Session = Depends(get_session)):
    user, msg = user_service.create_user(
        session=session,
        username=user_input.username.strip(),
        email=user_input.email,
        password=user_input.password,
        user_type=user_input.user_type,
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return AuthResponse(access_token=create_access_token(user.id), user=UserPublic.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(user_input: UserLogin, session: Session = Depends(get_session)):
    identifier = user_input.identifier.strip()
    if "@" in identifier:
        user, msg = user_service.login(session=session, email=identifier, password=user_input.password)
    else:
        user, msg = user_service.login(session=session, username=identifier, password=user_input.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)
    return AuthResponse(access_token=create_access_token(user.id), user=UserPublic.model_validate(user))


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return build_me(session, user)
