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
from .gameify_service import Gameify, MaxedCurrencyError
from .guardian_services import GuardianServices
from .reports_service import create_report

guardian_services = GuardianServices()
gameify_service = Gameify()

# Scans arrive every ~5 seconds, so 6 identical frames is ~30 seconds of an untouched screen
SAME_FRAME_SHUTDOWN_COUNT = 6
# Staying on flagged content this long after the warning counts as ignoring it
IGNORE_THRESHOLD_SECONDS = 30
# How long the user must stay away from flagged content for the warning to count as heeded
AVOIDANCE_SECONDS = 15
ALERT_COUNT_THRESHOLD = 5
CLEAN_MINUTE_POINTS = 10
AVOIDANCE_POINTS = 25


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

    def get_all_sessions(self, session: Session):
        return session.exec(select(GuardianSession)).all()

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

    def _settle(self, session: Session, sess: GuardianSession) -> bool:
        user = session.get(User, sess.user_id)
        if not user:
            return False
        result = gameify_service.compute_daily_settlement(
            avoided_count=sess.amount_of_warnings_listened,
            ignored_count=sess.amount_of_warnings_ignored,
            amount_of_warnings=sess.total_alerts,
            streak_days=sess.streak,
        )
        try:
            gameify_service.add_points(session=session, user=user, amount=result.get("total", 0))
        except MaxedCurrencyError:
            pass
        sess.reset()
        return True

    def end_of_the_day_disprute_guardian(self, session: Session, guardian: Guardian) -> int:
        try:
            count = sum(self._settle(session, s) for s in self.get_all_sessions_under_guardian(session, guardian))
            session.commit()
            return count
        except Exception as ex:
            session.rollback()
            raise ValueError(f"Error during session daily reset: {ex}")

    def end_of_the_day_disprute_all(self, session: Session) -> int:
        try:
            count = sum(self._settle(session, s) for s in self.get_all_sessions(session))
            session.commit()
            return count
        except Exception as ex:
            session.rollback()
            raise ValueError(f"Error during session daily reset: {ex}")

    def get_users_session(self, session: Session, user: User) -> GuardianSession | None:
        return session.exec(select(GuardianSession).where(GuardianSession.user_id == user.id)).first()

    def _award(self, session: Session, sm_row: GuardianSession, user: User, amount: int) -> int:
        """Give points within the daily limit. Returns how many were actually given."""
        amount = min(amount, max(sm_row.points_gain_daily_limit, 0))
        if amount <= 0:
            return 0
        try:
            gameify_service.add_points(session=session, user=user, amount=amount)
        except MaxedCurrencyError:
            return 0
        sm_row.points_gain_daily_limit -= amount
        return amount

    def _result(
        self,
        sm_row: GuardianSession,
        user: User,
        flagged: bool = False,
        description: str = "",
        category: str | None = None,
        points_awarded: int = 0,
        points_lost: int = 0,
        shutdown: bool = False,
        analysis_failed: bool = False,
    ) -> dict:
        return {
            "flagged": flagged,
            "description": description,
            "category": category,
            "warning_active": sm_row.warning_active,
            "points_awarded": points_awarded,
            "points_lost": points_lost,
            "currency": user.currency,
            "shutdown": shutdown,
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
        session_row.last_scan_at = now

        # An unchanged screen earns nothing and needs no new AI verdict. Too many in a row ends
        # the session, so leaving a page open can't be used to farm points.
        if is_same_frame(fingerprint, session_row.last_frame_hash):
            session_row.same_image_counter += 1
            session_row.total_same_image_counter_for_whole_session += 1
            if session_row.same_image_counter >= SAME_FRAME_SHUTDOWN_COUNT:
                session_row.shutdown_counter += 1
                session_row.same_image_counter = 0
                session_row.minute_timer = None
                session_row.last_frame_hash = None
                session_row.end()
                session.commit()
                return self._result(session_row, user, shutdown=True)
            session.commit()
            return self._result(session_row, user, flagged=session_row.warning_active)

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
            return self._result(
                session_row, user, flagged=False, description=analysis.description, analysis_failed=True
            )

        if analysis.flagged:
            points_lost = self._handle_flagged(session, session_row, guardian, settings, user, analysis, now)
            session.commit()
            return self._result(
                session_row,
                user,
                flagged=True,
                description=analysis.description,
                category=analysis.category,
                points_lost=points_lost,
            )

        points_awarded = self._handle_clean(session, session_row, user, now)
        session.commit()
        return self._result(session_row, user, description=analysis.description, points_awarded=points_awarded)

    def _handle_flagged(
        self,
        session: Session,
        sm_row: GuardianSession,
        guardian: Guardian,
        settings: GuardianSettings,
        user: User,
        analysis: Analysis,
        now: datetime,
    ) -> int:
        sm_row.minute_timer = None
        sm_row.tracking_start_at = None  # back on flagged content, so any avoidance countdown restarts

        if not sm_row.warning_active:
            # A new warning episode
            sm_row.warning_active = True
            sm_row.warning_started_at = now
            sm_row.penalized_this_episode = False
            sm_row.total_alerts += 1

            breakdown = ScreenClassifier.breakdown(user, analysis, include_name=guardian.guardian_type == GuardianType.FAMILY)
            self.add_event(session=session, content=breakdown, sm_row=sm_row)
            if settings.reports_enabled:
                create_report(session=session, guardian=guardian, content=breakdown)
            return 0

        # Still on flagged content after being warned
        started = sm_row.warning_started_at or now
        ignored = (now - started).total_seconds() >= IGNORE_THRESHOLD_SECONDS
        if ignored and not sm_row.penalized_this_episode:
            sm_row.amount_of_warnings_ignored += 1
            sm_row.penalized_this_episode = True
            if settings.reports_enabled:
                who = f"{user.name} " if guardian.guardian_type == GuardianType.FAMILY else ""
                create_report(
                    session=session,
                    guardian=guardian,
                    content=f"{who}stayed on flagged content ({analysis.category}) after being warned.".strip().capitalize(),
                )
            return self.apply_point_penalty(session=session, sm_row=sm_row, guardian_settings=settings, user=user)
        return 0

    def _handle_clean(self, session: Session, sm_row: GuardianSession, user: User, now: datetime) -> int:
        if sm_row.warning_active:
            # The user moved away from flagged content. Once they stay away long enough, the warning was heeded.
            if sm_row.tracking_start_at is None:
                sm_row.tracking_start_at = now
                sm_row.target_duration_seconds = AVOIDANCE_SECONDS
                return 0
            if (now - sm_row.tracking_start_at).total_seconds() < sm_row.target_duration_seconds:
                return 0

            sm_row.warning_active = False
            sm_row.tracking_start_at = None
            sm_row.warning_started_at = None
            sm_row.minute_timer = now
            if sm_row.penalized_this_episode:
                return 0  # walked away eventually, but only after ignoring the warning
            sm_row.amount_of_warnings_listened += 1
            return self._award(session, sm_row, user, AVOIDANCE_POINTS)

        # Clean browsing earns points every full minute
        if sm_row.minute_timer is None:
            sm_row.minute_timer = now
            return 0
        if (now - sm_row.minute_timer).total_seconds() >= 60:
            sm_row.minute_timer = now
            return self._award(session, sm_row, user, CLEAN_MINUTE_POINTS)
        return 0

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
        sm_row.events.append({"content": content, "should_avoid": True, "time_to_wait": time_duration})
        session.commit()

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

    def apply_point_penalty(
        self, session: Session, sm_row: GuardianSession, guardian_settings: GuardianSettings, user: User
    ) -> int:
        """Deduct points for an ignored warning. Returns points actually deducted (0 if none)."""
        if not guardian_settings.points_loss_enabled:
            return 0
        multiplier = STRICTNESS_MULTIPLIERS.get(guardian_settings.strictness, 1.5)
        penalty = round(guardian_settings.base_points_lost * multiplier)
        # Repeat offenders in one day lose double
        if sm_row.total_alerts >= ALERT_COUNT_THRESHOLD:
            penalty *= 2
        actual_deducted = min(penalty, user.currency)  # never go negative
        if actual_deducted > 0:
            gameify_service.remove_points(session=session, user=user, amount=actual_deducted)
        return actual_deducted

