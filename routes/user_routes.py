from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session

from fastapi_config import get_session
from helpers.security import get_current_user
from models.models import User, UserType
from models.schemas import UserPublic, UserSummary
from routes.deps import bad_request, not_found
from services.helpers import verify_password
from services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])
user_service = UserService()


class ChangeNameRequest(BaseModel):
    new_name: str = Field(..., min_length=3, max_length=120)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.get("/me", response_model=UserPublic)
def get_me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me/name", response_model=UserPublic)
def change_name(
    payload: ChangeNameRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    updated_user, msg = user_service.change_name(session=session, user=user, new_name=payload.new_name)
    if not updated_user:
        raise bad_request(msg)
    return updated_user


@router.put("/me/password", response_model=UserPublic)
def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if not verify_password(payload.current_password, user.password):
        raise bad_request("Current password is incorrect")
    updated_user, msg = user_service.change_password(session=session, user=user, new_password=payload.new_password)
    if not updated_user:
        raise bad_request(msg)
    return updated_user


@router.delete("/me")
def delete_me(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    success, msg = user_service.delete_user(session=session, user=user)
    if not success:
        raise bad_request(msg)
    return {"message": "Account deleted"}


@router.get("/number/{user_number_id}", response_model=UserSummary)
def get_user_by_number_id(
    user_number_id: int,
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Look up someone by the ID they shared, so a guardian owner can confirm before connecting them."""
    user = user_service.get_user_by_number_id(session, number_id=user_number_id)
    if not user or user.user_type != UserType.DEPENDENT:
        raise not_found(f"No dependent account with ID {user_number_id}")
    return user
