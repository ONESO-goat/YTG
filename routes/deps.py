"""Shared lookups that also enforce who may touch a guardian or a session."""
from fastapi import HTTPException, status
from sqlmodel import Session, select

from models.guardian_session import GuardianSession
from models.models import Guardian, GuardianConnection, User


def not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def forbidden(detail: str = "You don't have access to this") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def is_connected(session: Session, guardian: Guardian, user: User) -> bool:
    return (
        session.exec(
            select(GuardianConnection).where(
                GuardianConnection.guardian_id == guardian.id,
                GuardianConnection.user_id == user.id,
            )
        ).first()
        is not None
    )


def owned_guardian(session: Session, guardian_id: str, user: User) -> Guardian:
    """The guardian, if the current user owns it."""
    guardian = session.get(Guardian, guardian_id)
    if not guardian:
        raise not_found(f"Guardian '{guardian_id}' does not exist")
    if guardian.owner_id != user.id:
        raise forbidden("Only the guardian's owner can do this")
    return guardian


def accessible_guardian(session: Session, guardian_id: str, user: User) -> Guardian:
    """The guardian, if the current user owns it or is connected to it."""
    guardian = session.get(Guardian, guardian_id)
    if not guardian:
        raise not_found(f"Guardian '{guardian_id}' does not exist")
    if guardian.owner_id != user.id and not is_connected(session, guardian, user):
        raise forbidden()
    return guardian


def accessible_session(session: Session, session_id: str, user: User) -> GuardianSession:
    """The monitoring session, if it belongs to the current user or to a guardian they own."""
    sess = session.get(GuardianSession, session_id)
    if not sess:
        raise not_found(f"Session '{session_id}' does not exist")
    if sess.user_id == user.id:
        return sess
    guardian = session.get(Guardian, sess.guardian_id)
    if guardian and guardian.owner_id == user.id:
        return sess
    raise forbidden()


def can_be_monitored_by(session: Session, guardian: Guardian, user: User) -> bool:
    """Whether the user may run a monitoring session under this guardian.

    Members of a family guardian are monitored; the owner of a personal guardian monitors themself.
    """
    if is_connected(session, guardian, user):
        return True
    return guardian.owner_id == user.id and guardian.guardian_type.value == "personal"
