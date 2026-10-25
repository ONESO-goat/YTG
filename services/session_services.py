from datetime import datetime

from sqlmodel import Session, select

from agent.bot import Analysis, ScreenClassifier
from agent.frames import frame_fingerprint, is_same_frame
from helpers import clock
from models.guardian_session import GuardianSession
from models.models import STRICTNESS_MULTIPLIERS, Guardian, GuardianSettings, GuardianType, User

from .errors import Conflict, ServiceError
from .guardian_services import GuardianServices
from .progress_service import Outcome, ProgressService

guardian_services = GuardianServices()
progress_service = ProgressService()

# Scans arrive every ~5 seconds; anything much faster is a misbehaving or abusive client
MIN_SCAN_INTERVAL_SECONDS = 2
# An unchanged screen earns nothing, and after ~5 minutes of them the session stops
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


class YTGSessionService:
    def get_users_session(self, session: Session, user: User) -> GuardianSession | None:
        return session.exec(select(GuardianSession).where(GuardianSession.user_id == user.id)).first()

    def get_or_create(self, session: Session, user: User, guardian: Guardian) -> GuardianSession:
        existing = session.exec(
            select(GuardianSession).where(
                GuardianSession.user_id == user.id,
                GuardianSession.guardian_id == guardian.id,
            )
        ).first()
        if existing:
            return existing
        row = GuardianSession(user_id=user.id, guardian_id=guardian.id)
        session.add(row)
        session.flush()
        return row

    def start_session(
        self, session: Session, user: User, guardian: Guardian
    ) -> tuple[GuardianSession, Outcome]:
        if not guardian.on:
            raise Conflict("Monitoring is turned off for this guardian")
        sm_row = self.get_or_create(session, user, guardian)
        outcome = Outcome()
        if not sm_row.active:
            sm_row.start()
            sm_row.last_frame_hash = None
            sm_row.same_image_counter = 0
            sm_row.minute_timer = None
            outcome = progress_service.record_session_start(session, user, clock.now())
        session.commit()
        session.refresh(sm_row)
        return sm_row, outcome

    def stop_session(self, session: Session, sm_row: GuardianSession) -> GuardianSession:
        sm_row.end()
        session.commit()
        session.refresh(sm_row)
        return sm_row

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
            raise Conflict("This session is not running. Start it before sending scans.")
        guardian = session.get(Guardian, session_row.guardian_id)
        user = session.get(User, session_row.user_id)
        if not guardian or not user:
            raise ServiceError("This session no longer belongs to a guardian")
        if not guardian.on:
            session_row.end()
            session.commit()
            raise Conflict("Monitoring is turned off for this guardian.")

        now = clock.now()
        previous_scan_at = session_row.last_scan_at
        if previous_scan_at and (now - previous_scan_at).total_seconds() < MIN_SCAN_INTERVAL_SECONDS:
            raise ServiceError("Scans are arriving too quickly", status_code=429)

        fingerprint = frame_fingerprint(image_bytes)
        if fingerprint is None:
            raise ServiceError("Uploaded file is not a readable image")

        settings = guardian_services.settings(session, guardian)
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

        analysis = classifier.analyze(
            image_bytes=image_bytes,
            user_id=user.id,
            guardian_settings=settings,
            restrictions=guardian_services.active_restrictions(session, guardian),
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

        include_name = guardian.guardian_type == GuardianType.FAMILY
        guardian_services.report(
            session, guardian, ScreenClassifier.breakdown(user, analysis, include_name), respect_settings=True
        )
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
        """The user is still on flagged content after a warning; past the threshold that is ignoring it."""
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

        if first:
            who = f"{user.name} " if guardian.guardian_type == GuardianType.FAMILY else "You "
            what = category or sm_row.last_flag_category or "flagged content"
            guardian_services.report(
                session,
                guardian,
                f"{who}stayed on content flagged as {what} after being warned.",
                respect_settings=True,
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
            # The user moved away from flagged content. Staying away long enough means the warning was heeded.
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
