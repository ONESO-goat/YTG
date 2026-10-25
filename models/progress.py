"""Gamification state: lifetime progress, per-day stats and unlocked achievements."""

from datetime import date, datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from .helper import create_id


class UserProgress(SQLModel, table=True):
    __tablename__ = "user_progress"

    user_id: str = Field(foreign_key="user.id", primary_key=True)

    # Lifetime experience. Unlike points it is never spent or lost, so levels never go down.
    xp: int = Field(default=0)

    streak_current: int = Field(default=0)
    streak_best: int = Field(default=0)
    # Last local day the daily goal was completed
    streak_last_day: date | None = Field(default=None)
    streak_freezes: int = Field(default=0)

    total_clean_minutes: int = Field(default=0)
    total_heeded: int = Field(default=0)
    total_ignored: int = Field(default=0)
    total_sessions: int = Field(default=0)
    total_goals: int = Field(default=0)
    total_perfect_days: int = Field(default=0)
    total_purchases: int = Field(default=0)

    # IANA timezone name; decides where the user's days start and end
    timezone: str = Field(default="UTC")
    show_on_leaderboard: bool = Field(default=False)


class DailyStats(SQLModel, table=True):
    __tablename__ = "daily_stats"
    __table_args__ = (UniqueConstraint("user_id", "day"),)

    id: str = Field(default_factory=create_id, primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    # The user's local date
    day: date = Field(index=True)

    clean_minutes: int = Field(default=0)
    # Points from clean minutes, which have a daily cap
    minute_points: int = Field(default=0)
    avoidance_bonuses: int = Field(default=0)
    points_earned: int = Field(default=0)
    points_lost: int = Field(default=0)
    xp_earned: int = Field(default=0)

    warnings_total: int = Field(default=0)
    warnings_heeded: int = Field(default=0)
    warnings_ignored: int = Field(default=0)

    goal_completed: bool = Field(default=False)


class UserAchievement(SQLModel, table=True):
    __tablename__ = "user_achievement"
    __table_args__ = (UniqueConstraint("user_id", "code"),)

    id: str = Field(default_factory=create_id, primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    code: str
    unlocked_at: datetime
