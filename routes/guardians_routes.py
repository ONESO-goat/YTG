from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from fastapi_config import get_session
from helpers.security import get_current_user
from models.guardian_session import GuardianSession
from models.models import GuardianReport, GuardianType, RelationshipType, StrictnessLevel, User, UserType
from models.schemas import (
    ConnectionPublic,
    GuardianPublic,
    MemberOverview,
    ReportPublic,
    SessionPublic,
    UserSummary,
)
from routes.deps import accessible_guardian, bad_request, not_found, owned_guardian
from services.guardian_services import GuardianServices
from services.session_services import YTGSessionService
from services.user_service import UserService

router = APIRouter(prefix="/guardians", tags=["Guardians"])
guardian_service = GuardianServices()
session_service = YTGSessionService()
user_service = UserService()


class CreateGuardianRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)


class AddMemberRequest(BaseModel):
    user_number_id: int
    relationship: RelationshipType = RelationshipType.OFFSPRING


class RestrictionRequest(BaseModel):
    restriction: str = Field(..., min_length=2, max_length=60)


class UpdateGuardianSettingsRequest(BaseModel):
    warning_message: str | None = None
    applause_message: str | None = None
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


def _settings_public(settings) -> GuardianSettingsPublic:
    messages = settings.custom_warning_messages or {}
    return GuardianSettingsPublic(
        strictness=StrictnessLevel(settings.strictness),
        warning_message=messages.get("warning", ""),
        applause_message=messages.get("applause", ""),
        reports_enabled=settings.reports_enabled,
        points_loss_enabled=settings.points_loss_enabled,
        base_points_lost=settings.base_points_lost,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=GuardianPublic)
