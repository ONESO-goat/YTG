from datetime import datetime, timezone
import random

from sqlmodel import Session, select

from agent.bot import Analysis, ScreenClassifier
from agent.frames import frame_fingerprint, is_same_frame
from models.guardian_session import GuardianSession
from models.models import (
    STRICTNESS_MULTIPLIERS,
    Guardian,
    GuardianReport,
    GuardianSettings,
    GuardianType,
    User,
    default_restrictions_on_creation,
)
from .guardian_services import GuardianServices
from .progress_service import Outcome, ProgressService
from .reports_service import create_report

guardian_services = GuardianServices()
progress_service = ProgressService()

# Scans arrive every ~5 seconds. An unchanged screen earns nothing, and after ~5 minutes the session stops.
IDLE_SHUTDOWN_FRAMES = 60
# Staying on flagged content this long after the warning counts as ignoring it
IGNORE_THRESHOLD_SECONDS = 30
# While the user keeps ignoring a warning, the penalty repeats this often, up to MAX_PENALTIES_PER_WARNING
REPEAT_PENALTY_SECONDS = 60
MAX_PENALTIES_PER_WARNING = 3
# How long the user must stay away from flagged content for the warning to count as heeded
AVOIDANCE_SECONDS = 15
# From this many warnings in a day, penalties double
REPEAT_OFFENDER_WARNINGS = 5


class SessionInactiveError(Exception):
    pass


