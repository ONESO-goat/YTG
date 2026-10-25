from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.mutable import MutableList
from sqlmodel import JSON, Column, Field, SQLModel

from .helper import create_id, utcnow_naive


class GuardianSession(SQLModel, table=True):
    """A user's monitoring state under one guardian. Daily stats live in models/progress.py."""

    __tablename__ = "guardian_session"

    id: str = Field(default_factory=create_id, primary_key=True)

    user_id: str = Field(foreign_key="user.id")
    guardian_id: str = Field(foreign_key="guardian.id")
    active: bool = Field(default=False)

    # Current warning episode
    warning_active: bool = Field(default=False)
    warning_started_at: Optional[datetime] = Field(default=None, nullable=True)
    last_flag_category: Optional[str] = Field(default=None, nullable=True)
    penalized_this_episode: bool = Field(default=False)
    episode_penalties: int = Field(default=0)
    last_penalty_at: Optional[datetime] = Field(default=None, nullable=True)
    # When the user moved away from flagged content, and how long they must stay away
    tracking_start_at: Optional[datetime] = Field(default=None)
    target_duration_seconds: int = Field(default=0)

    # Start of the current clean minute
    minute_timer: Optional[datetime] = Field(default=None, nullable=True)

    # Perceptual hash of the last screenshot, see agent/frames.py
    last_frame_hash: Optional[str] = Field(default=None, nullable=True)
    same_image_counter: int = Field(default=0)
    total_same_image_counter_for_whole_session: int = Field(default=0)
    # How many times the session was stopped for an idle screen
    shutdown_counter: int = Field(default=0)

    # Latest flagged-content summaries
    events: list = Field(default_factory=list, sa_column=Column(MutableList.as_mutable(JSON)))

    last_scan_at: Optional[datetime] = Field(default=None)
    last_active_at: Optional[datetime] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=utcnow_naive)

    # Legacy counters, replaced by DailyStats/UserProgress. Kept only because existing databases have
    # them as NOT NULL columns without a default; drop them once there is a migration tool.
    total_alerts: int = Field(default=0)
    amount_of_warnings_ignored: int = Field(default=0)
    amount_of_warnings_listened: int = Field(default=0)
    points_pending: int = Field(default=0)
    points_gain_daily_limit: int = Field(default=0)
    streak: int = Field(default=0)

    def start(self):
        self.active = True
        self.last_active_at = datetime.now(timezone.utc).replace(tzinfo=None)

    def end(self):
        self.active = False
