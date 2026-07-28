from models.models import AvailableLanguages, User, Guardian, UserType, UserSettings, GuardianConnection
from sqlmodel import Session, select, func
from .helpers import validate_password, hash_password, verify_password
from datetime import datetime
from pydantic import ValidationError

class UserService:
    def __init__(self)->None:
        pass
    
    def get_all_users(self, session:Session):
        statement = select(User)
        return session.exec(statement).all()
    
    def get_user_by_email(self, session:Session, email:str)->User|None:
        if not email:
            raise ValueError("Email is required")
        return session.exec(
            select(User).where(User.email == email)
        ).first()
    
    def get_user_by_number_id(self, session:Session, number_id:int)->User|None:
            if not number_id:
                raise ValueError("Number id is required")
            return session.exec(
                select(User).where(User.number_id == number_id)
            ).first()
            
    def get_user_by_username(self, session: Session, username:str)->User|None:
        if not username:
            raise ValueError("Username is required")
        return session.exec(
            select(User).where(User.username == username)
        ).first()
        
    def get_user_by_id(self, session:Session, user_id:str)->User|None:
        if not user_id:
            raise ValueError("User ID is required")
        return session.get(User, user_id)
    
    def get_users_with_guardian_connection(self, session: Session, guardian_id:str):
        if not guardian_id:
            return None, "Guardian id is required"
        
        guardian = session.get(Guardian, guardian_id)
        if not guardian:
            return None, f"Guardian of id '{guardian_id}' does not exist"
        result = []
        users = session.exec(
            select(GuardianConnection)
            .where(GuardianConnection.guardian_id==guardian.id)).all()
        
        for connection in users:
            user = self.get_user_by_id(session,user_id=connection.user_id)
            if not user:
                continue
            result.append(user.model_dump())
        return result, "success"
        
    
    def create_user(self, session, username:str, email:str, password:str, user_type:UserType=UserType.INDIVIDUAL)->tuple[User|None, str]:
        if not username or not email or not password:
            return None, "Username, email, and password are required"
        
        if session.exec(
            select(User).where(func.lower(User.username) == username.lower())
        ).first():
            return None, f"User with username '{username}' already exists"
        
        if session.exec(
            select(User).where(func.lower(User.email) == email.lower())
        ).first():
            return None, f"User with email '{email}' already exists"
        
        valid, mes = validate_password(password)
        if not valid:
            return None, mes
        
        hashed_password = hash_password(password)
        user = User(
            username=username,
            name=username,
            email=email,
            password=hashed_password,  
            user_type=user_type,
            device_ip=None
        )
        settings = UserSettings(
            user=user,
            language=AvailableLanguages.ENGLISH.value
        )
        session.add_all([user, settings])
        session.commit()
        session.refresh(user)
        return user, "success"
    
    def delete_user(self, session, user:User):
        if not user:
            return False, "User is required"
        guardian = session.exec(
            select(Guardian).where(Guardian.owner_id == user.id)
        ).first()

        if guardian:
            session.delete(guardian)
            
        session.delete(user)
        session.commit()
        return True, "success"
    
    def login(self, session:Session, password:str, username:str='', email:str='')->tuple[User|None, str]:
        if not email and not username:
            return None, "Username or email are required"
        
        if not password:
            return None, "Password is required"
        
        if username:
            user = session.exec(
                select(User).where(User.username == username)
            ).first()
        else:
            
            user = session.exec(
                select(User).where(User.email == email)
            ).first()
            if not user:
                return None, "No user under this email"

        if not user or not verify_password(password, user.password):
            return None, "Username or password are incorrect"
        
        return user, "success"
    
    def change_name(self, session:Session, user:User, new_name:str)->tuple[None|User, str]:
        if not user:
            return None, "User is required"
        
        if not new_name:
            return None, "New name is required"
        
        if not 3 <= len(new_name) <= 120:
            return None, "Name is falls outside the valid range of 3-120 characters."
                    
        
        user.name = new_name
        session.add(user)
        session.commit()
        session.refresh(user)
        return user, "success"
    
    def change_password(self, session:Session, user:User, new_password:str)->tuple[None|User, str]:
        if not user:
            return None, "User is required"
        
        valid, mes = validate_password(new_password)
        if not new_password or not valid:
            return None, mes or "password required"
        
        hashed_password = hash_password(new_password)
        user.password = hashed_password
        session.add(user)
        session.commit()
        session.refresh(user)
        return user, "success"