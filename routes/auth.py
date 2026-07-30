from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, ValidationError
from sqlmodel import Session
from models.models import UserType
from fastapi_config import get_session
from services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])
user_service = UserService()


class UserSignup(BaseModel):
    username: str
    email: EmailStr
    password: str
    user_type: str


class UserLogin(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    password: str


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(user_input: UserSignup, session: Session = Depends(get_session)):
    try:
        user_type = UserType(user_input.user_type)
    except ValidationError:
        raise HTTPException(status_code=400, detail=f"The user type '{user_input.user_type}' is not known")
    user, msg = user_service.create_user(session=session, 
                                         username=user_input.username,
                                         email=user_input.email,
                                         password=user_input.password,
                                         user_type=user_type)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return user


@router.post("/login")
def login(user_input: UserLogin, session: Session = Depends(get_session)):
    user, msg = user_service.login(session=session, **user_input.model_dump())
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return user