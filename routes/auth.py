from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlmodel import Session

from fastapi_config import get_session
from services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])
user_service = UserService()


class UserSignup(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    password: str


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(user_input: UserSignup, session: Session = Depends(get_session)):
    user, msg = user_service.create_user(session=session, **user_input.model_dump())
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return user


@router.post("/login")
def login(user_input: UserLogin, session: Session = Depends(get_session)):
    user, msg = user_service.login(session=session, **user_input.model_dump())
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return user