def utcnow() -> datetime:
    """Naive UTC, matching how timestamps are stored in SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class YTGSessionService:

    def turn_off_guardian(self, session: Session, guardian_id: str) -> tuple[bool, str]:
        """Turn off the guardian and pause every session under it."""
        guardian_data, mes = guardian_services.get_guardian_data(session, guardian_id=guardian_id)
        guardian = guardian_data.get("guardian")
        if not guardian:
            return False, mes
        if not guardian.on:
            return False, "Guardian is already off"

        sessions = self.get_all_sessions_under_guardian(session=session, guardian=guardian)
        for running_session in sessions:
            running_session.end()
        guardian.on = False
        session.commit()
        session.refresh(guardian)
        return True, f"Guardian is now off, paused {len(sessions)} sessions"

    def turn_on_guardian(self, session: Session, guardian_id: str) -> tuple[list[GuardianSession] | None, str]:
        """Turn on the guardian so its members can start monitoring sessions."""
        guardian_data, mes = guardian_services.get_guardian_data(session, guardian_id=guardian_id)
        guardian = guardian_data.get("guardian")
        if not guardian:
            return None, mes
        if guardian.on:
            return None, "Guardian is already on"

        new_sessions = []
        for connection in guardian_services.get_all_connections(session=session, guardian=guardian):
            user = session.get(User, connection.user_id)
            if not user:
                continue
            s, _ = self.get_or_create(session=session, user=user, guardian=guardian)
            new_sessions.append(s)
        guardian.on = True
        session.commit()
        session.refresh(guardian)
        return new_sessions, f"Guardian is on, {len(new_sessions)} member sessions ready"

    def get_all_sessions_under_guardian(self, session: Session, guardian: Guardian):
        return session.exec(select(GuardianSession).where(GuardianSession.guardian_id == guardian.id)).all()

    def get_YTGSession(self, session: Session, session_id: str) -> tuple[GuardianSession | None, str]:
        if not session or not session_id:
            return None, "Session and ID are required"
        sess = session.get(GuardianSession, session_id)
        if not sess:
            return None, f"No session under the id '{session_id}'"
        return sess, "success"

    def get_or_create(self, session: Session, user: User, guardian: Guardian) -> tuple[GuardianSession, bool]:
        existing = session.exec(
            select(GuardianSession).where(
                GuardianSession.user_id == user.id,
                GuardianSession.guardian_id == guardian.id,
            )
        ).first()
        if existing:
            return existing, False

        row = GuardianSession(user_id=user.id, guardian_id=guardian.id)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row, True

    def get_users_session(self, session: Session, user: User) -> GuardianSession | None:
        return session.exec(select(GuardianSession).where(GuardianSession.user_id == user.id)).first()

    def start_session(self, session: Session, sm_row: GuardianSession, user: User) -> Outcome:
        outcome = Outcome()
        if not sm_row.active:
            sm_row.start()
            sm_row.last_frame_hash = None
            sm_row.same_image_counter = 0
            sm_row.minute_timer = None
            outcome = progress_service.record_session_start(session, user, utcnow())
        session.commit()
        return outcome

    def _result(
        self,
        sm_row: GuardianSession,
        user: User,
        outcome: Outcome | None = None,
        flagged: bool = False,
        description: str = "",
        category: str | None = None,
        shutdown: bool = False,
        idle: bool = False,
        analysis_failed: bool = False,
    ) -> dict:
        outcome = outcome or Outcome()
        return {
            "flagged": flagged,
            "description": description,
            "category": category,
            "warning_active": sm_row.warning_active,
            "points_awarded": outcome.points,
            "points_lost": outcome.lost,
            "xp_awarded": outcome.xp,
            "currency": user.currency,
            "events": outcome.events,
            "shutdown": shutdown,
            "idle": idle,
            "analysis_failed": analysis_failed,
        }

    def process_scan(
        self,
        session: Session,
        classifier: ScreenClassifier,
        session_row: GuardianSession,
        image_bytes: bytes,
    ) -> dict:
        if not session_row.active:
            raise SessionInactiveError("This session is not running. Start it before sending scans.")

        stuff, mes = guardian_services.get_guardian_data(session=session, guardian_id=session_row.guardian_id)
        guardian: Guardian | None = stuff.get("guardian")
        settings: GuardianSettings | None = stuff.get("settings")
        restrictions = stuff.get("restrictions")
        if not guardian or not settings:
            raise ValueError(f"Guardian data missing during scan: {mes}")
        if not guardian.on:
            session_row.end()
            session.commit()
            raise SessionInactiveError("Monitoring is turned off for this guardian.")

        user = session.get(User, session_row.user_id)
        if not user:
            raise ValueError("User is missing during scan")

        fingerprint = frame_fingerprint(image_bytes)
        if fingerprint is None:
            raise ValueError("Uploaded file is not a readable image")

        now = utcnow()
        previous_scan_at = session_row.last_scan_at
        session_row.last_scan_at = now

        # An unchanged screen needs no new AI verdict and earns nothing: the clean-minute timer is
        # paused for the idle time, so leaving a page open can't be used to farm points.
        if is_same_frame(fingerprint, session_row.last_frame_hash):
            session_row.same_image_counter += 1
            session_row.total_same_image_counter_for_whole_session += 1
            if session_row.minute_timer and previous_scan_at:
                session_row.minute_timer += now - previous_scan_at
            if session_row.same_image_counter >= IDLE_SHUTDOWN_FRAMES:
                session_row.shutdown_counter += 1
                session_row.same_image_counter = 0
                session_row.minute_timer = None
                session_row.last_frame_hash = None
                session_row.end()
                session.commit()
                return self._result(session_row, user, shutdown=True, idle=True)
            # Still on flagged content counts as ignoring the warning, even when the screen isn't changing
            outcome = Outcome()
            if session_row.warning_active and session_row.tracking_start_at is None:
                outcome = self._maybe_penalize(session, session_row, guardian, settings, user, None, now)
            session.commit()
            return self._result(session_row, user, outcome, flagged=session_row.warning_active, idle=True)

        session_row.same_image_counter = 0
        session_row.last_frame_hash = fingerprint

        active_restrictions = (
            [*restrictions.default_restrictions, *restrictions.restrictions]
            if restrictions
            else default_restrictions_on_creation()
        )
        analysis = classifier.analyze(
            image_bytes=image_bytes,
            user_id=user.id,
            guardian_settings=settings,
            restrictions=active_restrictions,
        )
        if analysis.failed:
            # Neither reward nor punish when the AI couldn't decide; the next scan will retry
            session.commit()
            return self._result(session_row, user, description=analysis.description, analysis_failed=True)

        if analysis.flagged:
            outcome = self._handle_flagged(session, session_row, guardian, settings, user, analysis, now)
            session.commit()
            return self._result(
                session_row,
                user,
                outcome,
                flagged=True,
                description=analysis.description,
                category=analysis.category,
            )

        outcome = self._handle_clean(session, session_row, user, now)
        session.commit()
        return self._result(session_row, user, outcome, description=analysis.description)

    def _handle_flagged(
        self,
        session: Session,
        sm_row: GuardianSession,
        guardian: Guardian,
        settings: GuardianSettings,
        user: User,
        analysis: Analysis,
        now: datetime,
    ) -> Outcome:
        sm_row.minute_timer = None
        sm_row.tracking_start_at = None  # back on flagged content, so any avoidance countdown restarts

        if sm_row.warning_active:
            return self._maybe_penalize(session, sm_row, guardian, settings, user, analysis.category, now)

        # A new warning episode
        sm_row.warning_active = True
        sm_row.warning_started_at = now
        sm_row.penalized_this_episode = False
        sm_row.episode_penalties = 0
        sm_row.last_penalty_at = None
        sm_row.last_flag_category = analysis.category
        progress_service.record_warning(session, user, now)

        breakdown = ScreenClassifier.breakdown(user, analysis, include_name=guardian.guardian_type == GuardianType.FAMILY)
        self.add_event(session=session, content=breakdown, sm_row=sm_row)
        if settings.reports_enabled:
            create_report(session=session, guardian=guardian, content=breakdown)
        return Outcome()

    def _maybe_penalize(
        self,
        session: Session,
        sm_row: GuardianSession,
        guardian: Guardian,
        settings: GuardianSettings,
        user: User,
        category: str | None,
        now: datetime,
    ) -> Outcome:
        """The user is still on flagged content after a warning. Past the threshold that counts as ignoring it."""
        started = sm_row.warning_started_at or now
        if (now - started).total_seconds() < IGNORE_THRESHOLD_SECONDS:
            return Outcome()
        if sm_row.episode_penalties >= MAX_PENALTIES_PER_WARNING:
            return Outcome()
        if sm_row.last_penalty_at and (now - sm_row.last_penalty_at).total_seconds() < REPEAT_PENALTY_SECONDS:
            return Outcome()

        first = not sm_row.penalized_this_episode
        sm_row.penalized_this_episode = True
        sm_row.episode_penalties += 1
        sm_row.last_penalty_at = now

        if first and settings.reports_enabled:
            who = f"{user.name} " if guardian.guardian_type == GuardianType.FAMILY else "You "
            what = category or sm_row.last_flag_category or "flagged content"
            create_report(
                session=session,
                guardian=guardian,
                content=f"{who}stayed on content flagged as {what} after being warned.",
            )
        penalty = self.penalty_for(settings, progress_service.warnings_today(session, user, now))
        return progress_service.record_ignored(session, user, now, penalty, first_in_episode=first)

    @staticmethod
    def penalty_for(settings: GuardianSettings, warnings_today: int) -> int:
        if not settings.points_loss_enabled:
            return 0
        multiplier = STRICTNESS_MULTIPLIERS.get(settings.strictness, 1.5)
        penalty = round(settings.base_points_lost * multiplier)
        if warnings_today >= REPEAT_OFFENDER_WARNINGS:
            penalty *= 2
        return penalty

    def _handle_clean(self, session: Session, sm_row: GuardianSession, user: User, now: datetime) -> Outcome:
        if sm_row.warning_active:
            # The user moved away from flagged content. Once they stay away long enough, the warning was heeded.
            if sm_row.tracking_start_at is None:
                sm_row.tracking_start_at = now
                sm_row.target_duration_seconds = AVOIDANCE_SECONDS
                return Outcome()
            if (now - sm_row.tracking_start_at).total_seconds() < sm_row.target_duration_seconds:
                return Outcome()

            sm_row.warning_active = False
            sm_row.tracking_start_at = None
            sm_row.warning_started_at = None
            sm_row.minute_timer = now
            if sm_row.penalized_this_episode:
                return Outcome()  # walked away eventually, but only after ignoring the warning
            return progress_service.record_heeded(session, user, now)

        # Clean browsing earns points every full minute
        if sm_row.minute_timer is None:
            sm_row.minute_timer = now
            return Outcome()
        if (now - sm_row.minute_timer).total_seconds() >= 60:
            sm_row.minute_timer = now
            return progress_service.record_clean_minute(session, user, now)
        return Outcome()

    def delete_session(self, session: Session, session_id: str):
        sess, mes = self.get_YTGSession(session=session, session_id=session_id)
        if not sess:
            return None, mes
        session.delete(sess)
        session.commit()
        return True, "success"

    def add_event(self, session: Session, sm_row: GuardianSession, content: str, time_duration: int | None = None):
        if time_duration is None:
            time_duration = random.randint(140, 300)
        # Only the latest few are kept; reports hold the history
        sm_row.events = [*sm_row.events[-19:], {"content": content, "should_avoid": True, "time_to_wait": time_duration}]

    def flush_wipe_events(self, session: Session, sm_row: GuardianSession):
        """Turn the session's pending events into reports for the guardian owner, then clear them."""
        if not sm_row.events:
            return
        guardian = session.get(Guardian, sm_row.guardian_id)
        if not guardian:
            raise ValueError(f"Guardian of id '{sm_row.guardian_id}' does not exist")

        for event in sm_row.events:
            session.add(GuardianReport(content=event["content"], guardian_id=guardian.id, send_to_id=guardian.owner_id))
        sm_row.events = []
        session.commit()
