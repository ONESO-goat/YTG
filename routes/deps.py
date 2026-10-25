"""Shared lookups that also enforce who may touch a guardian or a session."""

from sqlmodel import Session

from models.guardian_session import GuardianSession
from models.models import Guardian, GuardianConnection, GuardianType, User
from services.errors import Forbidden, NotFound
from services.guardian_services import GuardianServices

guardian_services = GuardianServices()


def guardian_for(session: Session, user: User) -> tuple[Guardian | None, GuardianConnection | None]:
    """The guardian the user owns, or else the one they are a member of (with that connection)."""
    owned = guardian_services.get_guardian_by_owner(session, user)
    if owned:
        return owned, None
    connection = guardian_services.get_connection_for(session, user)
    if connection:
        return session.get(Guardian, connection.guardian_id), connection
    return None, None


def is_member(session: Session, guardian: Guardian, user: User) -> bool:
    connection = guardian_services.get_connection_for(session, user)
    return connection is not None and connection.guardian_id == guardian.id


def owned_guardian(session: Session, guardian_id: str, user: User) -> Guardian:
    """The guardian, if the current user owns it."""
    guardian = session.get(Guardian, guardian_id)
    if not guardian:
        raise NotFound("Guardian not found")
    if guardian.owner_id != user.id:
        raise Forbidden("Only the guardian's owner can do this")
    return guardian


def accessible_guardian(session: Session, guardian_id: str, user: User) -> Guardian:
    """The guardian, if the current user owns it or is a member of it."""
    guardian = session.get(Guardian, guardian_id)
    if not guardian:
        raise NotFound("Guardian not found")
    if guardian.owner_id != user.id and not is_member(session, guardian, user):
        raise Forbidden("You don't have access to this guardian")
    return guardian


def accessible_session(session: Session, session_id: str, user: User) -> GuardianSession:
    """The monitoring session, if it belongs to the current user or to a guardian they own."""
    sess = session.get(GuardianSession, session_id)
    if not sess:
        raise NotFound("Session not found")
    if sess.user_id == user.id:
        return sess
    guardian = session.get(Guardian, sess.guardian_id)
    if guardian and guardian.owner_id == user.id:
        return sess
    raise Forbidden("You don't have access to this session")


def can_be_monitored_by(session: Session, guardian: Guardian, user: User) -> bool:
    """Members of a family guardian are monitored; the owner of a personal guardian monitors themself."""
    if is_member(session, guardian, user):
        return True
    return guardian.owner_id == user.id and guardian.guardian_type == GuardianType.PERSONAL
