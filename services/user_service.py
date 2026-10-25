import re

from sqlmodel import Session, delete, func, select

from helpers.security import hash_password, password_problem, verify_password
from models.guardian_session import GuardianSession
from models.models import (
    AvailableLanguages,
    GuardianConnection,
    User,
    UserSettings,
    UserType,
    UserWonReward,
)
from models.progress import DailyStats, UserAchievement, UserProgress

from .errors import ServiceError
from .guardian_services import GuardianServices

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,40}$")

guardian_services = GuardianServices()


class UserService:
    def get_by_number_id(self, session: Session, number_id: int) -> User | None:
        return session.exec(select(User).where(User.number_id == number_id)).first()

    def find_by_identifier(self, session: Session, identifier: str) -> User | None:
        """Look up a user by username or email, ignoring case."""
        identifier = identifier.strip().lower()
        column = User.email if "@" in identifier else User.username
        return session.exec(select(User).where(func.lower(column) == identifier)).first()

    def create_user(
        self,
        session: Session,
        username: str,
        email: str,
        password: str,
        user_type: UserType = UserType.INDIVIDUAL,
    ) -> User:
        username = username.strip()
        email = email.strip().lower()
        if not USERNAME_PATTERN.match(username):
            raise ServiceError(
                "Usernames are 3-40 characters: letters, numbers, dots, dashes and underscores."
            )
        if session.exec(select(User).where(func.lower(User.username) == username.lower())).first():
            raise ServiceError(f"The username '{username}' is taken")
        if session.exec(select(User).where(func.lower(User.email) == email)).first():
            raise ServiceError("An account with this email already exists")
        if problem := password_problem(password):
            raise ServiceError(problem)

        user = User(
            username=username,
            name=username,
            email=email,
            password=hash_password(password),
            user_type=user_type,
        )
        session.add_all([user, UserSettings(user=user, language=AvailableLanguages.ENGLISH.value)])
        session.commit()
        session.refresh(user)
        return user

    def authenticate(self, session: Session, identifier: str, password: str) -> User | None:
        user = self.find_by_identifier(session, identifier)
        # verify_password runs even without a user, so timing doesn't reveal which accounts exist
        if not verify_password(password, user.password if user else None):
            return None
        return user

    def change_name(self, session: Session, user: User, new_name: str) -> User:
        new_name = new_name.strip()
        if not 3 <= len(new_name) <= 120:
            raise ServiceError("Names are 3-120 characters long.")
        user.name = new_name
        # Keep the copy stored on connections in sync
        for connection in session.exec(
            select(GuardianConnection).where(GuardianConnection.user_id == user.id)
        ):
            connection.user_name = new_name
        session.commit()
        session.refresh(user)
        return user

    def change_password(self, session: Session, user: User, current_password: str, new_password: str) -> User:
        if not verify_password(current_password, user.password):
            raise ServiceError("Current password is incorrect")
        if problem := password_problem(new_password):
            raise ServiceError(problem)
        user.password = hash_password(new_password)
        user.token_version += 1  # signs out every other device
        session.commit()
        session.refresh(user)
        return user

    def delete_user(self, session: Session, user: User, password: str) -> None:
        """Delete the account and everything that belongs to it."""
        if not verify_password(password, user.password):
            raise ServiceError("Password is incorrect")

        owned = guardian_services.get_guardian_by_owner(session, user)
        if owned:
            guardian_services.delete_guardian(session, owned)
        for model in (
            GuardianConnection,
            GuardianSession,
            DailyStats,
            UserAchievement,
            UserWonReward,
            UserSettings,
        ):
            session.exec(delete(model).where(model.user_id == user.id))  # type: ignore[attr-defined]
        progress = session.get(UserProgress, user.id)
        if progress:
            session.delete(progress)
        session.delete(user)
        session.commit()