def create_guardian(
    payload: CreateGuardianRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # Caregivers watch over a family; individuals watch over themselves
    guardian_type = GuardianType.FAMILY if user.user_type == UserType.CAREGIVER else GuardianType.PERSONAL
    guardian, msg = guardian_service.create_guardian(
        session=session, user=user, name=payload.name.strip(), guardian_type=guardian_type
    )
    if not guardian:
        raise bad_request(msg)
    return guardian


@router.get("/{guardian_id}", response_model=GuardianPublic)
def get_guardian(guardian_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return accessible_guardian(session, guardian_id, user)


@router.delete("/{guardian_id}")
def delete_guardian(guardian_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    guardian = owned_guardian(session, guardian_id, user)
    for sess in session_service.get_all_sessions_under_guardian(session, guardian):
        session.delete(sess)
    success, msg = guardian_service.delete_guardian(session=session, guardian_id=guardian.id)
    if not success:
        raise bad_request(msg)
    return {"message": "Guardian deleted"}


@router.post("/{guardian_id}/on", response_model=GuardianPublic)
def turn_guardian_on(guardian_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    guardian = owned_guardian(session, guardian_id, user)
    if not guardian.on:
        sessions, msg = session_service.turn_on_guardian(session=session, guardian_id=guardian.id)
        if sessions is None:
            raise bad_request(msg)
    session.refresh(guardian)
    return guardian


@router.post("/{guardian_id}/off", response_model=GuardianPublic)
def turn_guardian_off(guardian_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    guardian = owned_guardian(session, guardian_id, user)
    if guardian.on:
        success, msg = session_service.turn_off_guardian(session=session, guardian_id=guardian.id)
        if not success:
            raise bad_request(msg)
    session.refresh(guardian)
    return guardian


# ------------------------------------------------------------------------------
# Members (connections)
# ------------------------------------------------------------------------------
@router.get("/{guardian_id}/members", response_model=list[MemberOverview])
def list_members(guardian_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    guardian = owned_guardian(session, guardian_id, user)
    members = []
    for connection in guardian_service.get_all_connections(session, guardian=guardian):
        member = session.get(User, connection.user_id)
        if not member:
            continue
        member_session = session.exec(
            select(GuardianSession).where(
                GuardianSession.user_id == member.id, GuardianSession.guardian_id == guardian.id
            )
        ).first()
        members.append(
            MemberOverview(
                connection=ConnectionPublic.model_validate(connection),
                user=UserSummary.model_validate(member),
                session=SessionPublic.model_validate(member_session) if member_session else None,
            )
        )
    return members


@router.post("/{guardian_id}/members", status_code=status.HTTP_201_CREATED, response_model=ConnectionPublic)
def add_member(
    guardian_id: str,
    payload: AddMemberRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    guardian = owned_guardian(session, guardian_id, user)
    member = user_service.get_user_by_number_id(session=session, number_id=payload.user_number_id)
    if not member or member.user_type != UserType.DEPENDENT:
        raise not_found(f"No dependent account with ID {payload.user_number_id}")
    existing, _ = guardian_service.get_user_connection_if_any(session=session, user=member)
    if existing and existing.guardian_id != guardian.id:
        raise bad_request("This dependent is already connected to another guardian")

    connection, msg = guardian_service.add_connection(
        session=session, guardian=guardian, user=member, connection_type=payload.relationship
    )
    if not connection:
        raise bad_request(msg)
    return connection


@router.delete("/{guardian_id}/members/{user_id}")
def remove_member(
    guardian_id: str,
    user_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    guardian = owned_guardian(session, guardian_id, user)
    member = session.get(User, user_id)
    if not member:
        raise not_found(f"User '{user_id}' does not exist")
    success, msg = guardian_service.remove_connection(session=session, guardian=guardian, user=member)
    if not success:
        raise bad_request(msg)
    member_session = session.exec(
        select(GuardianSession).where(GuardianSession.user_id == member.id, GuardianSession.guardian_id == guardian.id)
    ).first()
    if member_session:
        session.delete(member_session)
        session.commit()
    return {"message": f"{member.name} was removed"}


# ------------------------------------------------------------------------------
# Settings & restrictions
# ------------------------------------------------------------------------------
@router.get("/{guardian_id}/settings", response_model=GuardianSettingsPublic)
def get_settings(guardian_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    guardian = accessible_guardian(session, guardian_id, user)
    settings, msg = guardian_service.get_or_create_guardian_settings(session=session, guardian=guardian)
    if not settings:
        raise bad_request(msg)
    return _settings_public(settings)


@router.patch("/{guardian_id}/settings", response_model=GuardianSettingsPublic)
def update_settings(
    guardian_id: str,
    payload: UpdateGuardianSettingsRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    guardian = owned_guardian(session, guardian_id, user)
    settings, msg = guardian_service.update_guardian_settings(
        session=session,
        guardian=guardian,
        warning_message=payload.warning_message,
        applause_message=payload.applause_message,
        strictness=payload.strictness.value if payload.strictness else None,
        apply_penalty=payload.points_loss_enabled,
        enable_reports=payload.reports_enabled,
        amount_of_points_to_lose=payload.base_points_lost,
    )
    if not settings:
        raise bad_request(msg)
    return _settings_public(settings)


@router.get("/{guardian_id}/restrictions", response_model=RestrictionsPublic)
def get_restrictions(guardian_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    guardian = accessible_guardian(session, guardian_id, user)
    restrictions, msg = guardian_service.get_or_create_guardian_restrictions(session=session, guardian=guardian)
    if not restrictions:
        raise bad_request(msg)
    return RestrictionsPublic(default=list(restrictions.default_restrictions), custom=list(restrictions.restrictions))


@router.post("/{guardian_id}/restrictions", response_model=RestrictionsPublic)
def add_restriction(
    guardian_id: str,
    payload: RestrictionRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    guardian = owned_guardian(session, guardian_id, user)
    custom, msg = guardian_service.add_to_guardian_restrictions(
        session=session, guardian_id=guardian.id, restriction=payload.restriction.strip().lower()
    )
    if custom is None:
        raise bad_request(msg)
    return get_restrictions(guardian_id, user, session)


@router.delete("/{guardian_id}/restrictions", response_model=RestrictionsPublic)
def remove_restriction(
    guardian_id: str,
    restriction: str = Query(..., min_length=1),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    guardian = owned_guardian(session, guardian_id, user)
    custom, msg = guardian_service.remove_from_guardian_restrictions(
        session=session, guardian_id=guardian.id, restriction=restriction
    )
    if custom is None:
        raise bad_request(msg)
    return get_restrictions(guardian_id, user, session)


# ------------------------------------------------------------------------------
# Reports
# ------------------------------------------------------------------------------
@router.get("/{guardian_id}/reports", response_model=list[ReportPublic])
def list_reports(guardian_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    guardian = owned_guardian(session, guardian_id, user)
    return session.exec(
        select(GuardianReport)
        .where(GuardianReport.guardian_id == guardian.id)
        .order_by(GuardianReport.created_at.desc(), GuardianReport.updated_at.desc())  # type: ignore[union-attr]
    ).all()


@router.delete("/{guardian_id}/reports/{report_id}")
def delete_report(
    guardian_id: str,
    report_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    guardian = owned_guardian(session, guardian_id, user)
    report = session.get(GuardianReport, report_id)
    if not report or report.guardian_id != guardian.id:
        raise not_found("Report not found")
    session.delete(report)
    session.commit()
    return {"message": "Report removed"}
