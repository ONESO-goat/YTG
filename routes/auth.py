from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import Session

from db import get_session
from helpers.rate_limit import client_ip, login_by_account, login_by_ip, signup_by_ip
from helpers.security import create_access_token, get_current_user
from models.models import User, UserType
from models.schemas import AuthResponse, ConnectionPublic, GuardianPublic, MeResponse, UserPublic
from routes.deps import guardian_for
from services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])
user_service = UserService()


class UserSignup(BaseModel):
    username: str = Field(..., min_length=3, max_length=40)
    email: EmailStr
    password: str = Field(..., max_length=200)
    user_type: UserType = UserType.INDIVIDUAL


class UserLogin(BaseModel):
    # Username or email
    identifier: str = Field(..., min_length=1, max_length=254)
    password: str = Field(..., max_length=200)


def build_me(session: Session, user: User) -> MeResponse:
    guardian, connection = guardian_for(session, user)
    return MeResponse(
        user=UserPublic.model_validate(user),
        guardian=GuardianPublic.model_validate(guardian) if guardian else None,
        is_guardian_owner=bool(guardian and guardian.owner_id == user.id),
        connection=ConnectionPublic.model_validate(connection) if connection else None,
    )


def auth_response(user: User) -> AuthResponse:
    return AuthResponse(access_token=create_access_token(user), user=UserPublic.model_validate(user))


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=AuthResponse)
def signup(payload: UserSignup, request: Request, session: Session = Depends(get_session)):
    signup_by_ip.hit(client_ip(request))
    user = user_service.create_user(
        session,
        username=payload.username,
        email=payload.email,
        password=payload.password,
        user_type=payload.user_type,
    )
    return auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(payload: UserLogin, request: Request, session: Session = Depends(get_session)):
    account_key = payload.identifier.strip().lower()
    login_by_ip.hit(client_ip(request))
    login_by_account.hit(account_key)
    user = user_service.authenticate(session, payload.identifier, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Username/email or password is incorrect"
        )
    login_by_account.reset(account_key)
    return auth_response(user)


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return build_me(session, user)
