from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from db import get_session
from helpers import clock
from helpers.security import get_current_user
from models.guardian_session import GuardianSession
from models.models import GuardianRestrictions, GuardianSettings, RelationshipType, StrictnessLevel, User
from models.schemas import (
    ConnectionPublic,
    GuardianPublic,
    MemberOverview,
    ReportPublic,
    SessionPublic,
    UserSummary,
)
from routes.deps import accessible_guardian, owned_guardian
from services.guardian_services import GuardianServices
from services.progress_service import ProgressService
from services.user_service import UserService

router = APIRouter(prefix="/guardians", tags=["Guardians"])
guardian_service = GuardianServices()
progress_service = ProgressService()
user_service = UserService()


class CreateGuardianRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)


class AddMemberRequest(BaseModel):
    user_number_id: int
    relationship: RelationshipType = RelationshipType.OFFSPRING


class RestrictionRequest(BaseModel):
    restriction: str = Field(..., min_length=2, max_length=60)


class UpdateGuardianSettingsRequest(BaseModel):
    warning_message: str | None = Field(default=None, max_length=200)
    applause_message: str | None = Field(default=None, max_length=200)
    strictness: StrictnessLevel | None = None
    reports_enabled: bool | None = None
    points_loss_enabled: bool | None = None
    base_points_lost: int | None = Field(default=None, ge=0, le=1000)


class GuardianSettingsPublic(BaseModel):
    strictness: StrictnessLevel
    warning_message: str
    applause_message: str
    reports_enabled: bool
    points_loss_enabled: bool
    base_points_lost: int


class RestrictionsPublic(BaseModel):
    default: list[str]
    custom: list[str]


def _settings_public(settings: GuardianSettings) -> GuardianSettingsPublic:
    messages = settings.custom_warning_messages or {}
    return GuardianSettingsPublic(
        strictness=StrictnessLevel(settings.strictness),
        warning_message=messages.get("warning", ""),
        applause_message=messages.get("applause", ""),
        reports_enabled=settings.reports_enabled,
        points_loss_enabled=settings.points_loss_enabled,
        base_points_lost=settings.base_points_lost,
    )


def _restrictions_public(r: GuardianRestrictions) -> RestrictionsPublic:
    return RestrictionsPublic(default=list(r.default_restrictions or []), custom=list(r.restrictions or []))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=GuardianPublic)
def create_guardian(
    payload: CreateGuardianRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return guardian_service.create_guardian(session, user, payload.name)


@router.get("/{guardian_id}", response_model=GuardianPublic)
def get_guardian(
    guardian_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    return accessible_guardian(session, guardian_id, user)


@router.delete("/{guardian_id}")
def delete_guardian(
    guardian_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    guardian_service.delete_guardian(session, owned_guardian(session, guardian_id, user))
    return {"message": "Guardian deleted"}


@router.post("/{guardian_id}/on", response_model=GuardianPublic)
def turn_guardian_on(
    guardian_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    return guardian_service.set_on(session, owned_guardian(session, guardian_id, user), True)


@router.post("/{guardian_id}/off", response_model=GuardianPublic)
def turn_guardian_off(
    guardian_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    return guardian_service.set_on(session, owned_guardian(session, guardian_id, user), False)


# ------------------------------------------------------------------------------
# Members
# ------------------------------------------------------------------------------
@router.get("/{guardian_id}/members", response_model=list[MemberOverview])
def list_members(
    guardian_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    guardian = owned_guardian(session, guardian_id, user)
    connections = guardian_service.get_connections(session, guardian)
    member_ids = [c.user_id for c in connections]
    users = {u.id: u for u in session.exec(select(User).where(User.id.in_(member_ids)))}  # type: ignore[attr-defined]
    sessions = {
        s.user_id: s
        for s in session.exec(
            select(GuardianSession).where(
                GuardianSession.guardian_id == guardian.id,
                GuardianSession.user_id.in_(member_ids),  # type: ignore[attr-defined]
            )
        )
    }
    now = clock.now()
    members = [
        MemberOverview(
            connection=ConnectionPublic.model_validate(c),
            user=UserSummary.model_validate(users[c.user_id]),
            session=SessionPublic.model_validate(sessions[c.user_id]) if c.user_id in sessions else None,
            progress=progress_service.summary(session, users[c.user_id], now),
        )
        for c in connections
        if c.user_id in users
    ]
    session.commit()  # summaries may create today's stats rows
    return members


@router.post("/{guardian_id}/members", status_code=status.HTTP_201_CREATED, response_model=ConnectionPublic)
def add_member(
    guardian_id: str,
    payload: AddMemberRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    guardian = owned_guardian(session, guardian_id, user)
    member = user_service.get_by_number_id(session, payload.user_number_id)
    return guardian_service.add_member(session, guardian, member, payload.relationship)


@router.delete("/{guardian_id}/members/{user_id}")
def remove_member(
    guardian_id: str,
    user_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    member = guardian_service.remove_member(session, owned_guardian(session, guardian_id, user), user_id)
    return {"message": f"{member.name} was removed"}


# ------------------------------------------------------------------------------
# Settings & restrictions
# ------------------------------------------------------------------------------
@router.get("/{guardian_id}/settings", response_model=GuardianSettingsPublic)
def get_settings(
    guardian_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    settings = guardian_service.settings(session, accessible_guardian(session, guardian_id, user))
    session.commit()
    return _settings_public(settings)


@router.patch("/{guardian_id}/settings", response_model=GuardianSettingsPublic)
def update_settings(
    guardian_id: str,
    payload: UpdateGuardianSettingsRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    guardian = owned_guardian(session, guardian_id, user)
    settings = guardian_service.update_settings(session, guardian, **payload.model_dump())
    return _settings_public(settings)


@router.get("/{guardian_id}/restrictions", response_model=RestrictionsPublic)
def get_restrictions(
    guardian_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    restrictions = guardian_service.restrictions(session, accessible_guardian(session, guardian_id, user))
    session.commit()
    return _restrictions_public(restrictions)


@router.post("/{guardian_id}/restrictions", response_model=RestrictionsPublic)
def add_restriction(
    guardian_id: str,
    payload: RestrictionRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    guardian = owned_guardian(session, guardian_id, user)
    return _restrictions_public(guardian_service.add_restriction(session, guardian, payload.restriction))


@router.delete("/{guardian_id}/restrictions", response_model=RestrictionsPublic)
def remove_restriction(
    guardian_id: str,
    restriction: str = Query(..., min_length=1, max_length=60),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    guardian = owned_guardian(session, guardian_id, user)
    return _restrictions_public(guardian_service.remove_restriction(session, guardian, restriction))


# ------------------------------------------------------------------------------
# Reports
# ------------------------------------------------------------------------------
@router.get("/{guardian_id}/reports", response_model=list[ReportPublic])
def list_reports(
    guardian_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return guardian_service.list_reports(session, owned_guardian(session, guardian_id, user), limit, offset)


@router.delete("/{guardian_id}/reports/{report_id}")
def delete_report(
    guardian_id: str,
    report_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    guardian_service.delete_report(session, owned_guardian(session, guardian_id, user), report_id)
    return {"message": "Report removed"}
