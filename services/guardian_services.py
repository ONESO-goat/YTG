import re

from sqlmodel import Session, delete, select

from models.guardian_session import GuardianSession
from models.models import (
    Guardian,
    GuardianConnection,
    GuardianReport,
    GuardianRestrictions,
    GuardianSettings,
    GuardianType,
    RelationshipType,
    StrictnessLevel,
    User,
    UserType,
    default_restrictions_on_creation,
)

from .errors import Conflict, NotFound, ServiceError

MAX_MEMBERS = 7
MAX_CUSTOM_RESTRICTIONS = 25
# Restrictions end up in the AI's instructions, so keep them to plain words
RESTRICTION_PATTERN = re.compile(r"^[\w][\w '&/-]{1,59}$")
MESSAGE_LENGTH = (12, 120)


class GuardianServices:
    # ------------------------------------------------------------------ lookups
    def get_guardian_by_owner(self, session: Session, user: User) -> Guardian | None:
        return session.exec(select(Guardian).where(Guardian.owner_id == user.id)).first()

    def get_connection_for(self, session: Session, user: User) -> GuardianConnection | None:
        """The connection of a family member to their guardian, if any."""
        return session.exec(select(GuardianConnection).where(GuardianConnection.user_id == user.id)).first()

    def get_connections(self, session: Session, guardian: Guardian) -> list[GuardianConnection]:
        return list(
            session.exec(select(GuardianConnection).where(GuardianConnection.guardian_id == guardian.id))
        )

    def settings(self, session: Session, guardian: Guardian) -> GuardianSettings:
        settings = session.exec(
            select(GuardianSettings).where(GuardianSettings.guardian_id == guardian.id)
        ).first()
        if settings is None:
            settings = GuardianSettings(guardian_id=guardian.id)
            session.add(settings)
            session.flush()
        return settings

    def restrictions(self, session: Session, guardian: Guardian) -> GuardianRestrictions:
        restrictions = session.exec(
            select(GuardianRestrictions).where(GuardianRestrictions.guardian_id == guardian.id)
        ).first()
        if restrictions is None:
            restrictions = GuardianRestrictions(guardian_id=guardian.id)
            session.add(restrictions)
            session.flush()
        return restrictions

    def active_restrictions(self, session: Session, guardian: Guardian) -> list[str]:
        r = self.restrictions(session, guardian)
        return [*(r.default_restrictions or default_restrictions_on_creation()), *(r.restrictions or [])]

    # ------------------------------------------------------------------ guardians
    def create_guardian(self, session: Session, user: User, name: str) -> Guardian:
        if user.user_type == UserType.DEPENDENT:
            raise ServiceError("Family member accounts can't create a guardian")
        if self.get_guardian_by_owner(session, user):
            raise Conflict("You already have a guardian")
        name = name.strip()
        if not name:
            raise ServiceError("Give your guardian a name")

        # Caregivers watch over a family; individuals watch over themselves
        guardian_type = GuardianType.FAMILY if user.user_type == UserType.CAREGIVER else GuardianType.PERSONAL
        guardian = Guardian(name=name, owner_id=user.id, guardian_type=guardian_type, on=True)
        session.add(guardian)
        session.flush()
        session.add_all(
            [GuardianSettings(guardian_id=guardian.id), GuardianRestrictions(guardian_id=guardian.id)]
        )
        self.report(
            session, guardian, f"Welcome, {user.name}! Your guardian is set up and watching out for you."
        )
        session.commit()
        session.refresh(guardian)
        return guardian

    def delete_guardian(self, session: Session, guardian: Guardian) -> None:
        for model in (
            GuardianConnection,
            GuardianSession,
            GuardianSettings,
            GuardianRestrictions,
            GuardianReport,
        ):
            session.exec(delete(model).where(model.guardian_id == guardian.id))  # type: ignore[attr-defined]
        session.delete(guardian)
        session.commit()

    def set_on(self, session: Session, guardian: Guardian, on: bool) -> Guardian:
        """Turn monitoring on or off. Turning it off stops every running session."""
        if not on:
            for running in session.exec(
                select(GuardianSession).where(GuardianSession.guardian_id == guardian.id)
            ):
                running.end()
        guardian.on = on
        session.commit()
        session.refresh(guardian)
        return guardian

    # ------------------------------------------------------------------ members
    def add_member(
        self, session: Session, guardian: Guardian, member: User | None, relationship: RelationshipType
    ) -> GuardianConnection:
        if guardian.guardian_type != GuardianType.FAMILY:
            raise ServiceError("Only family guardians can have members")
        if member is None or member.user_type != UserType.DEPENDENT:
            raise NotFound("No family member account with that ID")
        existing = self.get_connection_for(session, member)
        if existing:
            raise Conflict(
                f"{member.name} is already connected"
                if existing.guardian_id == guardian.id
                else "This account is already connected to another guardian"
            )
        if len(self.get_connections(session, guardian)) >= MAX_MEMBERS:
            raise ServiceError(f"A guardian can have at most {MAX_MEMBERS} members")

        connection = GuardianConnection(
            guardian_id=guardian.id,
            user_id=member.id,
            user_name=member.name,
            relationship_with_owner=relationship,
        )
        session.add(connection)
        self.report(session, guardian, f"{member.name} (@{member.username}) joined your family guardian.")
        session.commit()
        session.refresh(connection)
        return connection

    def remove_member(self, session: Session, guardian: Guardian, member_id: str) -> User:
        connection = session.exec(
            select(GuardianConnection).where(
                GuardianConnection.guardian_id == guardian.id, GuardianConnection.user_id == member_id
            )
        ).first()
        member = session.get(User, member_id)
        if not connection or not member:
            raise NotFound("That person isn't a member of this guardian")
        session.delete(connection)
        session.exec(
            delete(GuardianSession).where(
                GuardianSession.guardian_id == guardian.id,  # type: ignore[arg-type]
                GuardianSession.user_id == member.id,  # type: ignore[arg-type]
            )
        )
        self.report(
            session, guardian, f"{member.name} (@{member.username}) was removed from your family guardian."
        )
        session.commit()
        return member

    # ------------------------------------------------------------------ settings
    def update_settings(
        self,
        session: Session,
        guardian: Guardian,
        warning_message: str | None = None,
        applause_message: str | None = None,
        strictness: StrictnessLevel | None = None,
        reports_enabled: bool | None = None,
        points_loss_enabled: bool | None = None,
        base_points_lost: int | None = None,
    ) -> GuardianSettings:
        settings = self.settings(session, guardian)
        messages = dict(settings.custom_warning_messages or {})
        for key, value in (("warning", warning_message), ("applause", applause_message)):
            if value is None:
                continue
            value = value.strip()
            low, high = MESSAGE_LENGTH
            if not low <= len(value) <= high:
                raise ServiceError(f"The {key} message must be {low}-{high} characters long")
            messages[key] = value
        settings.custom_warning_messages = messages

        if strictness is not None:
            settings.strictness = strictness.value
        if reports_enabled is not None:
            settings.reports_enabled = reports_enabled
        if points_loss_enabled is not None:
            settings.points_loss_enabled = points_loss_enabled
        if base_points_lost is not None:
            settings.base_points_lost = base_points_lost
        session.commit()
        session.refresh(settings)
        return settings

    def add_restriction(self, session: Session, guardian: Guardian, restriction: str) -> GuardianRestrictions:
        restriction = " ".join(restriction.split()).lower()
        if not RESTRICTION_PATTERN.match(restriction):
            raise ServiceError("Use 2-60 letters, numbers and spaces for a restriction")
        r = self.restrictions(session, guardian)
        if restriction in (r.default_restrictions or []):
            raise Conflict(f"'{restriction}' is always on already")
        if restriction in (r.restrictions or []):
            raise Conflict(f"'{restriction}' is already on your list")
        if len(r.restrictions or []) >= MAX_CUSTOM_RESTRICTIONS:
            raise ServiceError(f"You can add at most {MAX_CUSTOM_RESTRICTIONS} restrictions")
        r.restrictions = [*(r.restrictions or []), restriction]
        session.commit()
        session.refresh(r)
        return r

    def remove_restriction(
        self, session: Session, guardian: Guardian, restriction: str
    ) -> GuardianRestrictions:
        r = self.restrictions(session, guardian)
        if restriction not in (r.restrictions or []):
            raise NotFound(f"'{restriction}' isn't one of your restrictions")
        r.restrictions = [x for x in r.restrictions if x != restriction]
        session.commit()
        session.refresh(r)
        return r

    # ------------------------------------------------------------------ reports
    def report(
        self, session: Session, guardian: Guardian, content: str, respect_settings: bool = False
    ) -> None:
        """Add a report for the guardian's owner. Doesn't commit."""
        if respect_settings and not self.settings(session, guardian).reports_enabled:
            return
        session.add(GuardianReport(content=content, guardian_id=guardian.id, send_to_id=guardian.owner_id))

    def list_reports(
        self, session: Session, guardian: Guardian, limit: int, offset: int
    ) -> list[GuardianReport]:
        return list(
            session.exec(
                select(GuardianReport)
                .where(GuardianReport.guardian_id == guardian.id)
                .order_by(GuardianReport.created_at.desc())  # type: ignore[union-attr]
                .offset(offset)
                .limit(limit)
            )
        )

    def delete_report(self, session: Session, guardian: Guardian, report_id: str) -> None:
        report = session.get(GuardianReport, report_id)
        if not report or report.guardian_id != guardian.id:
            raise NotFound("Report not found")
        session.delete(report)
        session.commit()
