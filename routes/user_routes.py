# routes/user_routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from fastapi_config import get_session
from services.user_service import UserService
from services.guardian_services import GuardianServices

router = APIRouter(prefix="/users", tags=["Users"])
user_service = UserService()
guardian_service = GuardianServices()


class ChangeNameRequest(BaseModel):
    new_name: str = Field(..., min_length=3, max_length=120)


class ChangePasswordRequest(BaseModel):
    new_password: str


@router.get("/")
def get_all_users(session: Session = Depends(get_session)):
    return user_service.get_all_users(session)


@router.get("/{user_id}")
def get_user_by_id(user_id: str, session: Session = Depends(get_session)):
    user = user_service.get_user_by_id(session, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User with ID '{user_id}' does not exist"
        )
    return user

@router.get("/number/{user_number_id}")
def get_user_by_number_id(user_number_id: int, session: Session = Depends(get_session)):
    user = user_service.get_user_by_number_id(session, number_id=user_number_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User with number ID '{user_number_id}' does not exist"
        )
    return user

@router.patch("/{user_id}/name")
def change_name(
    user_id: str, 
    payload: ChangeNameRequest, 
    session: Session = Depends(get_session)
):
    user = user_service.get_user_by_id(session, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User with ID '{user_id}' does not exist"
        )

    updated_user, msg = user_service.change_name(
        session=session, user=user, new_name=payload.new_name
    )
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return updated_user


@router.put("/{user_id}/password")
def change_password(
    user_id: str, 
    payload: ChangePasswordRequest, 
    session: Session = Depends(get_session)
):
    user = user_service.get_user_by_id(session, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User with ID '{user_id}' does not exist"
        )

    updated_user, msg = user_service.change_password(
        session=session, user=user, new_password=payload.new_password
    )
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return updated_user


@router.delete("/{user_id}")
def delete_user(user_id: str, session: Session = Depends(get_session)):
    user = user_service.get_user_by_id(session, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User with ID '{user_id}' does not exist"
        )

    success, msg = user_service.delete_user(session=session, user=user)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return {"message": f"User '{user_id}' successfully deleted"}


@router.get("/guardian/{guardian_id}")
def get_users_by_guardian(guardian_id: str, session: Session = Depends(get_session)):
    users, msg = user_service.get_users_with_guardian_connection(
        session=session, guardian_id=guardian_id
    )
    if users is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    return users


@router.get("/get/user/connection/{user_id}")
def fetch_user_connection(
    user_id:str,
    session:Session=Depends(get_session)
):
    user = user_service.get_user_by_id(session=session, user_id=user_id)
    if not user:
        raise HTTPException(status_code=400, detail=f"User of id '{user_id}' does not exist.")
    connection, msg = guardian_service.get_user_connection_if_any(session=session, user=user)
    return connection

