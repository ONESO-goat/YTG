"""XP, levels, daily goals, streaks and achievements.

Every point a user earns or loses goes through here, so the daily caps and the per-day stats
always agree with the balance. Nothing in this module commits; callers commit once per request.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlmodel import Session, select

from models.models import User
from models.progress import DailyStats, UserAchievement, UserProgress

CLEAN_MINUTE_POINTS = 10
# Clean-minute points stop after an hour a day, so the app never rewards endless screen time
DAILY_MINUTE_POINTS_CAP = 600
AVOIDANCE_POINTS = 25
# Stops anyone farming bonuses by opening flagged content on purpose and then leaving
MAX_AVOIDANCE_BONUSES_PER_DAY = 5
DAILY_GOAL_MINUTES = 15
DAILY_GOAL_POINTS = 50
MAX_STREAK_FREEZES = 2
MAX_CURRENCY = 10_000_000

LEVEL_TITLES = [
    (1, "Seedling"),
    (3, "Sprout"),
    (5, "Explorer"),
    (8, "Pathfinder"),
    (12, "Defender"),
    (16, "Guardian"),
    (20, "Champion"),
    (30, "Legend"),
]


def xp_for_level(level: int) -> int:
    """Total XP needed to reach `level`. Each level takes 100 XP more than the one before."""
    return 50 * level * (level - 1)


def level_for_xp(xp: int) -> int:
    level = 1
    while xp >= xp_for_level(level + 1):
        level += 1
    return level


def title_for_level(level: int) -> str:
    return next(title for min_level, title in reversed(LEVEL_TITLES) if level >= min_level)


@dataclass(frozen=True)
class Achievement:
    code: str
    name: str
    description: str
    icon: str
    points: int
    target: int
    metric: Callable[[UserProgress], int]


ACHIEVEMENTS: list[Achievement] = [
    Achievement("first_session", "First steps", "Start your first session.", "footprints", 20, 1, lambda p: p.total_sessions),
    Achievement("goal_1", "Goal getter", "Complete a daily goal.", "target", 25, 1, lambda p: p.total_goals),
    Achievement("first_heed", "Walked away", "Move away from content after a warning.", "heart-handshake", 25, 1, lambda p: p.total_heeded),
    Achievement("clean_hour", "Clean hour", "Browse 60 clean minutes.", "sparkles", 50, 60, lambda p: p.total_clean_minutes),
    Achievement("streak_3", "On a roll", "Reach a 3-day streak.", "flame", 50, 3, lambda p: p.streak_best),
    Achievement("perfect_day", "Perfect day", "Complete a daily goal without ignoring a warning.", "sun", 50, 1, lambda p: p.total_perfect_days),
    Achievement("level_5", "Rising star", "Reach level 5.", "star", 100, 5, lambda p: level_for_xp(p.xp)),
    Achievement("heed_10", "Strong will", "Heed 10 warnings.", "shield-check", 100, 10, lambda p: p.total_heeded),
    Achievement("streak_7", "Week warrior", "Reach a 7-day streak.", "calendar-check", 150, 7, lambda p: p.streak_best),
    Achievement("goals_10", "Habit builder", "Complete 10 daily goals.", "repeat", 150, 10, lambda p: p.total_goals),
    Achievement("clean_10h", "Steady scroller", "Browse 600 clean minutes.", "leaf", 200, 600, lambda p: p.total_clean_minutes),
    Achievement("level_10", "Trailblazer", "Reach level 10.", "rocket", 250, 10, lambda p: level_for_xp(p.xp)),
    Achievement("heed_50", "Unshakeable", "Heed 50 warnings.", "shield", 300, 50, lambda p: p.total_heeded),
    Achievement("streak_30", "Unstoppable", "Reach a 30-day streak.", "crown", 500, 30, lambda p: p.streak_best),
    Achievement("first_purchase", "Treat yourself", "Buy something in the shop.", "gift", 25, 1, lambda p: p.total_purchases),
]
ACHIEVEMENTS_BY_CODE = {a.code: a for a in ACHIEVEMENTS}


@dataclass
class Outcome:
    """What a game action did, so the API can tell the user."""

    points: int = 0
    xp: int = 0
    lost: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)

    def merge(self, other: "Outcome") -> "Outcome":
        self.points += other.points
        self.xp += other.xp
        self.lost += other.lost
        self.events += other.events
        return self


def _event(type_: str, title: str, description: str, icon: str, points: int = 0, xp: int = 0) -> dict[str, Any]:
    return {"type": type_, "title": title, "description": description, "icon": icon, "points": points, "xp": xp}


def valid_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
        return True
    except (ZoneInfoNotFoundError, ValueError):
        return False


class ProgressService:
    def progress(self, session: Session, user: User) -> UserProgress:
        progress = session.get(UserProgress, user.id)
        if progress is None:
            progress = UserProgress(user_id=user.id)
            session.add(progress)
            session.flush()
        return progress

    @staticmethod
    def local_day(progress: UserProgress, now_utc: datetime) -> date:
        try:
            tz = ZoneInfo(progress.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            tz = ZoneInfo("UTC")
        return now_utc.replace(tzinfo=timezone.utc).astimezone(tz).date()

    def day_stats(self, session: Session, user_id: str, day: date) -> DailyStats:
        stats = session.exec(select(DailyStats).where(DailyStats.user_id == user_id, DailyStats.day == day)).first()
        if stats is None:
            stats = DailyStats(user_id=user_id, day=day)
            session.add(stats)
            session.flush()
        return stats

    def today(self, session: Session, user: User, now_utc: datetime) -> tuple[UserProgress, DailyStats]:
        progress = self.progress(session, user)
        return progress, self.day_stats(session, user.id, self.local_day(progress, now_utc))

    # ------------------------------------------------------------------ granting
    def _grant(
        self,
        user: User,
        progress: UserProgress,
        stats: DailyStats,
        points: int,
        xp: int,
        outcome: Outcome,
    ) -> None:
        level_before = level_for_xp(progress.xp)
        if points > 0:
            granted = min(points, MAX_CURRENCY - user.currency)
            user.currency += max(granted, 0)
            stats.points_earned += max(granted, 0)
            outcome.points += max(granted, 0)
        if xp > 0:
            progress.xp += xp
            stats.xp_earned += xp
            outcome.xp += xp
        level_after = level_for_xp(progress.xp)
        if level_after > level_before:
            outcome.events.append(
                _event(
                    "level_up",
                    f"Level {level_after}!",
                    f"You're now a {title_for_level(level_after)}.",
                    "trophy",
                )
            )

    def _finish(self, session: Session, user: User, progress: UserProgress, stats: DailyStats, now: datetime, outcome: Outcome) -> Outcome:
        """Unlock any achievements the action earned. Their rewards can unlock more (levels), so repeat."""
        unlocked = {
            code for code in session.exec(select(UserAchievement.code).where(UserAchievement.user_id == user.id)).all()
        }
        for _ in range(len(ACHIEVEMENTS)):
            newly = [a for a in ACHIEVEMENTS if a.code not in unlocked and a.metric(progress) >= a.target]
            if not newly:
                break
            for achievement in newly:
                unlocked.add(achievement.code)
                session.add(UserAchievement(user_id=user.id, code=achievement.code, unlocked_at=now))
                outcome.events.append(
                    _event(
                        "achievement",
                        achievement.name,
                        achievement.description,
                        achievement.icon,
                        points=achievement.points,
                        xp=achievement.points,
                    )
                )
                self._grant(user, progress, stats, achievement.points, achievement.points, outcome)
        return outcome

    # ------------------------------------------------------------------ streaks
    def _complete_goal(self, user: User, progress: UserProgress, stats: DailyStats, outcome: Outcome) -> None:
        stats.goal_completed = True
        progress.total_goals += 1
        if stats.warnings_ignored == 0:
            progress.total_perfect_days += 1
        outcome.events.append(
            _event(
                "goal",
                "Daily goal complete!",
                f"{DAILY_GOAL_MINUTES} clean minutes today.",
                "target",
                points=DAILY_GOAL_POINTS,
                xp=DAILY_GOAL_POINTS,
            )
        )
        self._grant(user, progress, stats, DAILY_GOAL_POINTS, DAILY_GOAL_POINTS, outcome)
        self._advance_streak(progress, stats.day, outcome)

    def _advance_streak(self, progress: UserProgress, today: date, outcome: Outcome) -> None:
        last = progress.streak_last_day
        if last == today:
            return
        missed = (today - last).days - 1 if last else 0
        if last is None or missed < 0:
            progress.streak_current = 1
        elif missed == 0:
            progress.streak_current += 1
        elif missed <= progress.streak_freezes:
            progress.streak_freezes -= missed
            progress.streak_current += 1
            outcome.events.append(
                _event(
                    "freeze_used",
                    "Streak saved",
                    f"{missed} streak freeze{'s' if missed > 1 else ''} covered the days you missed.",
                    "snowflake",
                )
            )
        else:
            progress.streak_current = 1
        progress.streak_last_day = today
        progress.streak_best = max(progress.streak_best, progress.streak_current)
        if progress.streak_current > 1:
            outcome.events.append(
                _event("streak", f"{progress.streak_current}-day streak!", "Come back tomorrow to keep it going.", "flame")
            )

    @staticmethod
    def streak_view(progress: UserProgress, today: date) -> dict[str, Any]:
        """The streak as it stands right now, accounting for days missed since the last goal."""
        last = progress.streak_last_day
        current = progress.streak_current
        if last is None:
            current = 0
        else:
            missed = (today - last).days - 1
            # Freezes are only spent when the next goal is completed, but they already protect the streak
            if missed > progress.streak_freezes:
                current = 0
        done_today = last == today
        return {
            "current": current,
            "best": progress.streak_best,
            "freezes": progress.streak_freezes,
            "max_freezes": MAX_STREAK_FREEZES,
            "done_today": done_today,
            "at_risk": current > 0 and not done_today,
        }

    # ------------------------------------------------------------------ actions
    def record_session_start(self, session: Session, user: User, now: datetime) -> Outcome:
        progress, stats = self.today(session, user, now)
        progress.total_sessions += 1
        return self._finish(session, user, progress, stats, now, Outcome())

    def record_clean_minute(self, session: Session, user: User, now: datetime) -> Outcome:
        progress, stats = self.today(session, user, now)
        outcome = Outcome()
        stats.clean_minutes += 1
        progress.total_clean_minutes += 1
        reward = min(CLEAN_MINUTE_POINTS, max(DAILY_MINUTE_POINTS_CAP - stats.minute_points, 0))
        if reward:
            stats.minute_points += reward
            self._grant(user, progress, stats, reward, reward, outcome)
        if not stats.goal_completed and stats.clean_minutes >= DAILY_GOAL_MINUTES:
            self._complete_goal(user, progress, stats, outcome)
        return self._finish(session, user, progress, stats, now, outcome)

    def record_warning(self, session: Session, user: User, now: datetime) -> int:
        """Count a new warning. Returns how many warnings the user has had today."""
        _, stats = self.today(session, user, now)
        stats.warnings_total += 1
        return stats.warnings_total

    def warnings_today(self, session: Session, user: User, now: datetime) -> int:
        return self.today(session, user, now)[1].warnings_total

    def record_heeded(self, session: Session, user: User, now: datetime) -> Outcome:
        progress, stats = self.today(session, user, now)
        outcome = Outcome()
        stats.warnings_heeded += 1
        progress.total_heeded += 1
        if stats.avoidance_bonuses < MAX_AVOIDANCE_BONUSES_PER_DAY:
            stats.avoidance_bonuses += 1
            self._grant(user, progress, stats, AVOIDANCE_POINTS, AVOIDANCE_POINTS, outcome)
        return self._finish(session, user, progress, stats, now, outcome)

    def record_ignored(self, session: Session, user: User, now: datetime, penalty: int, first_in_episode: bool) -> Outcome:
        progress, stats = self.today(session, user, now)
        if first_in_episode:
            stats.warnings_ignored += 1
            progress.total_ignored += 1
        lost = min(max(penalty, 0), user.currency)  # the balance never goes negative
        user.currency -= lost
        stats.points_lost += lost
        return Outcome(lost=lost)

    def grant(self, session: Session, user: User, now: datetime, points: int, xp: int) -> Outcome:
        """Give points and XP directly. Only used by the development helpers."""
        progress, stats = self.today(session, user, now)
        outcome = Outcome()
        self._grant(user, progress, stats, points, xp, outcome)
        return self._finish(session, user, progress, stats, now, outcome)

    def record_purchase(self, session: Session, user: User, now: datetime) -> Outcome:
        progress, stats = self.today(session, user, now)
        progress.total_purchases += 1
        return self._finish(session, user, progress, stats, now, Outcome())

    # ------------------------------------------------------------------ reading
    def summary(self, session: Session, user: User, now: datetime) -> dict[str, Any]:
        progress, stats = self.today(session, user, now)
        level = level_for_xp(progress.xp)
        floor, ceiling = xp_for_level(level), xp_for_level(level + 1)
        return {
            "level": level,
            "title": title_for_level(level),
            "xp": progress.xp,
            "xp_into_level": progress.xp - floor,
            "xp_for_next_level": ceiling - floor,
            "streak": self.streak_view(progress, stats.day),
            "today": {
                "day": stats.day,
                "clean_minutes": stats.clean_minutes,
                "goal_minutes": DAILY_GOAL_MINUTES,
                "goal_completed": stats.goal_completed,
                "minute_points": stats.minute_points,
                "minute_points_cap": DAILY_MINUTE_POINTS_CAP,
                "avoidance_bonuses_left": max(MAX_AVOIDANCE_BONUSES_PER_DAY - stats.avoidance_bonuses, 0),
                "points_earned": stats.points_earned,
                "points_lost": stats.points_lost,
                "xp_earned": stats.xp_earned,
                "warnings_total": stats.warnings_total,
                "warnings_heeded": stats.warnings_heeded,
                "warnings_ignored": stats.warnings_ignored,
            },
            "show_on_leaderboard": progress.show_on_leaderboard,
            "timezone": progress.timezone,
        }

    def achievements(self, session: Session, user: User) -> list[dict[str, Any]]:
        progress = self.progress(session, user)
        unlocked = {
            a.code: a.unlocked_at
            for a in session.exec(select(UserAchievement).where(UserAchievement.user_id == user.id)).all()
        }
        return [
            {
                "code": a.code,
                "name": a.name,
                "description": a.description,
                "icon": a.icon,
                "points": a.points,
                "target": a.target,
                "progress": min(a.metric(progress), a.target),
                "unlocked_at": unlocked.get(a.code),
            }
            for a in ACHIEVEMENTS
        ]

    def weekly_xp(self, session: Session, user_ids: list[str], today_utc: date) -> dict[str, int]:
        """XP earned over the last 7 days. Uses UTC days so everyone is ranked over the same window."""
        if not user_ids:
            return {}
        since = today_utc - timedelta(days=6)
        totals = {uid: 0 for uid in user_ids}
        rows = session.exec(
            select(DailyStats.user_id, DailyStats.xp_earned).where(
                DailyStats.user_id.in_(user_ids),  # type: ignore[attr-defined]
                DailyStats.day >= since,
            )
        ).all()
        for user_id, xp in rows:
            totals[user_id] += xp
        return totals
