from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session

from db import get_session
from helpers.security import get_current_user
from models.models import User, UserType
from models.schemas import AuthResponse, UserPublic, UserSummary
from routes.auth import auth_response
from services.errors import NotFound
from services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])
user_service = UserService()


class ChangeNameRequest(BaseModel):
    new_name: str = Field(..., min_length=3, max_length=120)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., max_length=200)
    new_password: str = Field(..., max_length=200)


class DeleteAccountRequest(BaseModel):
    password: str = Field(..., max_length=200)


@router.get("/me", response_model=UserPublic)
def get_me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me/name", response_model=UserPublic)
def change_name(
    payload: ChangeNameRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return user_service.change_name(session, user, payload.new_name)


@router.put("/me/password", response_model=AuthResponse)
def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Change the password. Other devices are signed out; this one gets a fresh token."""
    user = user_service.change_password(session, user, payload.current_password, payload.new_password)
    return auth_response(user)


@router.post("/me/delete")
def delete_me(
    payload: DeleteAccountRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user_service.delete_user(session, user, payload.password)
    return {"message": "Account deleted"}


@router.get("/number/{user_number_id}", response_model=UserSummary)
def get_user_by_number_id(
    user_number_id: int,
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Look up someone by the ID they shared, so a guardian owner can confirm before connecting them."""
    user = user_service.get_by_number_id(session, user_number_id)
    if not user or user.user_type != UserType.DEPENDENT:
        raise NotFound(f"No family member account with ID {user_number_id}")
    return user
